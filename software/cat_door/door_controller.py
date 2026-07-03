"""Door actuator logic."""

from __future__ import annotations

import time

try:
    from gpiozero import AngularServo
except Exception:  # pragma: no cover - depends on host hardware support
    AngularServo = None


LATCH_OPEN = 110
LATCH_CLOSED = 180
SERVO_SETTLE_SECONDS = 0.5


class DoorController:
    """Controls how the cat door opens and closes."""

    def __init__(
        self,
        servo_pin: int,
        open_duration_seconds: int,
        enable_hardware: bool,
        open_angle: int = LATCH_OPEN,
        closed_angle: int = LATCH_CLOSED,
    ) -> None:
        self.servo_pin = servo_pin
        self.open_duration_seconds = open_duration_seconds
        self.enable_hardware = enable_hardware
        self.open_angle = open_angle
        self.closed_angle = closed_angle
        self._servo = None
        self._backend_error: str | None = None

        if not enable_hardware:
            self._backend_error = "Servo hardware access disabled by configuration."
            return

        if AngularServo is None:
            self._backend_error = "gpiozero AngularServo backend is unavailable."
            return

        try:
            self._servo = AngularServo(
                servo_pin,
                min_angle=0,
                max_angle=180,
                min_pulse_width=0.0005,
                max_pulse_width=0.0026,
            )
            self.close()
        except Exception as exc:  # pragma: no cover - depends on host hardware
            self._backend_error = str(exc)

    def is_available(self) -> bool:
        return self._servo is not None

    def describe(self) -> str:
        if self.is_available():
            return f"Servo controller on GPIO {self.servo_pin}"
        return f"Servo controller in simulation mode: {self._backend_error}"

    def close(self) -> None:
        if self._servo:
            self._move_to_angle(self.closed_angle)

    def open_latch(self) -> None:
        """Move the latch to the calibrated open angle."""
        if self._servo:
            self._move_to_angle(self.open_angle)
            return

        print(f"[door] Simulating latch open on servo pin {self.servo_pin}")

    def close_latch(self) -> None:
        """Move the latch to the calibrated closed angle."""
        if self._servo:
            self._move_to_angle(self.closed_angle)
            return

        print(f"[door] Simulating latch close on servo pin {self.servo_pin}")

    def open_temporarily(self) -> None:
        """Open the flap for a fixed interval, then close it again."""
        if self._servo:
            self.open_latch()
            time.sleep(self.open_duration_seconds)
            self.close_latch()
            return

        # The simulation path keeps local development usable before hardware is
        # wired up. The same workflow can then drive the real servo on the Pi.
        print(
            f"[door] Simulating open on servo pin {self.servo_pin} for "
            f"{self.open_duration_seconds} seconds"
        )
        time.sleep(self.open_duration_seconds)
        print("[door] Simulating close")

    def _move_to_angle(self, angle: int) -> None:
        """Move the SG90 briefly, then detach PWM to reduce jitter."""
        if not self._servo:
            return

        self._servo.angle = angle
        time.sleep(SERVO_SETTLE_SECONDS)
        self._servo.detach()
