from uuid import uuid4

import pytest
from mimesis import Person
from sqlmodel import Session, create_engine

from app.controllers.user import pwd_context
from app.core.config import settings
from app.db.database import get_session
from app.main import app
from app.models.user import User, UserRole
from app.security.jwt import sign_jwt
from tests.conftest import generate_png_bytes


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.DATABASE_URL, echo=False)


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Generate test user data"""
    person = Person()
    return {
        "email": person.email(),
        "name": person.full_name(),
        "role": UserRole.VIEWER,
        "password": "TestPass123!",
    }


@pytest.fixture
def authenticated_user(session, test_user_data):
    """Create a user in the database and return user object"""
    hashed_password = pwd_context.hash(test_user_data["password"])

    user = User(
        uid=uuid4(),
        email=test_user_data["email"],
        name=test_user_data["name"],
        role=test_user_data["role"],
        password=hashed_password,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def auth_token(authenticated_user):
    """Generate JWT token for authenticated user"""
    user_data = {
        "uid": str(authenticated_user.uid),
        "email": authenticated_user.email,
        "name": authenticated_user.name,
        "role": authenticated_user.role,
    }

    token_response = sign_jwt(authenticated_user.uid, user_data)
    return token_response.access_token


@pytest.fixture
def auth_headers(auth_token):
    """Generate authorization headers"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def admin_user_data():
    """Generate test admin user data"""
    person = Person()
    return {
        "email": person.email(),
        "name": person.full_name(),
        "role": UserRole.ADMIN,
        "password": "AdminPass123!",
    }


@pytest.fixture
def admin_user(session, admin_user_data):
    """Create an admin user in the database and return user object"""
    hashed_password = pwd_context.hash(admin_user_data["password"])

    user = User(
        uid=uuid4(),
        email=admin_user_data["email"],
        name=admin_user_data["name"],
        role=admin_user_data["role"],
        password=hashed_password,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def admin_auth_token(admin_user):
    """Generate JWT token for admin user"""
    user_data = {
        "uid": str(admin_user.uid),
        "email": admin_user.email,
        "name": admin_user.name,
        "role": admin_user.role,
    }

    token_response = sign_jwt(admin_user.uid, user_data)
    return token_response.access_token


@pytest.fixture
def admin_auth_headers(admin_auth_token):
    """Generate authorization headers for admin user"""
    return {"Authorization": f"Bearer {admin_auth_token}"}


@pytest.fixture
def sample_png_bytes():
    """Generate a minimal valid PNG image (1x1 transparent pixel)"""
    return generate_png_bytes(1, 1)


@pytest.fixture
def user_with_photo(session, test_user_data, sample_png_bytes):
    """Create a user with a photo in the database"""
    hashed_password = pwd_context.hash(test_user_data["password"])

    user = User(
        uid=uuid4(),
        email=test_user_data["email"],
        name=test_user_data["name"],
        role=test_user_data["role"],
        password=hashed_password,
        photo=sample_png_bytes,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def user_with_photo_auth_token(user_with_photo):
    """Generate JWT token for user with photo"""
    user_data = {
        "uid": str(user_with_photo.uid),
        "email": user_with_photo.email,
        "name": user_with_photo.name,
        "role": user_with_photo.role,
    }

    token_response = sign_jwt(user_with_photo.uid, user_data)
    return token_response.access_token


@pytest.fixture
def user_with_photo_auth_headers(user_with_photo_auth_token):
    """Generate authorization headers for user with photo"""
    return {"Authorization": f"Bearer {user_with_photo_auth_token}"}
