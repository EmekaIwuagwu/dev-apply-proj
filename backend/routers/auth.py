from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from database import get_db
from models.user import User, JobPreference
from schemas.user import UserCreate, UserLogin, Token, UserResponse
from config import settings

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create User
    db_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        salutation=user_in.salutation,
        telephone=user_in.telephone,
        linkedin_url=user_in.linkedin_url,
        bio=user_in.bio,
        password_hash=get_password_hash(user_in.password),
        resume_base64=user_in.resume_base64,
        resume_filename=user_in.resume_filename,
        tier="free"
    )
    db.add(db_user)
    await db.flush() # Get ID
    
    # Create Default Preferences
    db_prefs = JobPreference(user_id=db_user.id, job_titles=[], skills=[])
    db.add(db_prefs)
    
    await db.commit()
    await db.refresh(db_user)
    
    token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "user": db_user}

@router.post("/login", response_model=Token)
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_in.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer", "user": user}

async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(lambda: None)): # Simplified for now
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    auth_scheme = HTTPBearer()
    
    # This is a bit of a hack to avoid circular dependencies if I put it in a separate file
    # In a real app, I'd move this to a security.py file
    async def get_token(auth: HTTPAuthorizationCredentials = Depends(auth_scheme)):
        return auth.credentials

    # Internal helper to handle the actual verification
    async def verify(token: str):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    return verify
