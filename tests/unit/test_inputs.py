import pytest
from pydantic import ValidationError
from smartflow.errors import ERRORS
from smartflow.jobs import CreateJob

pytestmark = pytest.mark.unit


def test_every_error_has_recovery_and_safe_message():
    assert all(spec.message and spec.recovery for spec in ERRORS.values())
    assert ERRORS["SEND_ACCEPTANCE_UNKNOWN"].recovery == "inspect_existing_request"


def test_blank_title_and_extra_fields_rejected():
    with pytest.raises(ValidationError):
        CreateJob(title="  ")
    with pytest.raises(ValidationError):
        CreateJob(title="valid", unsafe="value")
