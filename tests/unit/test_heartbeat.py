from smartflow.heartbeat import READY_SECONDS, STALL_SECONDS, beat, heartbeat_path, read, worker_state
from smartflow.worker import Pulse


def test_alive_ready_and_stalled_are_separate_signals():
    started = 1000.0
    assert worker_state(False, 7, (7, 1000.0), 1001.0, started) == ("down", None)
    # A live process without its own beat is starting, then stalled once the budget passes.
    assert worker_state(True, 7, None, started + 1, started) == ("starting", None)
    assert worker_state(True, 7, (6, 1000.5), started + 1, started) == ("starting", None)  # Old pid.
    assert worker_state(True, 7, None, started + STALL_SECONDS, started)[0] == "stalled"
    assert worker_state(True, 7, (7, 1000.0), 1000.0 + READY_SECONDS, started) == ("ready", READY_SECONDS)
    assert worker_state(True, 7, (7, 1000.0), 1010.0, started) == ("late", 10.0)
    assert worker_state(True, 7, (7, 1000.0), 1000.0 + STALL_SECONDS, started)[0] == "stalled"
    assert worker_state(True, 7, (7, 1005.0), 1000.0, started) == ("ready", 0.0)  # Clock skew.


def test_beat_is_atomic_and_unreadable_files_are_ignored(tmp_path):
    assert read(tmp_path) is None
    beat(tmp_path, 42, 1234.5)
    beat(tmp_path, 42, 1235.5)  # Duplicate beat replaces, never appends.
    assert read(tmp_path) == (42, 1235.5)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["worker.heartbeat"]
    heartbeat_path(tmp_path).write_text("{torn", encoding="utf-8")
    assert read(tmp_path) is None


class Clock:
    value = 0.0

    def __call__(self):
        return self.value


def test_pulse_beats_at_most_once_per_interval(tmp_path):
    clock, wall = Clock(), Clock()
    pulse = Pulse(tmp_path, clock, wall)
    wall.value = 50.0
    pulse.run()
    first = read(tmp_path)
    wall.value, clock.value = 60.0, 0.5
    pulse.run()
    assert read(tmp_path) == first  # Within the interval: no extra write.
    clock.value = 1.0
    pulse.run()
    assert read(tmp_path)[1] == 60.0
