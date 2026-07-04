from gpiozero import Button
from signal import pause

# Set up GPIO 22 (Physical Pin 15). 
# pull_up=False forces it to sit at 0V until it gets a 3.3V spike.
test_pin = Button(17, pull_up=False)

def on_high():
    print(" HIGH! The Pi successfully received 3.3V")

def on_low():
    print("LOW. The pin dropped back to 0V")

# Attach the events
test_pin.when_pressed = on_high
test_pin.when_released = on_low

print("Listening for voltage changes on GPIO 22 (Physical Pin 15)...")
print("Press Ctrl+C to exit.")

# Keep the script running
pause()
