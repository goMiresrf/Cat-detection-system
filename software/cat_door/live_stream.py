"""Small MJPEG live camera server for the cat door."""

from __future__ import annotations

from dataclasses import dataclass
import io
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from typing import Callable
from urllib.parse import urlparse

from .config import load_config


@dataclass(frozen=True)
class StreamConfig:
    """Runtime settings for the live camera server."""

    host: str
    port: int
    width: int
    height: int
    fps: int


class StreamingOutput(io.BufferedIOBase):
    """Thread-safe handoff point between Picamera2 and HTTP clients."""

    def __init__(self) -> None:
        self.frame: bytes | None = None
        self.frame_timestamp: float | None = None
        self.condition = threading.Condition()

    def writable(self) -> bool:
        return True

    def write(self, buffer: bytes | bytearray | memoryview) -> int:
        frame = bytes(buffer)
        with self.condition:
            self.frame = frame
            self.frame_timestamp = time.monotonic()
            self.condition.notify_all()
        return len(frame)

    def wait_for_frame(self, timeout_seconds: float = 5.0) -> bytes | None:
        """Return the latest JPEG frame, waiting briefly if needed."""
        deadline = time.monotonic() + timeout_seconds
        with self.condition:
            while self.frame is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.condition.wait(timeout=remaining)

            return self.frame


def _build_handler(output: StreamingOutput) -> type[BaseHTTPRequestHandler]:
    class CameraStreamHandler(BaseHTTPRequestHandler):
        server_version = "CatDoorCamera/1.0"

        def do_GET(self) -> None:
            path = urlparse(self.path).path

            if path in {"/", "/index.html"}:
                self._send_index()
            elif path == "/health":
                self._send_health()
            elif path == "/snapshot.jpg":
                self._send_snapshot()
            elif path == "/stream.mjpg":
                self._send_stream()
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Not found")

        def log_message(self, format: str, *args: object) -> None:
            print(f"[stream] {self.address_string()} - {format % args}")

        def _send_index(self) -> None:
            body = (
                "<!doctype html>"
                "<html><head>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<title>Cat Door Camera</title>"
                "<style>"
                "body{margin:0;background:#111;color:#eee;font-family:sans-serif;}"
                "header{padding:12px 16px;background:#1d1d1d;}"
                "img{display:block;width:100%;height:auto;}"
                "</style>"
                "</head><body>"
                "<header>Cat Door Camera</header>"
                "<img src='/stream.mjpg' alt='Live cat door camera'>"
                "</body></html>"
            ).encode("utf-8")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_health(self) -> None:
            if output.frame is None:
                body = b"warming_up\n"
                self.send_response(HTTPStatus.SERVICE_UNAVAILABLE)
            else:
                body = b"ok\n"
                self.send_response(HTTPStatus.OK)

            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_snapshot(self) -> None:
            frame = output.wait_for_frame()
            if frame is None:
                self.send_error(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "Camera stream is still warming up.",
                )
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(frame)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(frame)

        def _send_stream(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Age", "0")
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=FRAME",
            )
            self.end_headers()

            try:
                while True:
                    frame = output.wait_for_frame()
                    if frame is None:
                        continue

                    self.wfile.write(b"--FRAME\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode())
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                return

    return CameraStreamHandler


def _load_stream_config() -> StreamConfig:
    app_config = load_config()
    return StreamConfig(
        host=app_config.stream_host,
        port=app_config.stream_port,
        width=app_config.stream_width,
        height=app_config.stream_height,
        fps=app_config.stream_fps,
    )


def _create_picamera2(config: StreamConfig) -> tuple[object, StreamingOutput]:
    try:
        from picamera2 import Picamera2
        from picamera2.encoders import JpegEncoder
        from picamera2.outputs import FileOutput
    except ImportError as exc:
        raise RuntimeError(
            "Picamera2 is not available. On Raspberry Pi OS, install "
            "python3-picamera2 and create the venv with system site packages."
        ) from exc

    output = StreamingOutput()
    picam2 = Picamera2()
    camera_config = picam2.create_video_configuration(
        main={"size": (config.width, config.height)}
    )
    picam2.configure(camera_config)

    if config.fps > 0:
        frame_duration_us = int(1_000_000 / config.fps)
        try:
            picam2.set_controls(
                {"FrameDurationLimits": (frame_duration_us, frame_duration_us)}
            )
        except Exception as exc:
            print(f"[stream] Could not set camera FPS limit: {exc}")

    picam2.start_recording(JpegEncoder(), FileOutput(output))
    return picam2, output


def serve_forever(
    config: StreamConfig | None = None,
    camera_factory: Callable[[StreamConfig], tuple[object, StreamingOutput]]
    | None = None,
) -> None:
    """Start the Picamera2 MJPEG server and block until interrupted."""
    stream_config = config or _load_stream_config()
    factory = camera_factory or _create_picamera2
    picam2, output = factory(stream_config)
    server = ThreadingHTTPServer(
        (stream_config.host, stream_config.port),
        _build_handler(output),
    )

    print(
        "[stream] Cat door camera stream listening on "
        f"http://{stream_config.host}:{stream_config.port}"
    )
    print("[stream] Browser page: /")
    print("[stream] MJPEG stream: /stream.mjpg")
    print("[stream] Health check: /health")
    print("[stream] Snapshot: /snapshot.jpg")

    try:
        server.serve_forever()
    finally:
        server.server_close()
        stop_recording = getattr(picam2, "stop_recording", None)
        if callable(stop_recording):
            stop_recording()


def main() -> None:
    try:
        serve_forever()
    except KeyboardInterrupt:
        print("\n[stream] Camera stream stopped.")


if __name__ == "__main__":
    main()
