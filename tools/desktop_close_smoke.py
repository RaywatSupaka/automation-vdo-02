"""Owned WebView: edit, native close before debounce, then verify committed draft."""

import json
import socket
import sqlite3
import tempfile
import threading
import time
from pathlib import Path

import webview
from smartflow.config import Settings
from smartflow.runtime import desktop

ROOT = Path(__file__).resolve().parents[1]


def main():
    start = time.monotonic()
    directory = Path(tempfile.mkdtemp(prefix="smartflow-close-smoke-"))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    settings = Settings(directory, "owned-close-session-not-secret", "test", port)
    original_start = webview.start
    result = {"edited_before_close": False, "timed_out": False}

    def drive():
        window = webview.windows[0]
        window.set_title("SmartFlow Next - owned close test")
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            ready = window.evaluate_js(
                "Boolean(window.smartflowFlush && document.querySelector('.story-setting-field input[type=text]'))"
            )
            if ready:
                break
            time.sleep(0.1)
        else:
            return
        # User input through the native input setter activates React's change handler.
        window.evaluate_js("""(() => {
            const input = document.querySelector('.story-setting-field input[type=text]');
            Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'owned close flush fixture');
            input.dispatchEvent(new Event('input', {bubbles: true}));
        })()""")
        result["edited_before_close"] = window.evaluate_js(
            "document.querySelector('.draft-save-status').textContent.includes('กำลังบันทึก')"
        )
        window.destroy()  # Goes through the production native closing event and async flush.

    def start_test(*args, **kwargs):
        def deadline():
            result["timed_out"] = True
            # Only this test's window; remove its guard for teardown after recording failure.
            window = webview.windows[0]
            window.events.closing._items.clear()
            window.destroy()

        timer = threading.Timer(35, deadline)
        timer.start()
        try:
            return original_start(drive, **kwargs)
        finally:
            timer.cancel()

    webview.start = start_test
    desktop(settings)
    assert result["edited_before_close"] and not result["timed_out"], result
    with sqlite3.connect(settings.db_path) as connection:
        rows = connection.execute("SELECT config FROM story_drafts").fetchall()
    assert len(rows) == 1 and json.loads(rows[0][0])["topic"] == "owned close flush fixture"
    result.update(native_close_saved=True, seconds=round(time.monotonic() - start, 3))
    (ROOT / "build/desktop-close-smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
