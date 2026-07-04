# Cat Door Software

This directory contains the software package for the smart cat door system.
The application runs the notification and approval workflow that connects the
camera, PIR sensor, servo controller, and Telegram bot.

## Current operating mode

The implemented operating mode is:

1. PIR sensor detects motion
2. Raspberry Pi captures a snapshot
3. Telegram sends the image to the operator
4. Operator selects `Open Door`, `Close Door`, or `Open Camera`
5. Door opens only after approval, then closes automatically after the configured delay

The software treats PIR motion as a meaningful cat-door event. It does not try
to classify whether the image contains a cat; the operator decides from the
Telegram photo or live camera view.

The package also includes deployment helpers so the Raspberry Pi handoff stays
lightweight:

- `Shell/setup_pi.sh`: creates the venv, installs dependencies, and seeds `cat_door/.env`
- `Shell/install_cat_door_service.sh`: installs `monitor-loop` as a systemd service
- `Shell/install_camera_stream_service.sh`: installs the live camera stream as a systemd service
- `Shell/install_restart_sudoers.sh`: allows Telegram to restart only the cat-door services

## Project documents

- `Setup guide/TELEGRAM_SETUP.md`: Telegram bot setup and control validation
- `Setup guide/HOOKUP_AND_RUN.md`: Raspberry Pi deployment checklist

## Source layout

- `cat_door/main.py`: command-line entry point
- `cat_door/workflow.py`: end-to-end event workflow
- `cat_door/config.py`: `.env` loading and runtime settings
- `cat_door/camera.py`: `rpicam-still` snapshot capture
- `cat_door/live_stream.py`: lightweight MJPEG live camera server
- `cat_door/telegram_bot.py`: Telegram messaging and callback handling
- `cat_door/sensors.py`: PIR sensor access
- `cat_door/door_controller.py`: servo control and simulation fallback
- `Shell/setup_pi.sh`: Raspberry Pi bootstrap helper
- `Shell/start_camera_stream.sh`: starts the live camera server
- `Shell/install_cat_door_service.sh`: boot-time monitor installer
- `Shell/install_camera_stream_service.sh`: boot-time camera stream installer
- `cat_door/.env.example`: copyable runtime configuration template

## How to run the software

Run commands from the `software/` directory.

Preferred wrapper:

```bash
./Shell/run_cat_door.sh <mode>
```

Preferred Raspberry Pi setup:

```bash
./Shell/setup_pi.sh
```

Direct module form:

```bash
.venv/bin/python -m cat_door.main <mode>
```

Do not run `camera.py`, `workflow.py`, or the other module files directly.

## Available commands

```bash
./Shell/run_cat_door.sh show-chat-id
./Shell/run_cat_door.sh status
./Shell/run_cat_door.sh debug-updates
./Shell/run_cat_door.sh text-test
./Shell/run_cat_door.sh approval-test
./Shell/run_cat_door.sh photo-test
./Shell/run_cat_door.sh pir-watch
./Shell/run_cat_door.sh monitor-once
./Shell/run_cat_door.sh monitor-loop
```

Camera stream:

```bash
./Shell/start_camera_stream.sh
```

## File ownership guide

- Change camera capture settings in `cat_door/camera.py`
- Change Telegram messages or approval buttons in `cat_door/telegram_bot.py`
- Change workflow logic in `cat_door/workflow.py`
- Change PIR or servo settings in `cat_door/.env` and `cat_door/config.py`
- Change hardware wrappers in `cat_door/sensors.py` and `cat_door/door_controller.py`
