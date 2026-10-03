from unittest.mock import Mock

from smartflow.runtime import supervise_step


class Process:
    def __init__(self, alive):
        self.alive = alive
        self.terminated = 0
        self.joins = []

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.terminated += 1
        self.alive = False

    def join(self, timeout=None):
        self.joins.append(timeout)


def test_stalled_worker_is_terminated_once_then_restarted_with_same_budget():
    process, logger = Process(True), Mock()
    assert supervise_step(("stalled", 5.2), process, 0, logger) == (1, "restart")
    assert process.terminated == 1
    assert process.joins == [3]
    assert [call.args[0] for call in logger.info.call_args_list] == ["worker.stalled", "worker.restarting"]
    assert logger.info.call_args_list[0].kwargs["extra"]["safe_fields"] == {
        "code": "WORKER_STALLED",
        "duration_ms": 5200,
    }


def test_dead_worker_is_joined_then_restarted():
    process, logger = Process(False), Mock()
    assert supervise_step(("down", None), process, 1, logger) == (2, "restart")
    assert process.terminated == 0
    assert process.joins == [0]
    assert logger.info.call_args_list[0].args[0] == "worker.restarting"
    assert logger.info.call_args_list[0].kwargs["extra"]["safe_fields"] == {"attempt": 2}


def test_three_restarts_exhaust_budget_and_log_stable_code():
    process, logger = Process(False), Mock()
    assert supervise_step(("down", None), process, 3, logger) == (3, "exhausted")
    assert process.joins == [0]
    logger.info.assert_called_once_with(
        "worker.restart_exhausted", extra={"safe_fields": {"code": "WORKER_UNAVAILABLE"}}
    )


def test_ready_worker_requires_no_action_or_log():
    process, logger = Process(True), Mock()
    assert supervise_step(("ready", 0.2), process, 2, logger) == (2, "none")
    assert process.terminated == 0
    assert process.joins == []
    logger.info.assert_not_called()
