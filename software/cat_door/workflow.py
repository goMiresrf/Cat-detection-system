"""Main software workflow for the cat door."""

from __future__ import annotations

import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .camera import Camera, CameraError
from .door_controller import DoorController
from .sensors import PirSensor
from .telegram_bot import (
    CLOSE_DOOR,
    CLOSE_DOOR_ACTION,
    IgnoredCallback,
    OPEN_CAMERA,
    OPEN_DOOR,
    OPEN_DOOR_ACTION,
    TelegramBot,
)


class CatDoorWorkflow:
    """Coordinates snapshot capture, detection, messaging, and door control."""

    def __init__(
        self,
        camera: Camera,
        telegram_bot: TelegramBot,
        door_controller: DoorController,
        pir_sensor: PirSensor,
        motion_cooldown_seconds: int,
        approval_timeout_seconds: int,
        live_stream_url: str,
        stream_health_url: str,
        pir_snapshot_delay_seconds: float,
        monitor_poll_interval_seconds: float,
        gpiozero_pin_factory: str,
    ) -> None:
        self.camera = camera
        self.telegram_bot = telegram_bot
        self.door_controller = door_controller
        self.pir_sensor = pir_sensor
        self.motion_cooldown_seconds = motion_cooldown_seconds
        self.approval_timeout_seconds = approval_timeout_seconds
        self.live_stream_url = live_stream_url
        self.stream_health_url = stream_health_url
        self.pir_snapshot_delay_seconds = max(0.0, pir_snapshot_delay_seconds)
        self.monitor_poll_interval_seconds = monitor_poll_interval_seconds
        self.gpiozero_pin_factory = gpiozero_pin_factory
        self._last_motion_timestamp: float | None = None
        self._next_update_offset: int | None = None
        self._auto_close_at: float | None = None

    def show_latest_chat_id(self) -> None:
        """Print the most recent chat ID seen by the bot."""
        chat_id = self.telegram_bot.get_latest_chat_id()
        if chat_id is None:
            print(
                "No Telegram chat ID found yet. Message the bot first, then run "
                "this command again."
            )
            return

        print(f"Latest Telegram chat ID: {chat_id}")

    def debug_updates(self) -> None:
        """Print a short summary of recent Telegram updates for setup debugging."""
        updates = self.telegram_bot.get_updates()
        print(f"Telegram returned {len(updates)} update(s).")

        for update in updates:
            callback_query = update.get("callback_query")
            if callback_query:
                message = callback_query.get("message", {})
                chat = message.get("chat", {})
                print(
                    "- "
                    f"update_id={update.get('update_id')}, "
                    "type=callback_query, "
                    f"chat_id={chat.get('id')}, "
                    f"chat_type={chat.get('type')}, "
                    f"data={callback_query.get('data')!r}"
                )
                continue

            message = update.get("message") or update.get("edited_message")
            if not message:
                print(
                    f"- update_id={update.get('update_id')} has no standard message payload"
                )
                continue

            chat = message.get("chat", {})
            text = message.get("text", "")
            print(
                "- "
                f"update_id={update.get('update_id')}, "
                f"chat_id={chat.get('id')}, "
                f"chat_type={chat.get('type')}, "
                f"text={text!r}"
            )

    def show_runtime_status(self) -> None:
        """Print a compact view of the configured runtime backends."""
        print(f"- {self.pir_sensor.describe()}")
        print(f"- {self.door_controller.describe()}")
        print(
            "- GPIOZero pin factory: "
            f"{self.gpiozero_pin_factory or 'auto-detect'}"
        )
        print(f"- Motion cooldown: {self.motion_cooldown_seconds} seconds")
        print(f"- Approval timeout: {self.approval_timeout_seconds} seconds")
        print(f"- PIR snapshot delay: {self.pir_snapshot_delay_seconds} seconds")
        print(f"- Live stream URL: {self.live_stream_url or 'not configured'}")
        print(f"- Stream health URL: {self.stream_health_url or 'not configured'}")

    def run_text_test(self) -> None:
        """Send a simple text message to confirm Telegram delivery works."""
        self.telegram_bot.send_control_panel(
            "Cat door text test successful. Telegram is connected."
        )
        print("Telegram text test sent successfully.")

    def run_approval_test(self) -> None:
        """Send inline approval buttons and wait for the selected action."""
        highest_update_id = self.telegram_bot.get_highest_update_id()

        self.telegram_bot.send_approval_request(
            "Cat door approval test\nChoose the action to send back to the app."
        )
        print("Approval request sent. Waiting for a button selection...")

        action = self._wait_for_approval_action(highest_update_id)
        if action is None:
            print(
                f"No button selection was received within "
                f"{self.approval_timeout_seconds} seconds."
            )
            return

        print(f"Approval test action received: {action}")

    def run_photo_test(self) -> None:
        """Capture a photo and run the same approval flow used for real events."""
        image_path = self._process_event(trigger_reason="photo-test")
        if image_path is None:
            print("Photo test completed without sending a notification.")
        self._wait_for_scheduled_close()

    def run_monitor_once(self) -> None:
        """Wait for one PIR event and process it."""
        if not self.pir_sensor.is_available():
            print(self.pir_sensor.describe())
            return

        print("Waiting for a PIR motion event...")
        if self.pir_sensor.wait_for_motion(timeout_seconds=None):
            self._process_event(trigger_reason="pir")
            self._wait_for_scheduled_close()

    def run_monitor_loop(self) -> None:
        """Continuously wait for PIR motion and process each event."""
        self._start_telegram_controls()
        if not self.pir_sensor.is_available():
            print(self.pir_sensor.describe())
            print("Telegram controls are still running. Press Ctrl+C to stop.")

        print("Starting cat door monitor loop. Press Ctrl+C to stop.")
        try:
            while True:
                self._poll_telegram_controls()
                self._close_door_if_due()

                if self.pir_sensor.is_available() and self.pir_sensor.wait_for_motion(
                    timeout_seconds=self.monitor_poll_interval_seconds
                ):
                    self._process_event(trigger_reason="pir")
                elif not self.pir_sensor.is_available():
                    time.sleep(self.monitor_poll_interval_seconds)
        except KeyboardInterrupt:
            print("Monitor loop stopped.")

    def _process_event(
        self,
        trigger_reason: str,
    ) -> Path | None:
        """Run the full event pipeline from capture to approval handling."""
        cooldown_remaining = self._cooldown_remaining_seconds()
        if cooldown_remaining > 0:
            print(
                f"Skipping event because cooldown is active for "
                f"{cooldown_remaining:.1f} more seconds."
            )
            return None

        self._last_motion_timestamp = time.monotonic()
        self._wait_before_snapshot(trigger_reason)
        try:
            image_path = self.camera.capture_snapshot()
        except CameraError as exc:
            self._handle_camera_failure(trigger_reason, exc)
            return None

        event_live_stream_url = ""
        if self.live_stream_url and self._live_stream_is_online()[0]:
            event_live_stream_url = self.live_stream_url

        caption = self._build_event_caption(
            trigger_reason,
            image_path.name,
            event_live_stream_url,
        )
        highest_update_id = self.telegram_bot.get_highest_update_id()
        self.telegram_bot.send_photo_approval_request(
            image_path,
            caption,
            live_stream_url=event_live_stream_url,
        )
        print("Photo notification sent. Waiting for approval response...")

        action = self._wait_for_approval_action(highest_update_id)
        if action is None:
            print(
                f"No approval response received within "
                f"{self.approval_timeout_seconds} seconds. Keeping door closed."
            )
            return image_path

        if action == OPEN_DOOR:
            self._open_door()
        elif action == CLOSE_DOOR:
            self._close_door()

        return image_path

    def _build_event_caption(
        self,
        trigger_reason: str,
        image_name: str,
        live_stream_url: str,
    ) -> str:
        """Build the human-readable Telegram caption for an event photo."""
        live_view_line = (
            f"Live view: {live_stream_url}\n" if live_stream_url else ""
        )
        return (
            "Cat door event\n"
            f"Trigger: {trigger_reason}\n"
            f"Image: {image_name}\n"
            f"{live_view_line}"
            "Choose an action."
        )

    def _wait_before_snapshot(self, trigger_reason: str) -> None:
        """Delay PIR snapshots so the cat has time to enter the camera frame."""
        if trigger_reason != "pir" or self.pir_snapshot_delay_seconds <= 0:
            return

        print(
            "PIR triggered. Waiting "
            f"{self.pir_snapshot_delay_seconds:.1f} seconds before snapshot..."
        )
        time.sleep(self.pir_snapshot_delay_seconds)

    def _wait_for_approval_action(self, after_update_id: int | None) -> str | None:
        """Wait for a Telegram callback and convert it into a readable action."""
        result = self.telegram_bot.wait_for_callback(
            expected_actions={OPEN_DOOR_ACTION, CLOSE_DOOR_ACTION},
            after_update_id=after_update_id,
            timeout_seconds=self.approval_timeout_seconds,
        )

        if result is None:
            return None

        if isinstance(result, IgnoredCallback):
            self._next_update_offset = result.update_id + 1
            print(f"Ignored Telegram callback: {result.reason}")
            self.telegram_bot.answer_callback_query(
                result.callback_query_id,
                text="This button press was ignored. Check the Pi terminal.",
            )
            self.telegram_bot.send_message(
                "Button press ignored.\n"
                f"Reason: {result.reason}\n"
                "Check CAT_DOOR_TELEGRAM_CHAT_ID in cat_door/.env."
            )
            return None

        selected_label = (
            OPEN_DOOR if result.action == OPEN_DOOR_ACTION else CLOSE_DOOR
        )
        self._next_update_offset = result.update_id + 1

        # Telegram expects callback queries to be acknowledged to stop the client
        # loading indicator after a button press.
        self.telegram_bot.answer_callback_query(
            result.callback_query_id,
            text=f"Selected: {selected_label}",
        )

        if result.message_id is not None:
            self.telegram_bot.clear_inline_keyboard(
                chat_id=result.chat_id,
                message_id=result.message_id,
            )

        self.telegram_bot.send_message(
            f"Approval result received: {selected_label}."
        )
        return selected_label

    def _start_telegram_controls(self) -> None:
        """Send the persistent Telegram control buttons and ignore stale updates."""
        highest_update_id = self.telegram_bot.get_highest_update_id()
        self._next_update_offset = (
            None if highest_update_id is None else highest_update_id + 1
        )
        self.telegram_bot.send_control_panel(
            "Cat door controls are online.\n"
            "Use the buttons below to open the door, close the door, or open camera."
        )

    def _poll_telegram_controls(self) -> None:
        """Read Telegram button/message controls without blocking the monitor loop."""
        updates = self.telegram_bot.get_updates(
            offset=self._next_update_offset,
            allowed_updates=["message", "callback_query"],
            timeout=0,
        )

        for update in updates:
            self._next_update_offset = int(update["update_id"]) + 1
            callback_query = update.get("callback_query")
            if callback_query:
                self._handle_callback_query(callback_query)
                continue

            message = update.get("message") or update.get("edited_message")
            if message:
                self._handle_message(message)

    def _handle_message(self, message: dict) -> None:
        """Handle persistent keyboard presses and simple slash commands."""
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if not self.telegram_bot.is_authorized_chat(chat_id):
            self.telegram_bot.send_message(
                "This chat is not authorized to control the cat door.",
                chat_id=chat_id,
            )
            return

        text = str(message.get("text", "")).strip()
        command = text.lower()

        if command in {OPEN_DOOR.lower(), "/open"}:
            self._open_door()
        elif command in {CLOSE_DOOR.lower(), "/close"}:
            self._close_door()
        elif command in {OPEN_CAMERA.lower(), "/live"}:
            self._send_camera_button()
        elif command in {"/start", "/help"}:
            self.telegram_bot.send_control_panel(
                "Cat door controls:\n"
                "- Open Door\n"
                "- Close Door\n"
                "- Open Camera"
            )

    def _handle_callback_query(self, callback_query: dict) -> None:
        """Handle inline Open/Close buttons on cat-door event alerts."""
        callback_query_id = str(callback_query["id"])
        message = callback_query.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not self.telegram_bot.is_authorized_chat(chat_id):
            self.telegram_bot.answer_callback_query(
                callback_query_id,
                text="This chat is not authorized.",
            )
            return

        action = str(callback_query.get("data", ""))
        if action == OPEN_DOOR_ACTION:
            self._open_door()
            selected_label = OPEN_DOOR
        elif action == CLOSE_DOOR_ACTION:
            self._close_door()
            selected_label = CLOSE_DOOR
        else:
            return

        self.telegram_bot.answer_callback_query(
            callback_query_id,
            text=f"Selected: {selected_label}",
        )
        message_id = message.get("message_id")
        if message_id is not None:
            self.telegram_bot.clear_inline_keyboard(
                chat_id=str(chat_id),
                message_id=message_id,
            )

    def _open_door(self) -> None:
        """Open the door now and schedule the automatic close."""
        self.door_controller.open_latch()
        self._auto_close_at = (
            time.monotonic() + self.door_controller.open_duration_seconds
        )
        self.telegram_bot.send_message(
            "Door opened.\n"
            f"It will close automatically in "
            f"{self.door_controller.open_duration_seconds} seconds."
        )

    def _close_door(self) -> None:
        """Close the door now and cancel any pending automatic close."""
        self.door_controller.close_latch()
        self._auto_close_at = None
        self.telegram_bot.send_message("Door closed.")

    def _send_camera_button(self) -> None:
        """Send the configured live camera button, or a clear setup error."""
        if not self.live_stream_url:
            self.telegram_bot.send_message(
                "Live camera URL is not configured.\n"
                "Set CAT_DOOR_LIVE_STREAM_URL in cat_door/.env."
            )
            return

        stream_online, error_message = self._live_stream_is_online()
        if not stream_online:
            self.telegram_bot.send_message(
                "Live stream is currently unavailable.\n"
                f"{error_message}\n"
                "Check the Raspberry Pi camera stream service."
            )
            return

        self.telegram_bot.send_camera_button(self.live_stream_url)

    def _live_stream_is_online(self) -> tuple[bool, str]:
        """Check the local camera stream health endpoint when configured."""
        if not self.stream_health_url:
            return True, ""

        request = Request(
            self.stream_health_url,
            headers={"User-Agent": "cat-door-bot/1.0"},
        )
        try:
            with urlopen(request, timeout=2.0) as response:
                if getattr(response, "status", 200) == 200:
                    return True, ""
                return False, f"Health check returned HTTP {response.status}."
        except HTTPError as exc:
            return False, f"Health check returned HTTP {exc.code}."
        except URLError as exc:
            return False, f"Health check failed: {exc.reason}."
        except OSError as exc:
            return False, f"Health check failed: {exc}."

    def _close_door_if_due(self) -> None:
        """Automatically close the door after the configured open duration."""
        if self._auto_close_at is None or time.monotonic() < self._auto_close_at:
            return

        self._auto_close_at = None
        self.door_controller.close_latch()
        self.telegram_bot.send_message("Door closed automatically.")

    def _wait_for_scheduled_close(self) -> None:
        """Keep one-shot test modes alive until the automatic close has run."""
        while self._auto_close_at is not None:
            self._poll_telegram_controls()
            self._close_door_if_due()

            if self._auto_close_at is None:
                return

            remaining_seconds = max(0.0, self._auto_close_at - time.monotonic())
            time.sleep(min(self.monitor_poll_interval_seconds, remaining_seconds))

    def _handle_camera_failure(
        self,
        trigger_reason: str,
        error: CameraError,
    ) -> None:
        """Report a camera failure without crashing the monitor loop."""
        print("Camera snapshot failed.")
        print(error)

        message = (
            "Camera snapshot failed.\n"
            f"Trigger: {trigger_reason}\n\n"
            f"{error}\n\n"
            "Try /live if the stream is running, or check the Raspberry Pi camera."
        )

        try:
            self.telegram_bot.send_message(message)
        except Exception as telegram_error:
            print("Could not send camera failure message to Telegram.")
            print(telegram_error)

    def _cooldown_remaining_seconds(self) -> float:
        if self._last_motion_timestamp is None:
            return 0.0

        elapsed = time.monotonic() - self._last_motion_timestamp
        remaining = self.motion_cooldown_seconds - elapsed
        return max(0.0, remaining)
