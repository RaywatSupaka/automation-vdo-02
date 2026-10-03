import os
import threading
import time

from filelock import FileLock

from smartflow.engine import Engine
from smartflow.heartbeat import beat
from smartflow.observability import emit, safe_exception
from smartflow.providers import Simulator


class Maintenance:
    """Story lease/save upkeep. A failed pass is logged and retried with bounded backoff,
    never allowed to kill the worker (which would spend the supervisor restart budget)."""

    INTERVAL, MAX_DELAY = 1.0, 30.0

    def __init__(self, action, logger, clock=time.monotonic):
        self.action, self.logger, self.clock = action, logger, clock
        self.due, self.failures = 0.0, 0

    def run(self):
        now = self.clock()
        if now < self.due:
            return False
        try:
            self.action()
        except Exception as exc:  # Worker-loop boundary: log, back off, keep running.
            self.failures += 1
            delay = min(self.MAX_DELAY, self.INTERVAL * 2**self.failures)
            emit(
                self.logger,
                "story.maintain_failed",
                code="STORY_MAINTENANCE_FAILED",
                attempt=self.failures,
                **safe_exception(exc),
            )
            self.due = now + delay
            return False
        if self.failures:
            emit(self.logger, "story.maintain_recovered", attempt=self.failures)
        self.failures, self.due = 0, now + self.INTERVAL
        return True


def run_worker(db, settings, stop=None):
    stop = stop or threading.Event()
    with FileLock(str(settings.data_dir / "worker.lock"), timeout=0):
        engine = Engine(db, Simulator(db), settings.data_dir)
        engine.recover()
        emit(db.logger, "worker.started")
        from smartflow.story_workflow import StoryWorkflow

        maintenance = Maintenance(StoryWorkflow(db).maintain, db.logger)
        pulse = Pulse(settings.data_dir)
        while not stop.is_set():
            pulse.run()  # Written once per loop pass: a blocked step stops the beat.
            maintenance.run()
            if not engine.tick():
                stop.wait(0.25)
        emit(db.logger, "worker.stopped")


class Pulse:
    INTERVAL = 1.0

    def __init__(self, data_dir, clock=time.monotonic, wall=time.time):
        self.data_dir, self.clock, self.wall, self.due = data_dir, clock, wall, 0.0

    def run(self):
        if self.clock() < self.due:
            return
        self.due = self.clock() + self.INTERVAL
        try:
            beat(self.data_dir, os.getpid(), self.wall())
        except OSError:
            pass  # A reader holding the file on Windows; the next pass retries.
