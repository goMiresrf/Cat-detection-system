"""Sensor abstractions for the cat door."""

from __future__ import annotations

import time

try:
    from gpiozero import DigitalInputDevice
except Exception:  # pragma: no cover - depends on host hardware support
    DigitalInputDevice = None


class PirSensor:
    """Wrap a PIR motion sensor with a simulation-friendly fallback."""

    def __init__(
        self,
        pin: int,
        enable_hardware: bool,
        settle_seconds: float,
    ) -> None:
        self.pin = pin
        self.enable_hardware = enable_hardware
        self.settle_seconds = settle_seconds
        self._sensor = None
        self._backend_error: str | None = None

        # The class falls back to a "not available" state on non-Pi machines so
        # the rest of the software can still be developed and tested locally.
        if not enable_hardware:
            self._backend_error = "GPIO hardware access disabled by configuration."
            return

        if DigitalInputDevice is None:
            self._backend_error = "gpiozero DigitalInputDevice backend is unavailable."
            return

        try:
            self._sensor = DigitalInputDevice(pin, pull_up=False)
            if settle_seconds > 0:
                time.sleep(settle_seconds)
        except Exception as exc:  # pragma: no cover - depends on host hardware
            self._backend_error = str(exc)

    def is_available(self) -> bool:
        return self._sensor is not None

    def describe(self) -> str:
        if self.is_available():
            return f"PIR sensor digital input on GPIO {self.pin}"
        return f"PIR sensor unavailable: {self._backend_error}"

    def motion_detected(self) -> bool:
        if not self._sensor:
            return False
        return bool(self._sensor.is_active)

    def wait_for_motion(self, timeout_seconds: float | None) -> bool:
        """Wait until the PIR output goes active."""
        if not self._sensor:
            return False

        deadline = None
        if timeout_seconds is not None:
            deadline = time.monotonic() + timeout_seconds

        while True:
            if self.motion_detected():
                return True

            if deadline is not None and time.monotonic() >= deadline:
                return False

            time.sleep(0.05)
