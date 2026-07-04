"""Configuration loading for the cat door application."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .door_controller import LATCH_CLOSED, LATCH_OPEN


@dataclass(frozen=True)
class AppConfig:
    """Central application configuration loaded from environment variables."""

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    live_stream_url: str = ""
    stream_health_url: str = ""
    camera_snapshot_url: str = ""
    stream_host: str = "0.0.0.0"
    stream_port: int = 8080
    stream_width: int = 640
    stream_height: int = 480
    stream_fps: int = 10
    pir_pin: int = 17
    servo_pin: int = 14
    image_output_dir: str = "captures"
    camera_capture_timeout_ms: int = 250
    motion_cooldown_seconds: int = 10
    door_open_seconds: int = 30
    approval_timeout_seconds: int = 60
    monitor_poll_interval_seconds: float = 0.2
    pir_settle_seconds: float = 3.0
    pir_snapshot_delay_seconds: float = 2.0
    gpiozero_pin_factory: str = ""
    enable_gpio_hardware: bool = True
    enable_servo_hardware: bool = False
    latch_open_angle: int = LATCH_OPEN
    latch_closed_angle: int = LATCH_CLOSED


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
    # Loading the package-local .env matches the current project layout.
    _load_dotenv(Path(__file__).with_name(".env"))
    # Loading a cwd .env keeps old local setups working when no package value exists.
    _load_dotenv(Path(".env"))

    return AppConfig(
        telegram_bot_token=os.getenv("CAT_DOOR_TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("CAT_DOOR_TELEGRAM_CHAT_ID", ""),
        live_stream_url=os.getenv("CAT_DOOR_LIVE_STREAM_URL", "").strip(),
        stream_health_url=os.getenv("CAT_DOOR_STREAM_HEALTH_URL", "").strip(),
        camera_snapshot_url=os.getenv("CAT_DOOR_CAMERA_SNAPSHOT_URL", "").strip(),
        stream_host=os.getenv("CAT_DOOR_STREAM_HOST", "0.0.0.0"),
        stream_port=int(os.getenv("CAT_DOOR_STREAM_PORT", "8080")),
        stream_width=int(os.getenv("CAT_DOOR_STREAM_WIDTH", "640")),
        stream_height=int(os.getenv("CAT_DOOR_STREAM_HEIGHT", "480")),
        stream_fps=int(os.getenv("CAT_DOOR_STREAM_FPS", "10")),
        pir_pin=int(os.getenv("CAT_DOOR_PIR_PIN", "17")),
        servo_pin=int(os.getenv("CAT_DOOR_SERVO_PIN", "14")),
        image_output_dir=os.getenv("CAT_DOOR_IMAGE_OUTPUT_DIR", "captures"),
        camera_capture_timeout_ms=int(
            os.getenv("CAT_DOOR_CAMERA_CAPTURE_TIMEOUT_MS", "250")
        ),
        motion_cooldown_seconds=int(
            os.getenv("CAT_DOOR_MOTION_COOLDOWN_SECONDS", "10")
        ),
        door_open_seconds=int(os.getenv("CAT_DOOR_DOOR_OPEN_SECONDS", "30")),
        approval_timeout_seconds=int(
            os.getenv("CAT_DOOR_APPROVAL_TIMEOUT_SECONDS", "60")
        ),
        monitor_poll_interval_seconds=float(
            os.getenv("CAT_DOOR_MONITOR_POLL_INTERVAL_SECONDS", "0.2")
        ),
        pir_settle_seconds=float(os.getenv("CAT_DOOR_PIR_SETTLE_SECONDS", "3.0")),
        pir_snapshot_delay_seconds=float(
            os.getenv("CAT_DOOR_PIR_SNAPSHOT_DELAY_SECONDS", "2.0")
        ),
        gpiozero_pin_factory=os.getenv("CAT_DOOR_GPIOZERO_PIN_FACTORY", "").strip(),
        enable_gpio_hardware=_get_bool_env("CAT_DOOR_ENABLE_GPIO_HARDWARE", True),
        enable_servo_hardware=_get_bool_env("CAT_DOOR_ENABLE_SERVO_HARDWARE", False),
        latch_open_angle=int(
            os.getenv(
                "CAT_DOOR_LATCH_OPEN_ANGLE",
                os.getenv("CAT_DOOR_SERVO_OPEN_ANGLE", str(LATCH_OPEN)),
            )
        ),
        latch_closed_angle=int(
            os.getenv(
                "CAT_DOOR_LATCH_CLOSED_ANGLE",
                os.getenv("CAT_DOOR_SERVO_CLOSED_ANGLE", str(LATCH_CLOSED)),
            )
        ),
    )
