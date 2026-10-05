from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from .models import ProgressStatus, UserRole

class ORMModel(BaseModel): model_config=ConfigDict(from_attributes=True)
class Register(BaseModel):
    full_name: str=Field(min_length=2,max_length=120)
    email: EmailStr
    password: str=Field(min_length=8,max_length=128)
    @field_validator("full_name")
    @classmethod
    def clean_name(cls,v):
        if not v.strip(): raise ValueError("name cannot be blank")
        return v.strip()
class Login(BaseModel): email: EmailStr; password: str
class UserOut(ORMModel):
    user_id:int; full_name:str; email:EmailStr; role:UserRole; is_active:bool; created_at:datetime; updated_at:datetime
class ProfileUpdate(BaseModel):
    full_name: str=Field(min_length=2,max_length=120)
    email: EmailStr
    @field_validator("full_name")
    @classmethod
    def clean_name(cls,v):
        if not v.strip(): raise ValueError("name cannot be blank")
        return v.strip()
class PasswordChange(BaseModel):
    current_password: str=Field(min_length=1,max_length=128)
    new_password: str=Field(min_length=8,max_length=128)
class AccountConfirmation(BaseModel):
    current_password: str=Field(min_length=1,max_length=128)
class AccountDeleteConfirmation(AccountConfirmation):
    confirmation: Literal["DELETE"]

class Token(BaseModel): access_token:str; token_type:str="bearer"; user:UserOut

GATE_TYPES={"BUFFER":1,"NOT":1,"AND":2,"OR":2,"NAND":2,"NOR":2,"XOR":2,"XNOR":2}
class SourceType(str,Enum): variable="variable"; operator="operator"
class CircuitSource(BaseModel):
    source_type:SourceType; source_id:str=Field(min_length=1,max_length=50); input_position:int=Field(ge=1,le=2)
class CircuitVariable(BaseModel):
    id:str=Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,49}$"); label:str=Field(pattern=r"^[A-Z]$"); box:int=Field(ge=1,le=4)
class CircuitOperator(BaseModel):
    id:str=Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,49}$"); type:str; column:int=Field(ge=1,le=4); row:int=Field(ge=1,le=10); inputs:list[CircuitSource]
    @field_validator("type")
    @classmethod
    def gate_type(cls,v):
        v=v.upper()
        if v not in GATE_TYPES: raise ValueError("unsupported gate type")
        return v
    @model_validator(mode="after")
    def arity(self):
        if len(self.inputs)!=GATE_TYPES[self.type]: raise ValueError(f"{self.type} requires {GATE_TYPES[self.type]} input(s)")
        if len({x.input_position for x in self.inputs})!=len(self.inputs): raise ValueError("input positions must be unique")
        if {x.input_position for x in self.inputs}!=set(range(1,len(self.inputs)+1)): raise ValueError("input positions must start at 1")
        return self
class FinalOperator(BaseModel):
    id:str=Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,49}$"); type:str; inputs:list[CircuitSource]
    @field_validator("type")
    @classmethod
    def gate_type(cls,v):
        v=v.upper()
        if v not in GATE_TYPES: raise ValueError("unsupported gate type")
        return v
    @model_validator(mode="after")
    def arity(self):
        if len(self.inputs)!=GATE_TYPES[self.type]: raise ValueError(f"{self.type} requires {GATE_TYPES[self.type]} input(s)")
        if len({x.input_position for x in self.inputs})!=len(self.inputs): raise ValueError("input positions must be unique")
        return self
class CircuitDefinition(BaseModel):
    version:Literal[1]; variables:list[CircuitVariable]=Field(min_length=1,max_length=4); operators:list[CircuitOperator]; final_operator:FinalOperator
    @model_validator(mode="after")
    def topology(self):
        if len({v.label for v in self.variables})!=len(self.variables): raise ValueError("variable labels must be unique")
        if len({v.id for v in self.variables})!=len(self.variables): raise ValueError("variable ids must be unique")
        if len({v.box for v in self.variables})!=len(self.variables): raise ValueError("variable boxes must be unique")
        ids=[o.id for o in self.operators]
        if len(set(ids))!=len(ids) or self.final_operator.id in ids: raise ValueError("operator ids must be unique")
        occupied={(o.column,o.row) for o in self.operators}
        if len(occupied)!=len(self.operators): raise ValueError("only one operator is allowed per row")
        for col,row in occupied:
            if (col,row+1) in occupied: raise ValueError("consecutive active rows are not allowed in a column")
        variables={v.id for v in self.variables}; by_id={o.id:o for o in self.operators}
        for dest in self.operators:
            self._validate_sources(dest.inputs,dest.column,variables,by_id)
        self._validate_sources(self.final_operator.inputs,5,variables,by_id)
        return self
    @staticmethod
    def _validate_sources(inputs,destination_column,variables,operators):
        for source in inputs:
            if source.source_type==SourceType.variable:
                if source.source_id not in variables: raise ValueError(f"unknown variable source {source.source_id}")
            else:
                node=operators.get(source.source_id)
                if not node: raise ValueError(f"unknown operator source {source.source_id}")
                if node.column>=destination_column: raise ValueError("operator sources must come from an earlier column")

class GateBase(BaseModel):
    gate_name:str=Field(min_length=1,max_length=20); description:str=Field(min_length=1); input_count:int=Field(ge=1,le=2); boolean_symbol:str=Field(min_length=1,max_length=30); expression_pattern:str=Field(min_length=1,max_length=100)
    @field_validator("gate_name")
    @classmethod
    def name(cls,v): return v.strip().upper()
class GateCreate(GateBase): pass
class GateUpdate(GateBase): pass
class GateOut(GateBase,ORMModel): gate_id:int; created_at:datetime; updated_at:datetime
class LessonBase(BaseModel): gate_id:int=Field(gt=0); title:str=Field(min_length=1,max_length=180); theory_content:str=Field(min_length=1); lesson_order:int=Field(ge=0); is_published:bool=False
class LessonCreate(LessonBase): pass
class LessonUpdate(LessonBase): pass
class LessonOut(LessonBase,ORMModel): lesson_id:int; created_at:datetime; updated_at:datetime
class PrebuiltBase(BaseModel): title:str=Field(min_length=1,max_length=180); description:str=Field(min_length=1); difficulty:str=Field(min_length=1,max_length=30); circuit_definition:CircuitDefinition; expression:str=Field(min_length=1); is_published:bool=False
class PrebuiltCreate(PrebuiltBase): pass
class PrebuiltUpdate(PrebuiltBase): pass
class PrebuiltOut(PrebuiltBase,ORMModel): circuit_id:int; created_by:int; created_at:datetime; updated_at:datetime
class SavedCircuitCreate(BaseModel): circuit_name:str=Field(min_length=1,max_length=180); circuit_definition:CircuitDefinition; expression:str=Field(min_length=1)
class SavedCircuitUpdate(SavedCircuitCreate): pass
class SavedCircuitOut(SavedCircuitCreate,ORMModel): saved_circuit_id:int; learner_id:int; created_at:datetime; updated_at:datetime
class ProgressUpsert(BaseModel): lesson_id:int=Field(gt=0); status:ProgressStatus
class ProgressOut(ProgressUpsert,ORMModel): progress_id:int; learner_id:int; last_accessed_at:datetime; completed_at:datetime|None
class ExerciseBase(BaseModel):
    lesson_id:int|None=Field(default=None,gt=0); circuit_id:int|None=Field(default=None,gt=0); title:str=Field(min_length=1,max_length=180); instructions:str=Field(min_length=1); exercise_type:str=Field(min_length=1,max_length=50); expected_result:dict[str,Any]; is_published:bool=False
class ExerciseCreate(ExerciseBase): pass
class ExerciseUpdate(ExerciseBase): pass
class ExerciseOut(ExerciseBase,ORMModel): exercise_id:int; created_at:datetime; updated_at:datetime
class AttemptCreate(BaseModel): exercise_id:int=Field(gt=0); submitted_answer:dict[str,Any]
class AttemptOut(ORMModel): attempt_id:int; exercise_id:int; learner_id:int; submitted_answer:dict[str,Any]; is_correct:bool; score:Decimal=Field(ge=0,le=100); attempted_at:datetime
