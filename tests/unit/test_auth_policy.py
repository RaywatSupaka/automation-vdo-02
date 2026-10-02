import pytest
from smartflow.auth import AccessControl, Permission
from smartflow.config import Settings
from smartflow.errors import AppError

pytestmark = pytest.mark.unit
TOKEN = "unit-test-session-not-a-real-secret"


@pytest.mark.parametrize("token", [None, "", "wrong-session", "ข้อมูลที่ไม่ใช่ token"])
def test_invalid_credential_is_unauthorized_without_database(tmp_path, token):
    access = AccessControl(Settings(tmp_path, TOKEN))
    with pytest.raises(AppError) as error:
        access.authenticate(token)
    assert error.value.code == "UNAUTHORIZED"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("permission", [None, "not-registered", Permission.JOBS_CREATE])
def test_viewer_cannot_gain_permission_from_development_bypass(tmp_path, permission):
    access = AccessControl(Settings(tmp_path, TOKEN, auth_mode="dev_bypass", session_role="viewer"))
    principal = access.authenticate(TOKEN)
    access.require(principal, Permission.JOBS_READ)
    with pytest.raises(AppError) as error:
        access.require(principal, permission)
    assert error.value.code == "PERMISSION_DENIED"
