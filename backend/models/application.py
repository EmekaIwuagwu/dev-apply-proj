import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_title = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    job_url = Column(Text, nullable=False)
    job_description = Column(Text)
    platform = Column(String(100))
    status = Column(String(50), default="pending")  # pending, reading, planning, applying, submitted, failed, skipped
    ai_match_score = Column(Float)
    ai_reasoning = Column(Text)
    cover_note = Column(Text)
    error_message = Column(Text)
    applied_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    run_date = Column(Date, nullable=False, default=func.current_date())
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    total_jobs_found = Column(Integer, default=0)
    total_applied = Column(Integer, default=0)
    total_skipped = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # running, completed, failed
    log_output = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    tier = Column(String(20), nullable=False, default="free")
    status = Column(String(20), nullable=False, default="active")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    stripe_customer_id = Column(String(255))
    stripe_subscription_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
