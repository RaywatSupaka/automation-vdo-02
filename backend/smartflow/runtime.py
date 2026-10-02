import multiprocessing
import threading
import time
from contextlib import contextmanager

from filelock import FileLock

from smartflow.api import create_app
from smartflow.db import Database
from smartflow.observability import create_logger, emit, safe_exception
from smartflow.worker import run_worker


def worker_entry(settings, receiver):
    db = Database(settings.db_path, create_logger(settings.data_dir, "worker"))
    stop = threading.Event()

    # Parent death also ends the worker after a crash of the host process.
    def watch_parent():
        parent = multiprocessing.parent_process()
        try:
            while not stop.is_set():
                if receiver.poll(0.25):
                    receiver.recv_bytes()
                    stop.set()
                elif parent and not parent.is_alive():
                    stop.set()
        except (EOFError, OSError):
            stop.set()

    threading.Thread(target=watch_parent, daemon=True).start()
    try:
        run_worker(db, settings, stop)
    except Exception as exc:
        emit(db.logger, "worker.fatal", code="INTERNAL_ERROR", **safe_exception(exc))
        raise SystemExit(1)
    finally:
        db.close()
        receiver.close()


@contextmanager
def runtime(settings, worker=True):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with FileLock(str(settings.data_dir / "app.lock"), timeout=0):
        app = create_app(settings)
        app.state.db.migrate()
        context = multiprocessing.get_context("spawn")
        # Do not share an Event/Semaphore with a killable child: termination can
        # leave its lock permanently held. Each child gets a disposable pipe.
        stop = threading.Event()
        processes = []
        senders = []

        def launch():
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=worker_entry, args=(settings, receiver), daemon=True)
            process.start()
            receiver.close()
            senders.append(sender)
            processes.append(process)

        if worker:
            launch()
        app.state.worker_alive = lambda: bool(processes and processes[-1].is_alive())
        app.state.worker_process = lambda: processes[-1] if processes else None

        def supervise():
            restarts = 0
            while not stop.wait(0.5):
                if processes[-1].is_alive():
                    continue
                processes[-1].join(timeout=0)
                if restarts >= 3:
                    emit(app.state.db.logger, "worker.restart_exhausted", code="WORKER_UNAVAILABLE")
                    return
                restarts += 1
                emit(app.state.db.logger, "worker.restarting", attempt=restarts)
                if stop.wait(min(restarts, 3)):
                    return
                launch()

        supervisor = threading.Thread(target=supervise, daemon=True) if worker else None
        if supervisor:
            supervisor.start()
        try:
            yield app
        finally:
            stop.set()
            if supervisor:
                supervisor.join(timeout=2)
            for process, sender in zip(processes, senders):
                if process.is_alive():
                    try:
                        sender.send_bytes(b"stop")
                    except (BrokenPipeError, OSError):
                        pass
                sender.close()
                process.join(timeout=5)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=3)
            app.state.db.close()


def desktop(settings, smoke=False):
    import uvicorn
    import webview

    with runtime(settings) as app:
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=settings.port, access_log=False, log_config=None)
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 15
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Local API could not start; check the port and runtime log")
            time.sleep(0.05)
        window = webview.create_window(
            "SmartFlow Next",
            f"http://127.0.0.1:{settings.port}/#token={settings.token}",
            width=1320,
            height=860,
            min_size=(980, 680),
        )

        def smoke_check():
            # Explicit owned smoke only. Never closes an existing user window.
            try:
                limit = time.monotonic() + 20
                while time.monotonic() < limit:
                    if window.evaluate_js(
                        "Boolean(document.querySelector('[data-testid=dashboard]') && document.querySelector('.connection-status .online'))"
                    ):
                        import ctypes
                        import json
                        import os

                        (settings.data_dir / "desktop-smoke.json").write_text(
                            json.dumps(
                                {
                                    "webview_loaded": True,
                                    "dashboard_rendered": True,
                                    "console_attached": bool(ctypes.windll.kernel32.GetConsoleWindow())
                                    if os.name == "nt"
                                    else None,
                                }
                            ),
                            encoding="utf-8",
                        )
                        break
                    time.sleep(0.2)
            finally:
                window.destroy()

        try:
            webview.start(
                smoke_check if smoke else None,
                gui="edgechromium",
                private_mode=True,
                storage_path=str(settings.data_dir / "webview"),
            )
        finally:
            server.should_exit = True
            thread.join(timeout=5)
