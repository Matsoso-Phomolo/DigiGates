from typing import Any, Literal
from pydantic import BaseModel, EmailStr, Field

class Register(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
class Login(BaseModel): email: EmailStr; password: str
class UserOut(BaseModel):
    id: int; name: str; email: EmailStr; role: str; is_active: bool
    model_config = {"from_attributes": True}
class Token(BaseModel): access_token: str; token_type: str = "bearer"; user: UserOut
class GateIn(BaseModel): name: str; description: str; expression: str; arity: int = Field(ge=1, le=2)
class LessonIn(BaseModel): title: str; gate_name: str; content: str; order_index: int = 0
class CircuitIn(BaseModel): title: str; description: str = ""; definition: dict[str, Any]
class ExerciseIn(BaseModel): title: str; prompt: str; solution: dict[str, Any]
class SavedCircuitIn(BaseModel): name: str = Field(min_length=1, max_length=180); definition: dict[str, Any]
class ProgressIn(BaseModel): mode: Literal["learn", "explore", "build"]; item_key: str; state: dict[str, Any]

