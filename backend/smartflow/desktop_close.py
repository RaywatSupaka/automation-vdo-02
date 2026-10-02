"""Cancel the native close first; asynchronously flush without blocking the GUI thread."""

import threading


def install_close_guard(window, logger):
    allowed = False
    pending = False

    def closing():
        nonlocal pending
        if allowed:
            return True
        if pending:
            return False
        pending = True

        def check():
            nonlocal allowed, pending
            done = threading.Event()
            guard = threading.Lock()

            def unlock():
                try:
                    window.evaluate_js("document.body.inert = false")
                except Exception:
                    pass  # A closed renderer cannot be unlocked; keep native close blocked.

            def result(ok):
                nonlocal allowed, pending
                with guard:
                    if done.is_set():
                        return
                    done.set()
                    pending = False
                    if ok is True:
                        allowed = True
                if allowed:
                    window.destroy()

            try:
                window.evaluate_js(
                    """(async () => {
                    document.body.inert = true;
                    let ok = false;
                    try { ok = window.smartflowFlush ? await window.smartflowFlush() : true; }
                    finally { if (!ok) document.body.inert = false; }
                    return ok;
                })()""",
                    result,
                )
                if not done.wait(12):
                    with guard:
                        if done.is_set():
                            return
                        done.set()
                        pending = False
                    unlock()
            except Exception:
                done.set()
                pending = False
                unlock()
                from smartflow.observability import emit

                emit(logger, "desktop.close_blocked", code="DRAFT_SAVE_FAILED")

        threading.Timer(0.05, check).start()
        return False

    window.events.closing += closing
