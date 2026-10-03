"""Local sessions and permissions; dev bypass substitutes identity, not checks."""

import secrets
import sys
from dataclasses import dataclass
from enum import StrEnum

from smartflow.errors import AppError


class Permission(StrEnum):
    SESSION_READ = "session:read"
    SCHEMA_READ = "schema:read"
    JOBS_READ = "jobs:read"
    JOBS_CREATE = "jobs:create"
    JOBS_COMMAND = "jobs:command"
    DIAGNOSTICS_READ = "diagnostics:read"
    SUPPORT_EXPORT = "support:export"
    DRAFTS_READ = "stories:drafts:read"
    DRAFTS_WRITE = "stories:drafts:write"
    BROWSER_MANAGE = "browser:manage"
    BROWSER_PAIR = "browser:pair"
    BROWSER_STATUS = "browser:status"
    BROWSER_WORK = "browser:work"


class Role(StrEnum):
    BROWSER_AGENT = "browser_agent"
    BROWSER_PAIRING = "browser_pairing"
    OWNER = "owner"
    OPERATOR = "operator"
    VIEWER = "viewer"
    SUPPORT = "support"


class AuthMode(StrEnum):
    LOCAL_SESSION = "local_session"
    DEV_BYPASS = "dev_bypass"


BASE = frozenset({Permission.SESSION_READ, Permission.SCHEMA_READ})
ROLE_PERMISSIONS = {
    Role.OWNER: frozenset(Permission) - {Permission.BROWSER_PAIR, Permission.BROWSER_STATUS, Permission.BROWSER_WORK},
    Role.BROWSER_AGENT: frozenset({Permission.BROWSER_STATUS, Permission.BROWSER_WORK}),
    Role.BROWSER_PAIRING: frozenset({Permission.BROWSER_PAIR}),
    Role.OPERATOR: BASE
    | {
        Permission.JOBS_READ,
        Permission.JOBS_CREATE,
        Permission.JOBS_COMMAND,
        Permission.DRAFTS_READ,
        Permission.DRAFTS_WRITE,
    },
    Role.VIEWER: BASE | {Permission.JOBS_READ, Permission.DRAFTS_READ},
    Role.SUPPORT: BASE | {Permission.DIAGNOSTICS_READ, Permission.SUPPORT_EXPORT},
}


@dataclass(frozen=True)
class Principal:
    actor_id: str
    role: Role
    auth_mode: AuthMode

    @property
    def permissions(self):
        return ROLE_PERMISSIONS[self.role]


class AccessControl:
    def __init__(self, settings):
        self.mode = AuthMode(settings.auth_mode)
        self.role = Role(settings.session_role)
        if self.role in {Role.BROWSER_AGENT, Role.BROWSER_PAIRING}:
            raise ValueError("Browser identities require pairing, not a desktop session role")
        if self.mode == AuthMode.DEV_BYPASS and (
            settings.mode not in {"dev", "test"} or getattr(sys, "frozen", False)
        ):
            raise ValueError("Development identity bypass is forbidden in production and packaged builds")
        if len(settings.token) < 24:
            raise ValueError("Set SMARTFLOW_API_TOKEN with at least 24 characters")
        if settings.diagnostics_token and (
            len(settings.diagnostics_token) < 24 or settings.diagnostics_token == settings.token
        ):
            raise ValueError("Diagnostics token must be distinct and at least 24 characters")
        self._token = settings.token.encode("utf-8")
        self._diagnostics_token = settings.diagnostics_token.encode("utf-8")

    def authenticate(self, token: str | None):
        if not token:
            raise AppError("UNAUTHORIZED")
        candidate = token.encode("utf-8")
        if secrets.compare_digest(candidate, self._token):
            actor = "development-session" if self.mode == AuthMode.DEV_BYPASS else "desktop-session"
            return Principal(actor, self.role, self.mode)
        if self._diagnostics_token and secrets.compare_digest(candidate, self._diagnostics_token):
            return Principal("diagnostics-session", Role.SUPPORT, self.mode)
        raise AppError("UNAUTHORIZED")

    def require(self, principal: Principal, permission: str | None):
        # Missing declarations and unknown permission names never imply access.
        if permission not in principal.permissions:
            raise AppError("PERMISSION_DENIED")


def policy(permission: Permission):
    return {"x-required-permission": permission.value}
