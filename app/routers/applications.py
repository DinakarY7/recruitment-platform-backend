from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models import (
    User,
    CandidateProfile,
    Company,
    Job,
    Application,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdateStatus
)
from app.auth import get_current_user, require_candidate, require_employer

router = APIRouter(prefix="/api/applications", tags=["Applications"])

# --- Endpoints ---

@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    application_in: ApplicationCreate,
    current_user: User = Depends(require_candidate),
    session: AsyncSession = Depends(get_session)
):
    """Submits a job application for the current candidate."""
    # Find candidate profile
    profile_stmt = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    profile_res = await session.execute(profile_stmt)
    profile = profile_res.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete candidate profile before applying to jobs"
        )
        
    # Check if job exists and is active
    job = await session.get(Job, application_in.job_id)
    if not job or not job.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting is no longer active or does not exist"
        )
        
    # Check if already applied
    stmt = select(Application).where(
        Application.job_id == application_in.job_id,
        Application.candidate_id == profile.id
    )
    res = await session.execute(stmt)
    existing_app = res.scalar_one_or_none()
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job"
        )
        
    # Create application (use candidate's resume by default if cover letter doesn't override resume url)
    db_application = Application(
        job_id=application_in.job_id,
        candidate_id=profile.id,
        resume_url=application_in.resume_url or profile.resume_url,
        cover_letter=application_in.cover_letter
    )
    
    session.add(db_application)
    await session.commit()
    await session.refresh(db_application)
    
    # Return response joined with company details
    company = await session.get(Company, job.company_id)
    return ApplicationResponse(
        **db_application.model_dump(),
        job_title=job.title,
        company_name=company.name if company else "Unknown",
        candidate_name=profile.full_name
    )


@router.get("/my-applications", response_model=List[ApplicationResponse])
async def list_my_applications(
    current_user: User = Depends(require_candidate),
    session: AsyncSession = Depends(get_session)
):
    """Lists all job applications submitted by the current candidate."""
    profile_stmt = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    profile_res = await session.execute(profile_stmt)
    profile = profile_res.scalar_one_or_none()
    
    if not profile:
        return []
        
    stmt = select(Application, Job.title, Company.name)\
        .join(Job, Application.job_id == Job.id)\
        .join(Company, Job.company_id == Company.id)\
        .where(Application.candidate_id == profile.id)\
        .order_by(Application.created_at.desc())
        
    result = await session.execute(stmt)
    apps_with_details = result.all()
    
    output = []
    for app, job_title, company_name in apps_with_details:
        output.append(
            ApplicationResponse(
                **app.model_dump(),
                job_title=job_title,
                company_name=company_name,
                candidate_name=profile.full_name
            )
        )
    return output


@router.get("/job/{job_id}", response_model=List[ApplicationResponse])
async def list_job_applicants(
    job_id: str,
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Lists all applicants for a specific job. Only the job owner (employer) can access."""
    job_uuid = uuid.UUID(job_id)
    
    # Verify employer owns this job
    company_stmt = select(Company).where(Company.employer_id == current_user.id)
    company_res = await session.execute(company_stmt)
    company = company_res.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile incomplete")
        
    job = await session.get(Job, job_uuid)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        
    if job.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view applicants for this job")
        
    stmt = select(Application, CandidateProfile.full_name, Job.title)\
        .join(CandidateProfile, Application.candidate_id == CandidateProfile.id)\
        .join(Job, Application.job_id == Job.id)\
        .where(Application.job_id == job_uuid)\
        .order_by(Application.created_at.desc())
        
    result = await session.execute(stmt)
    apps_with_details = result.all()
    
    output = []
    for app, candidate_name, job_title in apps_with_details:
        output.append(
            ApplicationResponse(
                **app.model_dump(),
                job_title=job_title,
                company_name=company.name,
                candidate_name=candidate_name
            )
        )
    return output


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: str,
    status_data: ApplicationUpdateStatus,
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Updates an application status. Only the owner employer of the job listing can update it."""
    app_uuid = uuid.UUID(application_id)
    
    company_stmt = select(Company).where(Company.employer_id == current_user.id)
    company_res = await session.execute(company_stmt)
    company = company_res.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Profile incomplete")
        
    app = await session.get(Application, app_uuid)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        
    job = await session.get(Job, app.job_id)
    if not job or job.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update status for this job application")
        
    app.status = status_data.status
    await session.commit()
    await session.refresh(app)
    
    candidate = await session.get(CandidateProfile, app.candidate_id)
    return ApplicationResponse(
        **app.model_dump(),
        job_title=job.title,
        company_name=company.name,
        candidate_name=candidate.full_name if candidate else "Unknown"
    )
