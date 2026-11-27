"""Local admin access-control smoke tests; no production database writes."""
from fastapi.testclient import TestClient
from server import app

def test_admin_requires_session():
    client = TestClient(app, base_url="http://localhost")
    # TestClient is not a loopback peer; rejection is expected.
    assert client.get("/api/admin/overview").status_code in (401,403)

def test_cross_origin_login_denied():
    client = TestClient(app, base_url="http://localhost")
    assert client.post("/api/admin/login",json={"password":"not-a-real-password"},headers={"Origin":"https://example.invalid"}).status_code == 403

def test_private_files_not_served():
    client = TestClient(app,base_url="http://localhost")
    for path in ("/database.py","/admin.py","/.gitignore","/owner.hash"):
        assert client.get(path).status_code == 404
