from uuid import uuid4

import pytest
from mimesis import Person
from sqlmodel import Session, create_engine

from app.controllers.user import pwd_context
from app.core.config import settings
from app.models.user import User, UserRole
from app.security.jwt import sign_jwt


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.DATABASE_URL, echo=False)


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


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
