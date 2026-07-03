# Telegram Setup

This procedure validates the Telegram notification channel before Raspberry Pi
hardware testing.

## 1. Create the bot

In Telegram:

1. Open `@BotFather`
2. Send `/newbot`
3. Choose a display name
4. Choose a username ending in `bot`
5. Copy the bot token

## 2. Start a chat with the bot

Open the bot and send a plain message such as:

`hello cat door`

## 3. Prepare the local environment

From the `software/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Populate the bot token in `.env`:

```env
CAT_DOOR_TELEGRAM_BOT_TOKEN=your-token-here
```

Leave `CAT_DOOR_TELEGRAM_CHAT_ID` blank for the next step.

## 4. Discover the chat ID

Run:

```bash
./run_cat_door.sh show-chat-id
```

Store the discovered value in `.env`:

```env
CAT_DOOR_TELEGRAM_CHAT_ID=123456789
```

## 5. Validate text delivery

Run:

```bash
./run_cat_door.sh text-test
```

Expected result:

- the terminal reports successful delivery
- the Telegram chat receives a confirmation message

## 6. Validate approval buttons

Run:

```bash
./run_cat_door.sh approval-test
```

Expected result:

- the Telegram chat receives `Open Door` and `Keep Closed` buttons
- selecting a button sends the action back to the application
- the terminal prints the selected action

## 7. Validate camera-photo delivery on the Raspberry Pi

Run this step on the Raspberry Pi after camera setup:

```bash
./run_cat_door.sh photo-test
```

Expected result:

- the Raspberry Pi captures a snapshot
- the Telegram chat receives the image with approval buttons
