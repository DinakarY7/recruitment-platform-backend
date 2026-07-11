from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models import (
    User,
    Company,
    Job,
    JobCreate,
    JobResponse,
    JobType,
    ExperienceLevel
)
from app.auth import get_current_user, require_employer

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

# --- Endpoints ---

@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Post a new job. Only employers can post jobs under their company."""
    # Find employer's company
    company_stmt = select(Company).where(Company.employer_id == current_user.id)
    company_res = await session.execute(company_stmt)
    company = company_res.scalar_one_or_none()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employer must complete company profile before posting a job"
        )
        
    db_job = Job(
        **job_data.model_dump(),
        company_id=company.id
    )
    session.add(db_job)
    await session.commit()
    await session.refresh(db_job)
    
    # Construct response with company name
    return JobResponse(
        **db_job.model_dump(),
        company_name=company.name
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    q: Optional[str] = Query(None, description="Search term for job title, description or requirements"),
    location: Optional[str] = Query(None, description="Filter by location"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    experience_level: Optional[ExperienceLevel] = Query(None, description="Filter by experience level"),
    salary_min: Optional[float] = Query(None, description="Filter by minimum salary"),
    session: AsyncSession = Depends(get_session)
):
    """Lists and searches jobs with optional filtering. Accessible by anyone (public)."""
    # Select Job and Company Name
    stmt = select(Job, Company.name).join(Company, Job.company_id == Company.id).where(Job.is_active == True)
    
    conditions = []
    
    if q:
        search_pattern = f"%{q}%"
        conditions.append(
            or_(
                Job.title.ilike(search_pattern),
                Job.description.ilike(search_pattern),
                Job.requirements.ilike(search_pattern)
            )
        )
    if location:
        conditions.append(Job.location.ilike(f"%{location}%"))
    if job_type:
        conditions.append(Job.job_type == job_type)
    if experience_level:
        conditions.append(Job.experience_level == experience_level)
    if salary_min:
        conditions.append(Job.salary_max >= salary_min)  # make sure upper range covers min salary
        
    if conditions:
        stmt = stmt.where(and_(*conditions))
        
    # Order by newest
    stmt = stmt.order_by(Job.created_at.desc())
    
    result = await session.execute(stmt)
    jobs_with_companies = result.all()
    
    output = []
    for job, company_name in jobs_with_companies:
        output.append(
            JobResponse(
                **job.model_dump(),
                company_name=company_name
            )
        )
        
    return output


@router.get("/my-jobs", response_model=List[JobResponse])
async def list_my_jobs(
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Lists all jobs posted by the currently logged-in employer."""
    company_stmt = select(Company).where(Company.employer_id == current_user.id)
    company_res = await session.execute(company_stmt)
    company = company_res.scalar_one_or_none()
    
    if not company:
        return []
        
    stmt = select(Job, Company.name).join(Company, Job.company_id == Company.id).where(Job.company_id == company.id)
    stmt = stmt.order_by(Job.created_at.desc())
    
    result = await session.execute(stmt)
    jobs_with_companies = result.all()
    
    output = []
    for job, company_name in jobs_with_companies:
        output.append(
            JobResponse(
                **job.model_dump(),
                company_name=company_name
            )
        )
    return output


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_detail(
    job_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Gets details for a single job including the posting company name."""
    job_uuid = uuid.UUID(job_id)
    stmt = select(Job, Company.name).join(Company, Job.company_id == Company.id).where(Job.id == job_uuid)
    
    result = await session.execute(stmt)
    job_info = result.first()
    
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
        
    job, company_name = job_info
    return JobResponse(
        **job.model_dump(),
        company_name=company_name
    )


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_data: JobCreate,
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Updates a job listing. Only the owner company can modify their jobs."""
    job_uuid = uuid.UUID(job_id)
    # Check company ownership
    company_stmt = select(Company).where(Company.employer_id == current_user.id)
    company_res = await session.execute(company_stmt)
    company = company_res.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile incomplete")
        
    job = await session.get(Job, job_uuid)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    if job.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this job")
        
    for key, value in job_data.model_dump().items():
        setattr(job, key, value)
        
    await session.commit()
    await session.refresh(job)
    
    return JobResponse(
        **job.model_dump(),
        company_name=company.name
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Deletes a job listing. Only the owner company can delete their jobs."""
    job_uuid = uuid.UUID(job_id)
    company_stmt = select(Company).where(Company.employer_id == current_user.id)
    company_res = await session.execute(company_stmt)
    company = company_res.scalar_one_or_none()
    
    if not company:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile incomplete")
         
    job = await session.get(Job, job_uuid)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    if job.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this job")
        
    await session.delete(job)
    await session.commit()
    return None
