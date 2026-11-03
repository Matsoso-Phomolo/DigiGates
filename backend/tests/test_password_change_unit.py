from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.main import change_password
from app.models import ApprovalStatus, UserRole
from app.schemas import PasswordChange
from app.security import hash_password, verify_password


class CommitOnlySession:
    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


@pytest.mark.parametrize(
    "role,status",
    [
        (UserRole.LEARNER, ApprovalStatus.ACTIVE),
        (UserRole.ADMIN, ApprovalStatus.ACTIVE),
        (UserRole.SUPER_ADMIN, ApprovalStatus.ACTIVE),
        (UserRole.ADMIN, ApprovalStatus.PENDING),
        (UserRole.ADMIN, ApprovalStatus.REJECTED),
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
