"""Camera capture helpers."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shlex
import shutil
import subprocess
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class CameraError(RuntimeError):
    """Raised when a snapshot cannot be captured."""


class Camera:
    """Captures still images using Raspberry Pi camera tools."""

    def __init__(
        self,
        output_dir: str,
        capture_timeout_ms: int = 250,
        snapshot_url: str = "",
        snapshot_timeout_seconds: float = 5.0,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.capture_timeout_ms = max(0, capture_timeout_ms)
        self.snapshot_url = snapshot_url.strip()
        self.snapshot_timeout_seconds = snapshot_timeout_seconds
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(self) -> Path:
        """Capture a still image and return the saved file path."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_path = self.output_dir / f"snapshot-{timestamp}.jpg"

        if self.snapshot_url:
            try:
                return self._capture_snapshot_from_url(output_path)
            except CameraError as exc:
                print("[camera] Stream snapshot failed; falling back to camera command.")
                print(exc)

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

    def _capture_snapshot_from_url(self, output_path: Path) -> Path:
        """Save the latest frame from the live stream service."""
        request = Request(
            self.snapshot_url,
            headers={"User-Agent": "cat-door-camera/1.0"},
        )

        try:
            with urlopen(request, timeout=self.snapshot_timeout_seconds) as response:
                status = getattr(response, "status", 200)
                data = response.read()
        except HTTPError as exc:
            raise CameraError(
                "Snapshot URL returned an HTTP error.\n"
                f"URL: {self.snapshot_url}\n"
                f"Status: {exc.code}"
            ) from exc
        except URLError as exc:
            raise CameraError(
                "Snapshot URL could not be reached.\n"
                f"URL: {self.snapshot_url}\n"
                f"Error: {exc.reason}"
            ) from exc
        except OSError as exc:
            raise CameraError(
                "Snapshot URL request failed.\n"
                f"URL: {self.snapshot_url}\n"
                f"Error: {exc}"
            ) from exc

        if status >= 400:
            raise CameraError(
                "Snapshot URL returned an unsuccessful status.\n"
                f"URL: {self.snapshot_url}\n"
                f"Status: {status}"
            )

        if not data:
            raise CameraError(
                "Snapshot URL returned an empty response.\n"
                f"URL: {self.snapshot_url}"
            )

        if not data.startswith(b"\xff\xd8"):
            raise CameraError(
                "Snapshot URL did not return a JPEG image.\n"
                f"URL: {self.snapshot_url}"
            )

        output_path.write_bytes(data)
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
