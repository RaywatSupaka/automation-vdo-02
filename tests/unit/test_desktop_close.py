from types import SimpleNamespace

from smartflow.desktop_close import install_close_guard


def setup(monkeypatch, outcome):
    scheduled = []

    class Timer:
        def __init__(self, delay, callback):
            self.callback = callback

        def start(self):
            scheduled.append(self.callback)

    class Event:
        flag = False

        def is_set(self):
            return self.flag

        def set(self):
            self.flag = True

        def wait(self, seconds):
            return self.flag

    class Handlers:
        def __iadd__(self, callback):
            self.callback = callback
            return self

    class Window:
        destroyed = 0
        callback = None
        scripts = []
        events = SimpleNamespace(closing=Handlers())

        def evaluate_js(self, script, callback=None):
            self.scripts.append(script)
            if callback:
                self.callback = callback
                if outcome != "timeout":
                    callback(outcome)

        def destroy(self):
            self.destroyed += 1

    monkeypatch.setattr("smartflow.desktop_close.threading.Timer", Timer)
    monkeypatch.setattr("smartflow.desktop_close.threading.Event", Event)
    window = Window()
    install_close_guard(window, None)
    return window, scheduled


def test_close_is_cancelled_until_flush_ack_and_duplicate_close_is_coalesced(monkeypatch):
    window, scheduled = setup(monkeypatch, True)
    assert window.events.closing.callback() is False
    assert window.events.closing.callback() is False
    assert len(scheduled) == 1 and not window.destroyed
    scheduled.pop()()
    assert window.destroyed == 1 and window.events.closing.callback() is True


def test_failed_flush_keeps_window_open_and_allows_safe_retry(monkeypatch):
    window, scheduled = setup(monkeypatch, False)
    assert window.events.closing.callback() is False
    scheduled.pop()()
    assert not window.destroyed
    assert window.events.closing.callback() is False
    assert len(scheduled) == 1


def test_timeout_unlocks_ui_and_late_flush_cannot_close_new_edits(monkeypatch):
    window, scheduled = setup(monkeypatch, "timeout")
    window.events.closing.callback()
    scheduled.pop()()
    assert window.scripts[-1] == "document.body.inert = false"
    window.callback(True)
    assert not window.destroyed
