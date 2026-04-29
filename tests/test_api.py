import pytest
import httpx
import uuid
import asyncio
from app.main import app
import pytest_asyncio

BASE_URL = "http://testserver"

@pytest_asyncio.fixture(loop_scope="function")
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as ac:
        yield ac

@pytest.mark.asyncio
async def test_all_api_features(client):
    # 1. Register & Login Flow
    username = f"user_{uuid.uuid4().hex[:8]}"
    password = "testpassword123"
    
    register_response = await client.post("/auth/register", json={
        "username": username,
        "password": password
    })
    assert register_response.status_code == 200
    reg_json = register_response.json()
    assert reg_json["status"] is True
    user_id = reg_json["data"]["id"]

    login_response = await client.post("/auth/login", json={
        "username": username,
        "password": password
    })
    assert login_response.status_code == 200
    login_json = login_response.json()
    assert login_json["status"] is True
    tokens = login_json["data"]
    assert tokens["username"] == username
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Get Me
    me_response = await client.get("/users/me", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert me_response.status_code == 200
    me_json = me_response.json()
    assert me_json["status"] is True
    assert me_json["data"]["id"] == user_id

    # 3. Refresh Token
    await asyncio.sleep(1.1)
    refresh_response = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert refresh_response.status_code == 200
    refresh_json = refresh_response.json()
    assert refresh_json["status"] is True
    new_access_token = refresh_json["data"]["access_token"]
    assert new_access_token != access_token

    # 4. Chat History (Empty)
    u2_name = f"u2_{uuid.uuid4().hex[:8]}"
    r2 = await client.post("/auth/register", json={"username": u2_name, "password": "pw"})
    u2_id = r2.json()["data"]["id"]

    history_resp = await client.get(f"/messages/{u2_id}", headers={
        "Authorization": f"Bearer {new_access_token}"
    })
    assert history_resp.status_code == 200
    history_json = history_resp.json()
    assert history_json["status"] is True
    assert history_json["data"] == []

    # 5. Get User by ID
    user_response = await client.get(f"/users/{u2_id}", headers={
        "Authorization": f"Bearer {new_access_token}"
    })
    assert user_response.status_code == 200
    user_json = user_response.json()
    assert user_json["status"] is True
    assert user_json["data"]["username"] == u2_name

    # 6. User List with Pagination
    users_resp = await client.get("/users/", params={"page": 1, "size": 5}, headers={
        "Authorization": f"Bearer {new_access_token}"
    })
    assert users_resp.status_code == 200
    users_json = users_resp.json()
    assert users_json["status"] is True
    assert "items" in users_json["data"]
    assert users_json["data"]["page"] == 1
    assert users_json["data"]["size"] == 5
    assert len(users_json["data"]["items"]) >= 2  # We registered at least 2 users
