"""Camera capture helpers."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shlex
import shutil
import subprocess


class CameraError(RuntimeError):
    """Raised when a snapshot cannot be captured."""


class Camera:
    """Captures still images using Raspberry Pi camera tools."""

    def __init__(self, output_dir: str, capture_timeout_ms: int = 250) -> None:
        self.output_dir = Path(output_dir)
        self.capture_timeout_ms = max(0, capture_timeout_ms)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(self) -> Path:
        """Capture a still image and return the saved file path."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"snapshot-{timestamp}.jpg"

        command = self._build_camera_command(output_path)
        process_timeout_seconds = max(10.0, self.capture_timeout_ms / 1000 + 10.0)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=process_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise CameraError(
                "Camera command timed out.\n"
                f"Command: {shlex.join(command)}\n"
                f"Timeout: {process_timeout_seconds:.1f} seconds"
            ) from exc
        except OSError as exc:
            raise CameraError(
                "Camera command failed to start.\n"
                f"Command: {shlex.join(command)}\n"
                f"Error: {exc}"
            ) from exc

        if completed.returncode != 0:
            raise CameraError(self._format_command_failure(command, completed))

        if not output_path.exists():
            raise CameraError(
                "Camera command finished but did not create an image.\n"
                f"Command: {shlex.join(command)}\n"
                f"Expected output: {output_path}"
            )

        return output_path

    def _build_camera_command(self, output_path: Path) -> list[str]:
        """Choose the first supported Pi camera CLI on the current machine."""
        if shutil.which("rpicam-still"):
            return [
                "rpicam-still",
                "--nopreview",
                "--timeout",
                str(self.capture_timeout_ms),
                "--output",
                str(output_path),
            ]

        if shutil.which("libcamera-still"):
            return [
                "libcamera-still",
                "--nopreview",
                "--timeout",
                str(self.capture_timeout_ms),
                "--output",
                str(output_path),
            ]

        if shutil.which("raspistill"):
            return [
                "raspistill",
                "-n",
                "-t",
                str(self.capture_timeout_ms),
                "-o",
                str(output_path),
            ]

        raise CameraError(
            "No Raspberry Pi still-image command was found. Expected one of "
            "rpicam-still, libcamera-still, or raspistill."
        )

    @staticmethod
    def _format_command_failure(
        command: list[str],
        completed: subprocess.CompletedProcess[str],
    ) -> str:
        """Build a useful error message from a failed camera command."""
        details = [
            "Camera command failed.",
            f"Command: {shlex.join(command)}",
            f"Return code: {completed.returncode}",
        ]

        stderr = completed.stderr.strip()
        if stderr:
            details.append(f"stderr: {Camera._shorten_output(stderr)}")

        stdout = completed.stdout.strip()
        if stdout:
            details.append(f"stdout: {Camera._shorten_output(stdout)}")

        return "\n".join(details)

    @staticmethod
    def _shorten_output(output: str, limit: int = 1000) -> str:
        """Keep command output readable in terminal logs and Telegram messages."""
        if len(output) <= limit:
            return output

        return output[-limit:]
