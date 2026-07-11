from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.models import (
    User,
    UserCreate,
    UserResponse,
    UserRole,
    CandidateProfile,
    Company
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# --- Helper schemas for JSON response/request ---

class Token(BaseModel):
    access_token: str
    token_type: str
    role: UserRole

class JSONLoginRequest(BaseModel):
    email: EmailStr
    password: str

# --- Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    """Registers a new user (candidate or employer)."""
    # Check if user already exists
    statement = select(User).where(User.email == user_in.email)
    result = await session.execute(statement)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    
    # Hash password and save user
    hashed = hash_password(user_in.password)
    db_user = User(
        email=user_in.email,
        role=user_in.role,
        hashed_password=hashed
    )
    session.add(db_user)
    await session.flush()  # Populates db_user.id
    
    # Pre-populate related profiles
    if db_user.role == UserRole.CANDIDATE:
        profile = CandidateProfile(
            user_id=db_user.id,
            full_name=user_in.email.split("@")[0].capitalize(),  # default name from email
            skills=[]
        )
        session.add(profile)
    elif db_user.role == UserRole.EMPLOYER:
        company = Company(
            employer_id=db_user.id,
            name="My Company"  # default name
        )
        session.add(company)
        
    await session.commit()
    await session.refresh(db_user)
    return db_user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    """Logins user and returns access token. Supports Form data (Swagger) and JSON body."""
    email = None
    password = None
    
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email")
            password = body.get("password")
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide email/username and password"
        )
        
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

        
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Retrieves current user profile information."""
    return current_user
