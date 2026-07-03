# Hookup And Run

This document is the deployment checklist for the Raspberry Pi build.

## 1. Deployment target

The deployment target is a Raspberry Pi system with:

- Raspberry Pi OS
- Pi camera connected and enabled
- PIR motion sensor
- servo or actuator controller for the door
- internet access for Telegram

## 2. Software setup on the Raspberry Pi

From the `software/` directory on the Pi, the preferred setup command is:

```bash
./setup_pi.sh
```

Equivalent manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 3. Required `.env` values

Populate these values before running the system:

```env
CAT_DOOR_TELEGRAM_BOT_TOKEN=
CAT_DOOR_TELEGRAM_CHAT_ID=
CAT_DOOR_PIR_PIN=17
CAT_DOOR_SERVO_PIN=18
CAT_DOOR_GPIOZERO_PIN_FACTORY=lgpio
CAT_DOOR_ENABLE_GPIO_HARDWARE=true
CAT_DOOR_ENABLE_SERVO_HARDWARE=true
```

PIR motion is treated as a meaningful cat-door event. The operator makes the
open/close decision from the Telegram photo or live camera view.

For Pi bring-up before hardware is attached, temporarily use:

```env
CAT_DOOR_ENABLE_GPIO_HARDWARE=false
CAT_DOOR_ENABLE_SERVO_HARDWARE=false
```

## 4. Hardware hookup notes

- Connect the Pi camera to a camera ribbon port on the Raspberry Pi
- Connect the PIR output wire to `CAT_DOOR_PIR_PIN`
- Connect the servo signal wire to `CAT_DOOR_SERVO_PIN`
- Share ground between the Raspberry Pi and the servo power supply
- Do not power the servo directly from a GPIO signal pin

## 5. Runtime verification order

Run these checks from the `software/` directory in this order:

```bash
./run_cat_door.sh status
./run_cat_door.sh text-test
./run_cat_door.sh approval-test
./run_cat_door.sh photo-test
./run_cat_door.sh monitor-once
```

Use this command only after the single-event test is successful:

```bash
./run_cat_door.sh monitor-loop
```

To keep the system running automatically after boot once validation is done:

```bash
./install_cat_door_service.sh
```

## 6. Expected results

### `status`

Confirms whether the PIR and servo controller backends are available.

### `text-test`

Sends a Telegram text message to verify network connectivity and bot access.

### `approval-test`

Sends Telegram approval buttons and confirms that a button press is received by
the application.

### `photo-test`

Captures a real image with the first available Raspberry Pi camera command
(`rpicam-still`, `libcamera-still`, or `raspistill`), sends it to Telegram,
and runs the approval-button flow.

### `monitor-once`

Waits for one PIR event, captures an image, sends it to Telegram, and opens the
door only when the operator approves the event.

## 7. Expected live workflow

1. PIR sensor triggers
2. Camera captures a snapshot
3. Telegram sends the snapshot to the operator
4. Operator selects `Open Door` or `Keep Closed`
5. Door opens temporarily when approved
