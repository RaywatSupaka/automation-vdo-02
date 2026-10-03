import logging

from smartflow.worker import Maintenance


class Clock:
    value = 100.0

    def __call__(self):
        return self.value


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append((record.getMessage(), record.safe_fields))


def logger():
    log = logging.getLogger("maintenance-test")
    log.handlers, log.propagate = [Capture()], False
    log.setLevel(logging.INFO)
    return log


def test_failed_pass_backs_off_logs_safely_and_recovers_without_raising():
    clock, log, calls = Clock(), logger(), []

    def action():
        calls.append(clock.value)
        if len(calls) <= 3:
            raise RuntimeError("database is locked at C:/Users/private/path")

    upkeep = Maintenance(action, log, clock)
    delays = []
    for _ in range(3):
        assert upkeep.run() is False
        delays.append(upkeep.due - clock.value)
        assert upkeep.run() is False and len(calls) == len(delays)  # No retry before the backoff.
        clock.value = upkeep.due
    assert delays == [2.0, 4.0, 8.0]
    assert upkeep.run() is True and upkeep.failures == 0 and upkeep.due == clock.value + 1.0
    records = log.handlers[0].records
    assert [name for name, _ in records] == ["story.maintain_failed"] * 3 + ["story.maintain_recovered"]
    assert records[0][1]["code"] == "STORY_MAINTENANCE_FAILED"
    assert records[0][1]["exception_type"] == "RuntimeError"
    assert "private" not in str(records)  # Raw message and user path are never logged.


def test_backoff_is_bounded():
    clock = Clock()

    def action():
        raise OSError("disk")

    upkeep = Maintenance(action, logger(), clock)
    for _ in range(10):
        upkeep.run()
        clock.value = upkeep.due
    upkeep.run()
    assert upkeep.due - clock.value == Maintenance.MAX_DELAY == 30.0
