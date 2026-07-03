"""Application entry point."""

from __future__ import annotations

import argparse
import os

from .camera import Camera
from .config import load_config
from .door_controller import DoorController
from .sensors import PirSensor
from .telegram_bot import TelegramBot
from .workflow import CatDoorWorkflow


def build_parser() -> argparse.ArgumentParser:
    """Create the small CLI used for milestone-by-milestone testing."""
    parser = argparse.ArgumentParser(description="Smart cat door control app")
    parser.add_argument(
        "mode",
        choices=[
            "show-chat-id",
            "status",
            "debug-updates",
            "text-test",
            "approval-test",
            "photo-test",
            "monitor-once",
            "monitor-loop",
        ],
        help="Setup or test mode to run",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config()

    if config.gpiozero_pin_factory:
        os.environ.setdefault("GPIOZERO_PIN_FACTORY", config.gpiozero_pin_factory)

    # Build each subsystem once, then hand the assembled runtime into the
    # workflow layer that coordinates the event flow.
    workflow = CatDoorWorkflow(
        camera=Camera(
            config.image_output_dir,
            capture_timeout_ms=config.camera_capture_timeout_ms,
        ),
        telegram_bot=TelegramBot(
            token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id,
        ),
        door_controller=DoorController(
            servo_pin=config.servo_pin,
            open_duration_seconds=config.door_open_seconds,
            enable_hardware=config.enable_servo_hardware,
            open_value=config.servo_open_value,
            closed_value=config.servo_closed_value,
        ),
        pir_sensor=PirSensor(
            pin=config.pir_pin,
            enable_hardware=config.enable_gpio_hardware,
            settle_seconds=config.pir_settle_seconds,
        ),
        motion_cooldown_seconds=config.motion_cooldown_seconds,
        approval_timeout_seconds=config.approval_timeout_seconds,
        live_stream_url=config.live_stream_url,
        monitor_poll_interval_seconds=config.monitor_poll_interval_seconds,
        gpiozero_pin_factory=config.gpiozero_pin_factory,
    )

    if args.mode == "show-chat-id":
        workflow.show_latest_chat_id()
    elif args.mode == "status":
        workflow.show_runtime_status()
    elif args.mode == "debug-updates":
        workflow.debug_updates()
    elif args.mode == "text-test":
        workflow.run_text_test()
    elif args.mode == "approval-test":
        workflow.run_approval_test()
    elif args.mode == "monitor-once":
        workflow.run_monitor_once()
    elif args.mode == "monitor-loop":
        workflow.run_monitor_loop()
    else:
        workflow.run_photo_test()


if __name__ == "__main__":
    main()
