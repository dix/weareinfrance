from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import generate


WATCH_PATHS = [Path("data"), Path("templates"), Path("assets"), Path("src")]
DEBOUNCE_SECONDS = 0.4


class DebouncedBuilder(FileSystemEventHandler):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._last_event = 0.0

    def on_any_event(self, event) -> None:
        if event.is_directory:
            return
        now = time.monotonic()
        with self._lock:
            self._last_event = now
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(
                DEBOUNCE_SECONDS, self._run_if_latest, args=(now,)
            )
            self._timer.daemon = True
            self._timer.start()

    def _run_if_latest(self, event_time: float) -> None:
        with self._lock:
            if event_time != self._last_event:
                return
        try:
            generate.main()
        except Exception as exc:
            print(f"Build failed: {exc}")


def main() -> None:
    handler = DebouncedBuilder()
    observer = Observer()
    for path in WATCH_PATHS:
        if path.exists():
            observer.schedule(handler, str(path), recursive=True)

    observer.start()
    print("Watching for changes. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.8)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
