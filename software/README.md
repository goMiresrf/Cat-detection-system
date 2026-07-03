# Cat Door Software

This directory contains the software package for the smart cat door system.
The application runs the notification and approval workflow that connects the
camera, PIR sensor, servo controller, and Telegram bot.

## Current operating mode

The implemented operating mode is:

1. PIR sensor detects motion
2. Raspberry Pi captures a snapshot
3. Telegram sends the image to the operator
4. Operator selects `Open Door` or `Keep Closed`
5. Door opens only after approval

The software treats PIR motion as a meaningful cat-door event. It does not try
to classify whether the image contains a cat; the operator decides from the
Telegram photo or live camera view.

The package also includes deployment helpers so the Raspberry Pi handoff stays
lightweight:

- `setup_pi.sh`: creates the venv, installs dependencies, and seeds `.env`
- `install_cat_door_service.sh`: installs `monitor-loop` as a systemd service

## Project documents

- `SOFTWARE_PLAN.md`: architecture and system scope
- `DELIVERY_PLAN.md`: milestone tracking
- `VALIDATION_LOG.md`: local validation history
- `TELEGRAM_SETUP.md`: Telegram bot setup and approval-channel validation
- `HOOKUP_AND_RUN.md`: Raspberry Pi deployment checklist
- `PI_HANDOFF.md`: teammate handoff for hardware hookup and live testing
- `SOFTWARE_STATUS_REPORT.md`: concise project status summary

## Source layout

- `cat_door/main.py`: command-line entry point
- `cat_door/workflow.py`: end-to-end event workflow
- `cat_door/config.py`: `.env` loading and runtime settings
- `cat_door/camera.py`: `rpicam-still` snapshot capture
- `cat_door/telegram_bot.py`: Telegram messaging and callback handling
- `cat_door/sensors.py`: PIR sensor access
- `cat_door/door_controller.py`: servo control and simulation fallback
- `setup_pi.sh`: Raspberry Pi bootstrap helper
- `install_cat_door_service.sh`: boot-time monitor installer

## How to run the software

Run commands from the `software/` directory.

Preferred wrapper:

```bash
./run_cat_door.sh <mode>
```

Preferred Raspberry Pi setup:

```bash
./setup_pi.sh
```

Direct module form:

```bash
.venv/bin/python -m cat_door.main <mode>
```

Do not run `camera.py`, `workflow.py`, or the other module files directly.

## Available commands

```bash
./run_cat_door.sh show-chat-id
./run_cat_door.sh status
./run_cat_door.sh debug-updates
./run_cat_door.sh text-test
./run_cat_door.sh approval-test
./run_cat_door.sh photo-test
./run_cat_door.sh monitor-once
./run_cat_door.sh monitor-loop
```

## File ownership guide

- Change camera capture settings in `cat_door/camera.py`
- Change Telegram messages or approval buttons in `cat_door/telegram_bot.py`
- Change workflow logic in `cat_door/workflow.py`
- Change PIR or servo settings in `.env` and `cat_door/config.py`
- Change hardware wrappers in `cat_door/sensors.py` and `cat_door/door_controller.py`
