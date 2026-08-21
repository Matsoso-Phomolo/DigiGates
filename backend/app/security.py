from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()
def hash_password(value): return pwd.hash(value)
def verify_password(value, hashed): return pwd.verify(value, hashed)
def token_for(user):
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": expires}, settings.secret_key, algorithm="HS256")
def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try: user_id = int(jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])["sub"])
    except (JWTError, KeyError, ValueError): raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, user_id)
    if not user or not user.is_active: raise HTTPException(401, "Account unavailable")
    return user
def admin_user(user: User = Depends(current_user)):
    if user.role != "admin": raise HTTPException(403, "Administrator role required")
    return user

