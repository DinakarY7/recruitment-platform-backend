import pytest
from httpx import AsyncClient
from app.models import UserRole, JobType, ExperienceLevel

@pytest.mark.asyncio
async def test_create_and_list_jobs(client: AsyncClient):
    """Test job posting by employer and public search capabilities."""
    # 1. Register and login as employer
    emp_email = "jobemployer@example.com"
    password = "jobpassword"
    await client.post("/api/auth/register", json={
        "email": emp_email,
        "password": password,
        "role": UserRole.EMPLOYER
    })
    
    login_res = await client.post("/api/auth/login", json={
        "email": emp_email,
        "password": password
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Update company profile (needed to post jobs)
    await client.put("/api/profiles/company", json={
        "name": "Acme Industries",
        "description": "Premium industrial services",
        "website": "https://acme.org",
        "location": "Bangalore"
    }, headers=headers)
    
    # 3. Post a job
    job_payload = {
        "title": "Senior Python Developer",
        "description": "Build high-performance web applications using FastAPI",
        "requirements": "3+ years Python experience, FastAPI or Django proficiency",
        "salary_min": 800000,
        "salary_max": 1500000,
        "currency": "INR",
        "location": "Bangalore",
        "job_type": JobType.HYBRID,
        "experience_level": ExperienceLevel.SENIOR,
        "is_active": True
    }
    post_res = await client.post("/api/jobs", json=job_payload, headers=headers)
    assert post_res.status_code == 201
    job_data = post_res.json()
    assert job_data["title"] == "Senior Python Developer"
    assert job_data["company_name"] == "Acme Industries"
    job_id = job_data["id"]
    
    # 4. Search/List jobs publicly (anonymous client call)
    list_res = await client.get("/api/jobs?location=Bangalore&job_type=hybrid")
    assert list_res.status_code == 200
    jobs = list_res.json()
    assert len(jobs) >= 1
    assert jobs[0]["title"] == "Senior Python Developer"
    
    # 5. Fetch single job details
    detail_res = await client.get(f"/api/jobs/{job_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["company_name"] == "Acme Industries"
