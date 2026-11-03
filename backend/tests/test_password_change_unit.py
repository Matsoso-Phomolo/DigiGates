from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.main import change_password, login
from app.models import ApprovalStatus, UserRole
from app.schemas import Login, PasswordChange
from fastapi.security import HTTPAuthorizationCredentials
from app.security import authenticated_account, hash_password, token_for, verify_password


class CommitOnlySession:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class ScalarSession:
    def __init__(self, user):
        self.user = user

    def scalar(self, _statement):
        return self.user


def auth_user(status):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        user_id=9,
        full_name="Admin Applicant",
        email="applicant@example.com",
        password_hash=hash_password("Secure123!"),
        role=UserRole.ADMIN,
        approval_status=status,
        gender=None,
        date_of_birth=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    "role,status",
    [
        (UserRole.LEARNER, ApprovalStatus.ACTIVE),
        (UserRole.ADMIN, ApprovalStatus.ACTIVE),
        (UserRole.SUPER_ADMIN, ApprovalStatus.ACTIVE),
    ],
)
def test_change_password_hashes_for_every_authenticated_account(role, status):
    user = SimpleNamespace(
        role=role,
        approval_status=status,
        password_hash=hash_password("Secure123!"),
    )
    db = CommitOnlySession()
    response = change_password(
        PasswordChange(current_password="Secure123!", new_password="DifferentSecure123!"),
        db,
        user,
    )
    assert response.status_code == 204
    assert db.committed
    assert verify_password("DifferentSecure123!", user.password_hash)
    assert not verify_password("Secure123!", user.password_hash)
    assert user.password_hash != "DifferentSecure123!"


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_unapproved_admin_stale_token_is_rejected(status):
    user = SimpleNamespace(user_id=7, role=UserRole.ADMIN, approval_status=status, is_active=True)
    class LookupSession:
        def get(self, _model, _identifier):
            return user
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_for(user))
    with pytest.raises(HTTPException) as denied:
        authenticated_account(credentials, LookupSession())
    assert denied.value.status_code == 403


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_unapproved_admin_login_is_rejected(status):
    with pytest.raises(HTTPException) as denied:
        login(Login(email="applicant@example.com", password="Secure123!"), ScalarSession(auth_user(status)))
    assert denied.value.status_code == 403


def test_approved_admin_login_succeeds():
    result = login(Login(email="applicant@example.com", password="Secure123!"), ScalarSession(auth_user(ApprovalStatus.ACTIVE)))
    assert result.user.approval_status == ApprovalStatus.ACTIVE
    assert result.access_token


def test_change_password_rejects_wrong_current_password_and_reuse():
    user = SimpleNamespace(password_hash=hash_password("Secure123!"))
    with pytest.raises(HTTPException) as wrong:
        change_password(
            PasswordChange(current_password="WrongPassword!", new_password="DifferentSecure123!"),
            CommitOnlySession(),
            user,
        )
    assert wrong.value.status_code == 401
    with pytest.raises(HTTPException) as reused:
        change_password(
            PasswordChange(current_password="Secure123!", new_password="Secure123!"),
            CommitOnlySession(),
            user,
        )
    assert reused.value.status_code == 400
