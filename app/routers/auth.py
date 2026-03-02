"""
Authentication router
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, Token, LoginRequest
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Configure password context with bcrypt
# Using 'bcrypt' scheme with proper configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash. Works with both bcrypt and passlib formats."""
    try:
        # Try passlib verification first (for older hashes or passlib format)
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        # If passlib fails, try bcrypt directly (for new bcrypt hashes)
        try:
            password_bytes = plain_password.encode('utf-8')
            if len(password_bytes) > 72:
                password_bytes = password_bytes[:72]
            hash_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            return False


def get_password_hash(password: str) -> str:
    """Hash password using bcrypt. Bcrypt has a 72-byte limit."""
    # Ensure password is a string
    if not isinstance(password, str):
        password = str(password)
    
    # Convert to bytes for bcrypt (bcrypt works with bytes)
    password_bytes = password.encode('utf-8')
    
    # Bcrypt has a strict 72-byte limit - truncate if necessary
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Use bcrypt directly to hash - this avoids passlib issues
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    
    # Return as string (passlib format compatible)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_EXPIRATION_DAYS)
    # JWT exp must be numeric Unix timestamp (RFC 7519)
    to_encode.update({"exp": int(expire.timestamp())})
    # Ensure sub is int for consistent lookup
    if "sub" in to_encode and not isinstance(to_encode["sub"], int):
        to_encode["sub"] = int(to_encode["sub"])
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt if isinstance(encoded_jwt, str) else encoded_jwt.decode("utf-8")


def _auth_error(reason: str, hint: str = None):
    """Build 401 response with reason for debugging."""
    detail = "Could not validate credentials"
    if hint:
        detail = f"{detail}: {hint}"
    logger.warning("Auth validation failed: %s", reason)
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    token = (token or "").strip()
    if not token:
        raise _auth_error("missing_token", "no token provided")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise _auth_error("invalid_payload", "token missing 'sub' claim")
        user_id = int(sub) if not isinstance(sub, int) else sub
    except JWTError as e:
        logger.warning("JWT decode failed: %s", str(e))
        raise _auth_error(
            "jwt_decode_failed",
            f"invalid or expired token (check JWT_SECRET_KEY matches between deployments)",
        )
    except (TypeError, ValueError) as e:
        raise _auth_error("invalid_sub", f"invalid user id in token: {e}")
    except Exception as e:
        logger.warning("Token validation error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}" if settings.DEBUG else "Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
    except SQLAlchemyError as e:
        logger.error(
            "Database error during auth (Vercel Postgres): %s",
            str(e),
            exc_info=True,
            extra={"user_id": user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user is None:
        raise _auth_error("user_not_found", f"user id {user_id} not found in database")
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, user_data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Validate password strength
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Validate username
    if len(user_data.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    
    # Check if user exists
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    logger = logging.getLogger(__name__)
    try:
        # Create new user
        # Log password length for debugging (don't log actual password!)
        password_len = len(user_data.password)
        password_bytes_len = len(user_data.password.encode('utf-8'))
        logger.info(f"Password length: {password_len} chars, {password_bytes_len} bytes")
        
        hashed_password = get_password_hash(user_data.password)
        user = User(
            email=user_data.email.lower().strip(),
            username=user_data.username.strip(),
            full_name=user_data.full_name.strip() if user_data.full_name else None,
            password_hash=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Optionally issue token on registration (auto-login)
        # Uncomment the lines below if you want to return a token on registration
        # access_token = create_access_token(data={"sub": user.id})
        # return {"user": user, "access_token": access_token, "token_type": "bearer"}
        
        # For now, just return user (mobile app will auto-login after registration)
        return user
    except HTTPException:
        # Re-raise HTTP exceptions (like from get_password_hash)
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            "Database error during registration (Vercel Postgres): %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    logger = logging.getLogger(__name__)
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify password
        if not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create and return access token
        access_token = create_access_token(data={"sub": user.id})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        # Re-raise HTTP exceptions (like authentication errors)
        raise
    except SQLAlchemyError as e:
        logger.error(
            "Database error during login (Vercel Postgres): %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.get("/verify-token")
async def verify_token_debug(token: str = Depends(oauth2_scheme)):
    """
    Debug endpoint: Decode JWT and return payload (no DB lookup).
    Helps diagnose if 401 is from JWT decode or user lookup.
    Only returns payload when DEBUG=true.
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not found")
    token = (token or "").strip()
    if not token:
        return {"error": "No token provided"}
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return {"valid": True, "payload": payload, "user_id": payload.get("sub")}
    except JWTError as e:
        return {"valid": False, "error": str(e), "hint": "JWT decode failed - check JWT_SECRET_KEY matches between login and this request"}


