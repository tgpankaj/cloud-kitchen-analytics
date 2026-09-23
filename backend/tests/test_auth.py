"""
Auth endpoint tests.
Run: pytest tests/test_auth.py -v
"""
import random


def test_health(client):
    res = client.get('/api/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'ok'


def test_signup_and_login(client):
    email = f'test{random.randint(10000, 99999)}@example.com'

    # Signup
    res = client.post('/api/auth/signup', json={
        'email': email,
        'password': 'test1234',
        'full_name': 'Test User',
        'kitchen_name': 'Test Kitchen',
        'city': 'Mumbai'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert 'token' in data
    assert data['user']['email'] == email

    # Login
    res = client.post('/api/auth/login', json={
        'email': email, 'password': 'test1234'
    })
    assert res.status_code == 200
    assert 'token' in res.get_json()


def test_login_wrong_password(client):
    res = client.post('/api/auth/login', json={
        'email': 'nonexistent@example.com',
        'password': 'wrong'
    })
    assert res.status_code == 401


def test_me_unauthorized(client):
    res = client.get('/api/auth/me')
    assert res.status_code == 401


def test_me_authorized(client, auth_headers):
    res = client.get('/api/auth/me', headers=auth_headers)
    assert res.status_code == 200
    assert 'user' in res.get_json()