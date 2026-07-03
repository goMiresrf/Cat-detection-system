"""Sensor abstractions for the cat door."""

from __future__ import annotations

import time

try:
    from gpiozero import MotionSensor
except Exception:  # pragma: no cover - depends on host hardware support
    MotionSensor = None


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
        self._arm_calm_seconds = 2.0
        self._arm_timeout_seconds = 30.0

        # The class falls back to a "not available" state on non-Pi machines so
        # the rest of the software can still be developed and tested locally.
        if not enable_hardware:
            self._backend_error = "GPIO hardware access disabled by configuration."
            return

        if MotionSensor is None:
            self._backend_error = "gpiozero MotionSensor backend is unavailable."
            return

        try:
            self._sensor = MotionSensor(pin)
            if settle_seconds > 0:
                time.sleep(settle_seconds)
        except Exception as exc:  # pragma: no cover - depends on host hardware
            self._backend_error = str(exc)

    def is_available(self) -> bool:
        return self._sensor is not None

    def describe(self) -> str:
        if self.is_available():
            return f"PIR sensor on GPIO {self.pin}"
        return f"PIR sensor unavailable: {self._backend_error}"

    def motion_detected(self) -> bool:
        if not self._sensor:
            return False
        return bool(self._sensor.motion_detected)

    def wait_for_motion(self, timeout_seconds: float | None) -> bool:
        """Wait for a fresh motion event after the PIR has gone calm."""
        if not self._sensor:
            return False

        if not self._wait_until_calm(
            calm_seconds=self._arm_calm_seconds,
            timeout_seconds=self._arm_timeout_seconds,
        ):
            self._backend_error = (
                "PIR sensor did not become calm before arming. "
                "Try reducing sensitivity or moving heat sources away."
            )
            return False

        self._sensor.wait_for_motion(timeout=timeout_seconds)
        return bool(self._sensor.motion_detected)

    def _wait_until_calm(
        self,
        calm_seconds: float,
        timeout_seconds: float,
    ) -> bool:
        """Require a short calm period before treating motion as a fresh event."""
        if not self._sensor:
            return False

        deadline = time.monotonic() + timeout_seconds
        calm_start: float | None = None

        while time.monotonic() < deadline:
            if self._sensor.motion_detected:
                calm_start = None
            else:
                if calm_start is None:
                    calm_start = time.monotonic()
                elif time.monotonic() - calm_start >= calm_seconds:
                    return True

            time.sleep(0.1)

        return False
