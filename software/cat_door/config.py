"""Configuration loading for the cat door application."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Central application configuration loaded from environment variables."""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    live_stream_url: str = ""
    pir_pin: int = 17
    reed_switch_pin: int = 27
    servo_pin: int = 18
    image_output_dir: str = "captures"
    camera_capture_timeout_ms: int = 250
    motion_cooldown_seconds: int = 30
    door_open_seconds: int = 5
    approval_timeout_seconds: int = 60
    monitor_poll_interval_seconds: float = 1.0
    pir_settle_seconds: float = 3.0
    notify_on_any_motion: bool = True
    gpiozero_pin_factory: str = ""
    detector_mode: str = "disabled"
    detector_command: str = ""
    detector_command_timeout_seconds: int = 30
    detection_confidence_threshold: float = 0.5
    enable_gpio_hardware: bool = True
    enable_servo_hardware: bool = False
    reed_closed_when_pressed: bool = True
    servo_open_value: float = 1.0
    servo_closed_value: float = -1.0


def _load_dotenv(dotenv_path: Path) -> None:
    """Populate missing environment variables from a local .env file."""
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)

        # Keep real environment variables in charge so Pi deployment stays flexible.
        os.environ.setdefault(key.strip(), value.strip())


def _get_bool_env(name: str, default: bool) -> bool:
    """Parse common boolean environment values such as true/false or 1/0."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> AppConfig:
    """Load runtime configuration from environment variables."""
    # Loading a project-local .env keeps local development simple in IntelliJ.
    _load_dotenv(Path(".env"))

    return AppConfig(
        telegram_bot_token=os.getenv("CAT_DOOR_TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("CAT_DOOR_TELEGRAM_CHAT_ID", ""),
        live_stream_url=os.getenv("CAT_DOOR_LIVE_STREAM_URL", "").strip(),
        pir_pin=int(os.getenv("CAT_DOOR_PIR_PIN", "17")),
        reed_switch_pin=int(os.getenv("CAT_DOOR_REED_SWITCH_PIN", "27")),
        servo_pin=int(os.getenv("CAT_DOOR_SERVO_PIN", "18")),
        image_output_dir=os.getenv("CAT_DOOR_IMAGE_OUTPUT_DIR", "captures"),
        camera_capture_timeout_ms=int(
            os.getenv("CAT_DOOR_CAMERA_CAPTURE_TIMEOUT_MS", "250")
        ),
        motion_cooldown_seconds=int(
            os.getenv("CAT_DOOR_MOTION_COOLDOWN_SECONDS", "30")
        ),
        door_open_seconds=int(os.getenv("CAT_DOOR_DOOR_OPEN_SECONDS", "5")),
        approval_timeout_seconds=int(
            os.getenv("CAT_DOOR_APPROVAL_TIMEOUT_SECONDS", "60")
        ),
        monitor_poll_interval_seconds=float(
            os.getenv("CAT_DOOR_MONITOR_POLL_INTERVAL_SECONDS", "1.0")
        ),
        pir_settle_seconds=float(os.getenv("CAT_DOOR_PIR_SETTLE_SECONDS", "3.0")),
        notify_on_any_motion=_get_bool_env("CAT_DOOR_NOTIFY_ON_ANY_MOTION", True),
        gpiozero_pin_factory=os.getenv("CAT_DOOR_GPIOZERO_PIN_FACTORY", "").strip(),
        detector_mode=os.getenv("CAT_DOOR_DETECTOR_MODE", "disabled"),
        detector_command=os.getenv("CAT_DOOR_DETECTOR_COMMAND", ""),
        detector_command_timeout_seconds=int(
            os.getenv("CAT_DOOR_DETECTOR_COMMAND_TIMEOUT_SECONDS", "30")
        ),
        detection_confidence_threshold=float(
            os.getenv("CAT_DOOR_DETECTION_CONFIDENCE_THRESHOLD", "0.5")
        ),
        enable_gpio_hardware=_get_bool_env("CAT_DOOR_ENABLE_GPIO_HARDWARE", True),
        enable_servo_hardware=_get_bool_env("CAT_DOOR_ENABLE_SERVO_HARDWARE", False),
        reed_closed_when_pressed=_get_bool_env(
            "CAT_DOOR_REED_CLOSED_WHEN_PRESSED",
            True,
        ),
        servo_open_value=float(os.getenv("CAT_DOOR_SERVO_OPEN_VALUE", "1.0")),
        servo_closed_value=float(os.getenv("CAT_DOOR_SERVO_CLOSED_VALUE", "-1.0")),
    )
