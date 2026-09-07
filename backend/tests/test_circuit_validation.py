import pytest
from pydantic import ValidationError
from app.schemas import CircuitDefinition

def valid_circuit():
    return {"version":1,"variables":[{"id":"v1","label":"A","box":1},{"id":"v2","label":"B","box":2}],"operators":[{"id":"op1","type":"AND","column":1,"row":1,"inputs":[{"source_type":"variable","source_id":"v1","input_position":1},{"source_type":"variable","source_id":"v2","input_position":2}]}],"final_operator":{"id":"final","type":"NOT","inputs":[{"source_type":"operator","source_id":"op1","input_position":1}]}}
def test_valid_definition(): assert CircuitDefinition.model_validate(valid_circuit()).version==1
def test_duplicate_variable_label_rejected():
    data=valid_circuit(); data["variables"][1]["label"]="A"
    with pytest.raises(ValidationError,match="labels must be unique"): CircuitDefinition.model_validate(data)
def test_consecutive_rows_rejected():
    data=valid_circuit(); data["operators"].append({"id":"op2","type":"NOT","column":1,"row":2,"inputs":[{"source_type":"variable","source_id":"v1","input_position":1}]})
    with pytest.raises(ValidationError,match="consecutive"): CircuitDefinition.model_validate(data)
def test_backward_connection_rejected():
    data=valid_circuit(); data["operators"]=[{"id":"op1","type":"NOT","column":2,"row":1,"inputs":[{"source_type":"operator","source_id":"op2","input_position":1}]},{"id":"op2","type":"NOT","column":3,"row":1,"inputs":[{"source_type":"variable","source_id":"v1","input_position":1}]}]
    with pytest.raises(ValidationError,match="earlier column"): CircuitDefinition.model_validate(data)
def test_incorrect_arity_rejected():
    data=valid_circuit(); data["operators"][0]["inputs"]=data["operators"][0]["inputs"][:1]
    with pytest.raises(ValidationError,match="requires 2"): CircuitDefinition.model_validate(data)
