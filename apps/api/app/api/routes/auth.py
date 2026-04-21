
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import create_access_token, get_current_user
from app.api.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.db.models import Organization, OrgMembership, OrgRole, User
from app.db.session import get_db

router = APIRouter()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    # Check existing user
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create org
    slug = req.org_name.lower().replace(" ", "-")[:100]
    org = Organization(name=req.org_name, slug=slug)
    db.add(org)
    await db.flush()

    # Create user (password hashed)
    user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.flush()

    # Create membership (owner)
    membership = OrgMembership(user_id=user.id, org_id=org.id, role=OrgRole.OWNER)
    db.add(membership)

    token = create_access_token(user.id, org.id)
    return TokenResponse(access_token=token, expires_in=86400)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials — this account may use SSO only",
        )
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get the user's first org for the token
    result = await db.execute(
        select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1)
    )
    membership = result.scalar_one_or_none()
    org_id = membership.org_id if membership else None

    token = create_access_token(user.id, org_id)
    return TokenResponse(access_token=token, expires_in=86400)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    # Resolve the user's role in their org
    result = await db.execute(
        select(OrgMembership).where(OrgMembership.user_id == user.id).limit(1)
    )
    membership = result.scalar_one_or_none()
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        role=membership.role.value if membership else None,
        created_at=user.created_at,
    )
