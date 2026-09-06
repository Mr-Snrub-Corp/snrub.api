from uuid import uuid4

import pytest
from mimesis import Person
from sqlmodel import Session, create_engine

from app.controllers.user import pwd_context
from app.core.config import settings
from app.db.database import get_session
from app.main import app
from app.models.incident_category import IncidentCategory
from app.models.incident_report import EscalationLevel, IncidentReport, IncidentStatus
from app.models.incident_type import IncidentType
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
    token_response = sign_jwt(authenticated_user.uid, authenticated_user.to_jwt_data())
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
    token_response = sign_jwt(admin_user.uid, admin_user.to_jwt_data())
    return token_response.access_token


@pytest.fixture
def admin_auth_headers(admin_auth_token):
    """Generate authorization headers for admin user"""
    return {"Authorization": f"Bearer {admin_auth_token}"}


@pytest.fixture
def super_admin_user_data():
    """Generate test super admin user data"""
    person = Person()
    return {
        "email": person.email(),
        "name": person.full_name(),
        "role": UserRole.SUPER_ADMIN,
        "password": "SuperAdminPass123!",
    }


@pytest.fixture
def super_admin_user(session, super_admin_user_data):
    """Create a super admin user in the database and return user object"""
    hashed_password = pwd_context.hash(super_admin_user_data["password"])

    user = User(
        uid=uuid4(),
        email=super_admin_user_data["email"],
        name=super_admin_user_data["name"],
        role=super_admin_user_data["role"],
        password=hashed_password,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def super_admin_auth_token(super_admin_user):
    """Generate JWT token for super admin user"""
    token_response = sign_jwt(super_admin_user.uid, super_admin_user.to_jwt_data())
    return token_response.access_token


@pytest.fixture
def super_admin_auth_headers(super_admin_auth_token):
    """Generate authorization headers for super admin user"""
    return {"Authorization": f"Bearer {super_admin_auth_token}"}


@pytest.fixture
def sample_category(session):
    cat = IncidentCategory(code=f"test_cat_{uuid4().hex[:8]}", name="Test Category")
    session.add(cat)
    session.commit()
    session.refresh(cat)
    return cat


@pytest.fixture
def sample_type(session, sample_category):
    t = IncidentType(
        code=f"test_type_{uuid4().hex[:8]}",
        name="Test Type",
        category_id=sample_category.uid,
        default_severity=3,
    )
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def godmode_incident_types(session, sample_category):
    """Ensure the five God-mode lever incident types exist (idempotent get-or-create)."""
    from sqlmodel import select

    from app.controllers.godmode import LEVER_CODE_MAP

    types = {}
    for code in LEVER_CODE_MAP.values():
        existing = session.exec(select(IncidentType).where(IncidentType.code == code)).first()
        if existing:
            types[code] = existing
            continue
        t = IncidentType(
            code=code,
            name=code.replace("_", " ").title(),
            category_id=sample_category.uid,
            default_severity=5,
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        types[code] = t
    return types


@pytest.fixture
def creator_user(session):
    person = Person()
    hashed_password = pwd_context.hash("CreatorPass123!")
    user = User(
        uid=uuid4(),
        email=person.email(),
        name=person.full_name(),
        role=UserRole.CREATOR,
        password=hashed_password,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def creator_auth_token(creator_user):
    token_response = sign_jwt(creator_user.uid, creator_user.to_jwt_data())
    return token_response.access_token


@pytest.fixture
def creator_auth_headers(creator_auth_token):
    return {"Authorization": f"Bearer {creator_auth_token}"}


@pytest.fixture
def sample_report(session, sample_type, creator_user):
    from datetime import datetime

    report = IncidentReport(
        incident_type_id=sample_type.uid,
        severity=4,
        status=IncidentStatus.REPORTED,
        escalation_level=EscalationLevel.NONE,
        reported_by_user_id=creator_user.uid,
        occurred_at=datetime.utcnow(),
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


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
    token_response = sign_jwt(user_with_photo.uid, user_with_photo.to_jwt_data())
    return token_response.access_token


@pytest.fixture
def user_with_photo_auth_headers(user_with_photo_auth_token):
    """Generate authorization headers for user with photo"""
    return {"Authorization": f"Bearer {user_with_photo_auth_token}"}
