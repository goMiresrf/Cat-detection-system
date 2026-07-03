from gpiozero import AngularServo
from time import sleep

SERVO_GPIO = 18

servo = AngularServo(
    SERVO_GPIO,
    min_angle=0,
    max_angle=180,
    min_pulse_width=0.0005,
    max_pulse_width=0.0026   # slightly beyond normal SG90 max
)

print("Type an angle from 0 to 180.")
print("180 should now go a bit further than before.")
print("Type q to quit.")

while True:
    command = input("Angle: ")

    if command.lower() == "q":
        break

    try:
        angle = int(command)

        if angle < 0 or angle > 180:
            print("Use 0–180 only.")
            continue

        servo.angle = angle
        sleep(0.5)
        servo.detach()

        print(f"Moved to {angle} degrees and detached.")

    except ValueError:
        print("Type a number or q.")