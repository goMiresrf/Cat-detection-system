# Software Delivery Plan

## Objective

Deliver the Raspberry Pi application for the smart cat door in testable
milestones.

## Milestone status

### Milestone 1: Local foundation

- [x] Create the software package structure
- [x] Configure the Python virtual environment workflow
- [x] Install runtime dependencies
- [x] Load runtime settings from environment variables

### Milestone 2: Telegram connectivity

- [x] Create the Telegram bot
- [x] Store the bot token in local configuration
- [x] Discover the private chat ID
- [x] Verify inbound update retrieval from Telegram
- [x] Verify outbound text-message delivery to Telegram

### Milestone 3: Telegram approval flow

- [x] Add inline action buttons for approval decisions
- [x] Add polling-based callback handling
- [x] Verify end-to-end approval action receipt from Telegram

### Milestone 4: Camera notification flow

- [x] Implement the software path from image capture to Telegram approval
- [x] Verify `rpicam-still` snapshot capture on the Raspberry Pi
- [x] Verify camera-photo delivery to Telegram on the Raspberry Pi

### Milestone 5: Sensor-triggered workflow

- [x] Integrate PIR-triggered event handling in software
- [x] Add event cooldown handling
- [x] Validate PIR-triggered events on the Raspberry Pi

### Milestone 6: Detection workflow

- [x] Add detector-mode handling and confidence evaluation
- [x] Add notification rules for motion events and cat-likely events
- [ ] Confirm the final production detector configuration

### Milestone 7: Door control workflow

- [x] Add actuator-control abstraction
- [x] Add reed-switch reporting after the close cycle
- [ ] Verify timed open and close behavior on the Raspberry Pi
- [ ] Verify reed-switch closed confirmation on the Raspberry Pi

## Current release state

- Local software workflow is complete for Telegram setup and approval testing
- First live deployment mode is manual Telegram approval with detector disabled
- Remaining work is hardware hookup and Raspberry Pi validation

## Outstanding engineering decisions

- [ ] Confirm the final actuator hardware: servo or motor driver
- [ ] Confirm whether production behavior should notify on all motion events
- [ ] Confirm whether Raspberry Pi 5 remains the final deployment board
- [ ] Confirm whether known-cat identification is required
