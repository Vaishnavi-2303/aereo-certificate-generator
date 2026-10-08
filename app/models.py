from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .database import Base

class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    id = Column(String, primary_key=True)
    total = Column(Integer, nullable=False)
    successful = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    recipients = relationship("Recipient", back_populates="job", cascade="all, delete-orphan")

class Recipient(Base):
    __tablename__ = "recipients"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("generation_jobs.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    course = Column(String, nullable=False)
    completion_date = Column(String, nullable=False)
    status = Column(String, default="pending")
    error = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    job = relationship("GenerationJob", back_populates="recipients")
