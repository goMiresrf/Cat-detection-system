"""Main software workflow for the cat door."""

from __future__ import annotations

import time

from .camera import Camera
from .detector import DetectionResult, Detector
from .door_controller import DoorController
from .sensors import PirSensor, ReedSwitch
from .telegram_bot import TelegramBot


class CatDoorWorkflow:
    """Coordinates snapshot capture, detection, messaging, and door control."""

    def __init__(
        self,
        camera: Camera,
        detector: Detector,
        telegram_bot: TelegramBot,
        door_controller: DoorController,
        pir_sensor: PirSensor,
        reed_switch: ReedSwitch,
        motion_cooldown_seconds: int,
        approval_timeout_seconds: int,
        live_stream_url: str,
        notify_on_any_motion: bool,
        monitor_poll_interval_seconds: float,
        gpiozero_pin_factory: str,
    ) -> None:
        self.camera = camera
        self.detector = detector
        self.telegram_bot = telegram_bot
        self.door_controller = door_controller
        self.pir_sensor = pir_sensor
        self.reed_switch = reed_switch
        self.motion_cooldown_seconds = motion_cooldown_seconds
        self.approval_timeout_seconds = approval_timeout_seconds
        self.live_stream_url = live_stream_url
        self.notify_on_any_motion = notify_on_any_motion
        self.monitor_poll_interval_seconds = monitor_poll_interval_seconds
        self.gpiozero_pin_factory = gpiozero_pin_factory
        self._last_motion_timestamp: float | None = None

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
        print(f"- {self.reed_switch.describe()}")
        print(f"- {self.door_controller.describe()}")
        print(f"- {self.detector.describe()}")
        print(
            "- GPIOZero pin factory: "
            f"{self.gpiozero_pin_factory or 'auto-detect'}"
        )
        print(f"- Motion cooldown: {self.motion_cooldown_seconds} seconds")
        print(f"- Approval timeout: {self.approval_timeout_seconds} seconds")
        print(f"- Notify on any motion: {self.notify_on_any_motion}")

    def run_text_test(self) -> None:
        """Send a simple text message to confirm Telegram delivery works."""
        self.telegram_bot.send_message(
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
        detection = self._process_event(trigger_reason="photo-test", send_even_if_no_cat=True)
        if detection is None:
            print("Photo test completed without sending a notification.")

    def run_monitor_once(self) -> None:
        """Wait for one PIR event and process it."""
        if not self.pir_sensor.is_available():
            print(self.pir_sensor.describe())
            return

        print("Waiting for a PIR motion event...")
        if self.pir_sensor.wait_for_motion(timeout_seconds=None):
            self._process_event(trigger_reason="pir", send_even_if_no_cat=False)

    def run_monitor_loop(self) -> None:
        """Continuously wait for PIR motion and process each event."""
        if not self.pir_sensor.is_available():
            print(self.pir_sensor.describe())
            return

        print("Starting cat door monitor loop. Press Ctrl+C to stop.")
        try:
            while True:
                if self.pir_sensor.wait_for_motion(
                    timeout_seconds=self.monitor_poll_interval_seconds
                ):
                    self._process_event(trigger_reason="pir", send_even_if_no_cat=False)
        except KeyboardInterrupt:
            print("Monitor loop stopped.")

    def _process_event(
        self,
        trigger_reason: str,
        send_even_if_no_cat: bool,
    ) -> DetectionResult | None:
        """Run the full event pipeline from capture to approval handling."""
        cooldown_remaining = self._cooldown_remaining_seconds()
        if cooldown_remaining > 0:
            print(
                f"Skipping event because cooldown is active for "
                f"{cooldown_remaining:.1f} more seconds."
            )
            return None

        self._last_motion_timestamp = time.monotonic()
        image_path = self.camera.capture_snapshot()
        detection = self.detector.detect_cat(image_path)

        if not send_even_if_no_cat and not self._should_notify(detection):
            print(
                "Event processed but notification suppressed because detector "
                "did not mark it as cat-likely."
            )
            print(f"Detector reason: {detection.reason}")
            return detection

        caption = self._build_event_caption(trigger_reason, image_path.name, detection)
        highest_update_id = self.telegram_bot.get_highest_update_id()
        self.telegram_bot.send_photo_approval_request(image_path, caption)
        print("Photo notification sent. Waiting for approval response...")

        action = self._wait_for_approval_action(highest_update_id)
        if action is None:
            print(
                f"No approval response received within "
                f"{self.approval_timeout_seconds} seconds. Keeping door closed."
            )
            return detection

        if action == "Open Door":
            self.door_controller.open_temporarily()

        return detection

    def _build_event_caption(
        self,
        trigger_reason: str,
        image_name: str,
        detection: DetectionResult,
    ) -> str:
        """Build the human-readable Telegram caption for an event photo."""
        live_view_line = (
            f"Live view: {self.live_stream_url}\n" if self.live_stream_url else ""
        )
        return (
            "Cat door event\n"
            f"Trigger: {trigger_reason}\n"
            f"Image: {image_name}\n"
            f"Cat likely: {detection.is_cat_likely}\n"
            f"Confidence: {detection.confidence:.2f}\n"
            f"Reason: {detection.reason}\n"
            f"{live_view_line}"
            "Approve opening?"
        )

    def _wait_for_approval_action(self, after_update_id: int | None) -> str | None:
        """Wait for a Telegram callback and convert it into a readable action."""
        result = self.telegram_bot.wait_for_callback(
            expected_actions={"OPEN_DOOR", "KEEP_CLOSED"},
            after_update_id=after_update_id,
            timeout_seconds=self.approval_timeout_seconds,
        )

        if result is None:
            return None

        selected_label = "Open Door" if result.action == "OPEN_DOOR" else "Keep Closed"

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



    def _cooldown_remaining_seconds(self) -> float:
        if self._last_motion_timestamp is None:
            return 0.0

        elapsed = time.monotonic() - self._last_motion_timestamp
        remaining = self.motion_cooldown_seconds - elapsed
        return max(0.0, remaining)

    def _should_notify(self, detection: DetectionResult) -> bool:
        """Decide whether an event should notify even before manual approval."""
        if self.notify_on_any_motion:
            return True

        return detection.is_cat_likely
