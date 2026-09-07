from sqlalchemy import select
from .database import SessionLocal
from .models import LogicGate
GATES=[
 ("BUFFER","Passes the input through unchanged.",1,"A","A"),("NOT","Inverts the input.",1,"¬A","NOT A"),
 ("AND","True only when both inputs are true.",2,"A · B","A AND B"),("OR","True when either input is true.",2,"A + B","A OR B"),
 ("NAND","Inverse of AND.",2,"¬(A · B)","NOT (A AND B)"),("NOR","Inverse of OR.",2,"¬(A + B)","NOT (A OR B)"),
 ("XOR","True when inputs differ.",2,"A ⊕ B","A XOR B"),("XNOR","True when inputs match.",2,"¬(A ⊕ B)","NOT (A XOR B)"),
]
def seed_logic_gates(db):
    existing=set(db.scalars(select(LogicGate.gate_name)).all())
    for name,desc,count,symbol,pattern in GATES:
        if name not in existing: db.add(LogicGate(gate_name=name,description=desc,input_count=count,boolean_symbol=symbol,expression_pattern=pattern))
    db.commit()
def main():
    with SessionLocal() as db: seed_logic_gates(db)
if __name__=="__main__": main()
