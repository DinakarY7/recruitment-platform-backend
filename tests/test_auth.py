import pytest
from httpx import AsyncClient
from app.models import UserRole

@pytest.mark.asyncio
async def test_register_candidate(client: AsyncClient):
    """Test candidate user registration."""
    payload = {
        "email": "testcandidate@example.com",
        "password": "strongpassword123",
        "role": UserRole.CANDIDATE
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == "testcandidate@example.com"
    assert data["role"] == UserRole.CANDIDATE
    assert "id" in data

@pytest.mark.asyncio
async def test_register_employer(client: AsyncClient):
    """Test employer user registration."""
    payload = {
        "email": "testemployer@example.com",
        "password": "strongpassword123",
        "role": UserRole.EMPLOYER
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["email"] == "testemployer@example.com"
    assert data["role"] == UserRole.EMPLOYER
    assert "id" in data

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    """Test user login and token generation."""
    # Register candidate first
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "loginpassword",
        "role": UserRole.CANDIDATE
    }
    await client.post("/api/auth/register", json=reg_payload)
    
    # Login
    login_payload = {
        "email": "loginuser@example.com",
        "password": "loginpassword"
    }
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == UserRole.CANDIDATE

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    """Test getting current user profile with JWT authentication."""
    # Register and login
    email = "meuser@example.com"
    password = "mepassword"
    await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "role": UserRole.CANDIDATE
    })
    
    login_res = await client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    token = login_res.json()["access_token"]
    
    # Fetch /api/auth/me using headers
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email
