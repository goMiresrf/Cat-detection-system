"""Telegram messaging support."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

import requests


OPEN_DOOR = "Open Door"
CLOSE_DOOR = "Close Door"
OPEN_CAMERA = "Open Camera"

OPEN_DOOR_ACTION = "OPEN_DOOR"
CLOSE_DOOR_ACTION = "CLOSE_DOOR"
DEFAULT_ALLOWED_UPDATES = ["message", "edited_message", "callback_query"]


@dataclass(frozen=True)
class CallbackResult:
    """Represents a callback button selection returned by Telegram."""

    action: str
    callback_query_id: str
    chat_id: str
    message_id: int | None
    update_id: int


@dataclass(frozen=True)
class IgnoredCallback:
    """Represents a callback button press that was seen but not accepted."""

    reason: str
    action: str
    callback_query_id: str
    chat_id: str
    update_id: int


class TelegramBot:
    """Small wrapper around the Telegram Bot API."""

    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def has_token(self) -> bool:
        return bool(self.token)

    def has_chat_target(self) -> bool:
        return bool(self.chat_id)

    def is_authorized_chat(self, chat_id: str | int | None) -> bool:
        return bool(self.chat_id) and str(chat_id) == str(self.chat_id)

    def _require_token(self) -> None:
        if not self.has_token():
            raise RuntimeError("Telegram bot token is missing.")

    def _require_chat_target(self) -> None:
        if not self.has_chat_target():
            raise RuntimeError("Telegram chat ID is missing.")

    def _parse_result(self, response: requests.Response) -> dict[str, Any] | list[Any]:
        """Validate a Telegram API response and return its result payload."""
        response.raise_for_status()
        payload = response.json()

        if not payload.get("ok", False):
            description = payload.get("description", "Unknown Telegram API error.")
            raise RuntimeError(f"Telegram API request failed: {description}")

        return payload.get("result", {})

    @staticmethod
    def build_control_keyboard() -> dict[str, Any]:
        """Build the persistent Telegram keyboard for everyday controls."""
        return {
            "keyboard": [
                [{"text": OPEN_DOOR}, {"text": CLOSE_DOOR}],
                [{"text": OPEN_CAMERA}],
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
            "is_persistent": True,
        }

    @staticmethod
    def build_event_keyboard(live_stream_url: str = "") -> dict[str, Any]:
        """Build inline buttons for a cat-door event alert."""
        keyboard: list[list[dict[str, str]]] = []
        if live_stream_url:
            keyboard.append([{"text": OPEN_CAMERA, "url": live_stream_url}])

        keyboard.append(
            [
                {"text": OPEN_DOOR, "callback_data": OPEN_DOOR_ACTION},
                {"text": CLOSE_DOOR, "callback_data": CLOSE_DOOR_ACTION},
            ]
        )
        return {"inline_keyboard": keyboard}

    @staticmethod
    def build_camera_keyboard(live_stream_url: str) -> dict[str, Any]:
        """Build a single URL button for the live camera."""
        return {"inline_keyboard": [[{"text": OPEN_CAMERA, "url": live_stream_url}]]}

    def send_message(
        self,
        text: str,
        reply_markup: dict[str, Any] | None = None,
        chat_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Send a text message, optionally with Telegram reply markup."""
        self._require_token()
        target_chat_id = chat_id if chat_id is not None else self.chat_id
        if not target_chat_id:
            self._require_chat_target()

        payload: dict[str, Any] = {"chat_id": target_chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        response = requests.post(
            f"{self.base_url}/sendMessage",
            json=payload,
            timeout=30,
        )
        result = self._parse_result(response)
        return result if isinstance(result, dict) else {}

    def send_control_panel(self, text: str) -> dict[str, Any]:
        """Send the persistent Open/Close/Camera controls."""
        return self.send_message(
            text,
            reply_markup=self.build_control_keyboard(),
        )

    def send_camera_button(self, live_stream_url: str) -> dict[str, Any]:
        """Send a clean button that opens the configured live camera URL."""
        return self.send_message(
            "Open the live camera below.",
            reply_markup=self.build_camera_keyboard(live_stream_url),
        )

    def send_photo(
        self,
        image_path: Path,
        caption: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a photo message, optionally with inline buttons."""
        self._require_token()
        self._require_chat_target()

        data: dict[str, Any] = {"chat_id": self.chat_id, "caption": caption}
        if reply_markup is not None:
            # Multipart requests require reply markup to be JSON serialized.
            data["reply_markup"] = json.dumps(reply_markup)

        with image_path.open("rb") as image_file:
            response = requests.post(
                f"{self.base_url}/sendPhoto",
                data=data,
                files={"photo": image_file},
                timeout=60,
            )
        result = self._parse_result(response)
        return result if isinstance(result, dict) else {}

    def send_approval_request(self, prompt_text: str) -> dict[str, Any]:
        """Send the initial approval request with inline action buttons."""
        return self.send_message(
            prompt_text,
            reply_markup=self.build_event_keyboard(),
        )

    def send_photo_approval_request(
        self,
        image_path: Path,
        caption: str,
        live_stream_url: str = "",
    ) -> dict[str, Any]:
        """Send a photo and attach the standard approval buttons."""
        return self.send_photo(
            image_path,
            caption,
            reply_markup=self.build_event_keyboard(live_stream_url),
        )

    def get_updates(
        self,
        limit: int = 10,
        offset: int | None = None,
        allowed_updates: list[str] | None = None,
        timeout: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch recent bot updates from Telegram."""
        self._require_token()

        params: dict[str, Any] = {"limit": limit, "timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        update_types = allowed_updates or DEFAULT_ALLOWED_UPDATES
        params["allowed_updates"] = json.dumps(update_types)

        request_timeout_seconds = timeout + 5 if timeout > 0 else 1
        response = requests.get(
            f"{self.base_url}/getUpdates",
            params=params,
            timeout=request_timeout_seconds,
        )
        result = self._parse_result(response)
        return result if isinstance(result, list) else []

    def get_latest_chat_id(self) -> str | None:
        """Return the most recent chat ID seen in standard message updates."""
        updates = self.get_updates()

        for update in reversed(updates):
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue

            chat = message.get("chat", {})
            chat_id = chat.get("id")
            if chat_id is not None:
                return str(chat_id)

        return None

    def get_highest_update_id(self) -> int | None:
        """Return the highest update ID seen so far, if any updates exist."""
        updates = self.get_updates(limit=100)
        if not updates:
            return None
        return max(int(update["update_id"]) for update in updates)

    def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        """Acknowledge a pressed button so Telegram clears its loading state."""
        self._require_token()

        response = requests.post(
            f"{self.base_url}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=30,
        )
        self._parse_result(response)

    def clear_inline_keyboard(self, chat_id: str, message_id: int) -> None:
        """Remove inline buttons from a message after a selection is made."""
        self._require_token()

        response = requests.post(
            f"{self.base_url}/editMessageReplyMarkup",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": {"inline_keyboard": []},
            },
            timeout=30,
        )
        self._parse_result(response)

    def wait_for_callback(
        self,
        expected_actions: set[str],
        after_update_id: int | None,
        timeout_seconds: int,
    ) -> CallbackResult | IgnoredCallback | None:
        """Poll Telegram until one of the expected callback actions arrives."""
        self._require_token()
        deadline = time.monotonic() + timeout_seconds
        next_offset = None if after_update_id is None else after_update_id + 1

        while time.monotonic() < deadline:
            remaining_seconds = max(1, int(deadline - time.monotonic()))
            updates = self.get_updates(
                offset=next_offset,
                allowed_updates=DEFAULT_ALLOWED_UPDATES,
                timeout=min(10, remaining_seconds),
            )

            for update in updates:
                next_offset = int(update["update_id"]) + 1
                callback_query = update.get("callback_query")
                if not callback_query:
                    continue

                data = str(callback_query.get("data", ""))
                message = callback_query.get("message", {})
                chat = message.get("chat", {})
                chat_id = str(chat.get("id", ""))

                if self.chat_id and chat_id != self.chat_id:
                    return IgnoredCallback(
                        reason=(
                            "chat_id_mismatch: "
                            f"expected {self.chat_id!r}, got {chat_id!r}"
                        ),
                        action=data,
                        callback_query_id=str(callback_query["id"]),
                        chat_id=chat_id,
                        update_id=int(update["update_id"]),
                    )
                if data not in expected_actions:
                    return IgnoredCallback(
                        reason=(
                            "unexpected_action: "
                            f"expected {sorted(expected_actions)!r}, got {data!r}"
                        ),
                        action=data,
                        callback_query_id=str(callback_query["id"]),
                        chat_id=chat_id,
                        update_id=int(update["update_id"]),
                    )

                return CallbackResult(
                    action=data,
                    callback_query_id=str(callback_query["id"]),
                    chat_id=chat_id,
                    message_id=message.get("message_id"),
                    update_id=int(update["update_id"]),
                )

        return None
