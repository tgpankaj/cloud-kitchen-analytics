"""
Pytest fixtures.
"""
import pytest # type: ignore
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import create_app


@pytest.fixture
def app():
    """Create test app."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    """Create user + return auth headers."""
    import random
    email = f'test{random.randint(10000, 99999)}@example.com'

    res = client.post('/api/auth/signup', json={
        'email': email,
        'password': 'test1234',
        'full_name': 'Test User',
        'kitchen_name': 'Test Kitchen',
        'city': 'Mumbai'
    })
    data = res.get_json()
    return {'Authorization': f'Bearer {data["token"]}'}