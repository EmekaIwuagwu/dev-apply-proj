from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import JobPreference, User
from schemas.user import Token, UserCreate, UserLogin

router = APIRouter()

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash(password: str) -> str:
    return _pwd.hash(password)


def _verify(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _make_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        full_name=body.full_name,
        salutation=body.salutation,
        telephone=body.telephone,
        linkedin_url=body.linkedin_url,
        bio=body.bio,
        password_hash=_hash(body.password),
        resume_base64=body.resume_base64,
        resume_filename=body.resume_filename,
        tier="free",
    )
    db.add(user)
    await db.flush()

    prefs = JobPreference(user_id=user.id, job_titles=[], skills=[])
    db.add(prefs)

    await db.commit()
    await db.refresh(user)

    return {"access_token": _make_token(str(user.id)), "token_type": "bearer", "user": user}


@router.post("/login", response_model=Token)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not _verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    return {"access_token": _make_token(str(user.id)), "token_type": "bearer", "user": user}
