from datetime import date, timedelta
import pytest
from pydantic import ValidationError
from app.schemas import ManagedUserCreate, ProfileUpdate, Register

def test_future_birth_date_rejected():
    with pytest.raises(ValidationError,match="cannot be in the future"):
        ProfileUpdate(full_name="Learner User",email="learner@example.com",date_of_birth=date.today()+timedelta(days=1))

def test_optional_profile_fields_supported():
    value=ProfileUpdate(full_name="Learner User",email="learner@example.com")
    assert value.gender is None and value.date_of_birth is None

def test_public_registration_cannot_request_super_admin():
    with pytest.raises(ValidationError):
        Register(full_name="Unsafe",email="unsafe@example.com",password="Secure123!",requested_role="SUPER_ADMIN")

def test_gender_options_are_constrained():
    with pytest.raises(ValidationError):
        ManagedUserCreate(full_name="Learner",email="learner@example.com",password="Secure123!",gender="UNDOCUMENTED")
