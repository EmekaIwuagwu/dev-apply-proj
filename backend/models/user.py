import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime, Float, Integer, ForeignKey, Date, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    salutation = Column(String(10), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    linkedin_url = Column(String(500))
    telephone = Column(String(30), nullable=False)
    bio = Column(Text, nullable=False)
    resume_base64 = Column(Text, nullable=False)
    resume_filename = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    agent_enabled = Column(Boolean, default=True)
    tier = Column(String(20), default="free", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class JobPreference(Base):
    __tablename__ = "job_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    job_titles = Column(ARRAY(String), nullable=False)
    skills = Column(ARRAY(String), nullable=False)
    experience_level = Column(String(50))
    job_type = Column(String(50))
    preferred_locations = Column(ARRAY(String))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    excluded_companies = Column(ARRAY(String))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
