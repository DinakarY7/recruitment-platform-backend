from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models import (
    User,
    UserRole,
    CandidateProfile,
    CandidateProfileCreate,
    CandidateProfileResponse,
    Company,
    CompanyCreate,
    CompanyResponse
)
from app.auth import get_current_user, require_candidate, require_employer

router = APIRouter(prefix="/api/profiles", tags=["Profiles"])

# --- Candidate Profile Endpoints ---

@router.get("/candidate", response_model=CandidateProfileResponse)
async def get_candidate_profile(
    current_user: User = Depends(require_candidate),
    session: AsyncSession = Depends(get_session)
):
    """Retrieves current candidate's profile."""
    statement = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    result = await session.execute(statement)
    profile = result.scalar_one_or_none()
    
    if not profile:
        # If it doesn't exist for some reason, create a blank one
        profile = CandidateProfile(user_id=current_user.id, full_name=current_user.email.split("@")[0].capitalize())
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        
    return profile


@router.put("/candidate", response_model=CandidateProfileResponse)
async def update_candidate_profile(
    profile_data: CandidateProfileCreate,
    current_user: User = Depends(require_candidate),
    session: AsyncSession = Depends(get_session)
):
    """Updates current candidate's profile."""
    statement = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    result = await session.execute(statement)
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = CandidateProfile(user_id=current_user.id, full_name=profile_data.full_name)
        session.add(profile)
    
    # Update fields dynamically
    for key, value in profile_data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
        
    await session.commit()
    await session.refresh(profile)
    return profile


# --- Company Profile Endpoints ---

@router.get("/company", response_model=CompanyResponse)
async def get_company_profile(
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Retrieves current employer's company profile."""
    statement = select(Company).where(Company.employer_id == current_user.id)
    result = await session.execute(statement)
    company = result.scalar_one_or_none()
    
    if not company:
        # Create a default company profile if not exists
        company = Company(employer_id=current_user.id, name="My Company")
        session.add(company)
        await session.commit()
        await session.refresh(company)
        
    return company


@router.put("/company", response_model=CompanyResponse)
async def update_company_profile(
    company_data: CompanyCreate,
    current_user: User = Depends(require_employer),
    session: AsyncSession = Depends(get_session)
):
    """Updates current employer's company profile."""
    statement = select(Company).where(Company.employer_id == current_user.id)
    result = await session.execute(statement)
    company = result.scalar_one_or_none()
    
    if not company:
        company = Company(employer_id=current_user.id, name=company_data.name)
        session.add(company)
        
    for key, value in company_data.model_dump(exclude_unset=True).items():
        setattr(company, key, value)
        
    await session.commit()
    await session.refresh(company)
    return company


# --- Public Endpoints ---

@router.get("/company/{company_id}", response_model=CompanyResponse)
async def get_public_company_profile(
    company_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Retrieves public details of a company."""
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
