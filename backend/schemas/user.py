from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    salutation: str
    telephone: str
    linkedin_url: Optional[str] = None
    bio: str
    tier: str = "free"

class UserCreate(UserBase):
    password: str
    resume_base64: str
    resume_filename: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    agent_enabled: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class JobPreferenceBase(BaseModel):
    job_titles: List[str]
    skills: List[str]
    experience_level: Optional[str] = None
    job_type: Optional[str] = None
    preferred_locations: List[str] = []
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    excluded_companies: List[str] = []

class JobPreferenceUpdate(JobPreferenceBase):
    pass

class JobPreferenceResponse(JobPreferenceBase):
    id: UUID
    user_id: UUID
    
    class Config:
        from_attributes = True
