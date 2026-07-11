from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import ARRAY, VARCHAR

# --- ENUMS ---

class UserRole(str, Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"

class JobType(str, Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"

class ExperienceLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"

class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    REVIEWING = "reviewing"
    SHORTLISTED = "shortlisted"
    INTERVIEWING = "interviewing"
    HIRED = "hired"
    REJECTED = "rejected"

# --- DB MODELS & SCHEMAS ---

# User Models
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True)
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")}
    )
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    company: Optional["Company"] = Relationship(back_populates="employer", sa_relationship_kwargs={"uselist": False})
    candidate_profile: Optional["CandidateProfile"] = Relationship(back_populates="user", sa_relationship_kwargs={"uselist": False})


# Company Models
class CompanyBase(SQLModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    location: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: uuid.UUID
    employer_id: uuid.UUID
    created_at: datetime

class Company(CompanyBase, table=True):
    __tablename__ = "companies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    employer_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    employer: User = Relationship(back_populates="company")
    jobs: List["Job"] = Relationship(back_populates="company")


# Candidate Profile Models
class CandidateProfileBase(SQLModel):
    full_name: str
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    skills: List[str] = Field(default=[], sa_column=Column(ARRAY(VARCHAR(255))))
    experience_years: int = Field(default=0)
    current_company: Optional[str] = None
    education: Optional[str] = None

class CandidateProfileCreate(CandidateProfileBase):
    pass

class CandidateProfileResponse(CandidateProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

class CandidateProfile(CandidateProfileBase, table=True):
    __tablename__ = "candidate_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="candidate_profile")
    applications: List["Application"] = Relationship(back_populates="candidate")


# Job Models
class JobBase(SQLModel):
    title: str
    description: str
    requirements: str
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = "INR"
    location: str
    job_type: JobType
    experience_level: ExperienceLevel
    is_active: bool = True

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    company_name: Optional[str] = None

class Job(JobBase, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    company_id: uuid.UUID = Field(foreign_key="companies.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    company: Company = Relationship(back_populates="jobs")
    applications: List["Application"] = Relationship(back_populates="job")


# Application Models
class ApplicationBase(SQLModel):
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    job_id: uuid.UUID

class ApplicationUpdateStatus(SQLModel):
    status: ApplicationStatus

class ApplicationResponse(ApplicationBase):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    candidate_name: Optional[str] = None

class Application(ApplicationBase, table=True):
    __tablename__ = "applications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", index=True)
    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", index=True)
    status: ApplicationStatus = Field(default=ApplicationStatus.APPLIED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    job: Job = Relationship(back_populates="applications")
    candidate: CandidateProfile = Relationship(back_populates="applications")
