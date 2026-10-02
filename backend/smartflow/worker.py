import threading

from filelock import FileLock

from smartflow.engine import Engine
from smartflow.observability import emit
from smartflow.providers import Simulator


def run_worker(db, settings, stop=None):
    stop = stop or threading.Event()
    with FileLock(str(settings.data_dir / "worker.lock"), timeout=0):
        engine = Engine(db, Simulator(db), settings.data_dir)
        engine.recover()
        emit(db.logger, "worker.started")
        while not stop.is_set():
            if not engine.tick():
                stop.wait(0.25)
        emit(db.logger, "worker.stopped")
