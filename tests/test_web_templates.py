from fastapi.testclient import TestClient

from app.main import app


def test_login_page_renders():
    response = TestClient(app).get('/login')

    assert response.status_code == 200
    assert 'Willkommen bei GlobalStay.' in response.text
