from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas
from app.database import SessionLocal
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

print("DEBUG SECRET_KEY:", SECRET_KEY)

ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_db():
    """Dependency that provides a SQLAlchemy session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """Generates a JWT token with an expiration time."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# -------------------- ROUTES -------------------- #

@router.post("/register", response_model=schemas.UserCreate)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new user after checking username availability."""
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(username=user.username, password=hashed_pw, email=user.email)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
def login(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    """Validates user credentials and returns a JWT token."""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username, "id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "user_id": user.id
    }
