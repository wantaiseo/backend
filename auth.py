"""
CiteKit – Authentication Module
Uses Supabase Auth for secure user management
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from supabase import create_client, Client
from config import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict
    message: str

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: str

# ============================================
# SUPABASE CLIENT
# ============================================

def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)

# ============================================
# AUTH DEPENDENCY
# ============================================

async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency to extract and validate the current user from JWT.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        supabase = get_supabase()
        # Verify the token with Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return {
            "id": user_response.user.id,
            "email": user_response.user.email,
            "created_at": str(user_response.user.created_at),
            "token": token
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# ============================================
# AUTH ENDPOINTS
# ============================================

@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """
    Create a new user account.
    """
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if response.user is None:
            raise HTTPException(status_code=400, detail="Signup failed. Please try again.")
        
        # Check if email confirmation is required
        if response.session is None:
            return AuthResponse(
                access_token="",
                refresh_token="",
                user={
                    "id": response.user.id,
                    "email": response.user.email,
                    "email_confirmed": False
                },
                message="Please check your email to confirm your account."
            )
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email,
                "email_confirmed": True
            },
            message="Account created successfully!"
        )
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        raise HTTPException(status_code=400, detail=f"Signup failed: {error_msg}")


@router.post("/login/google")
async def login_google():
    """
    Get the OAuth URL for Google login.
    """
    try:
        supabase = get_supabase()
        settings = get_settings()
        
        # Use FRONTEND_URL from env, fallback to localhost for dev
        frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:5173"
        redirect_url = f"{frontend_url}/auth/callback"
        
        data = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url
            }
        })
        
        if not data.url:
             raise HTTPException(status_code=400, detail="Could not generate OAuth URL")
             
        return {"url": data.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google login failed: {str(e)}")


@router.post("/exchange")
async def exchange_code(code: str):
    """
    Exchange OAuth code for session (PKCE flow).
    """
    try:
        supabase = get_supabase()
        # Exchange code for session
        response = supabase.auth.exchange_code_for_session({
            "auth_code": code
        })
        
        if response.user is None or response.session is None:
             raise HTTPException(status_code=400, detail="Invalid code or code expired")
             
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            },
            message="Login successful!"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Code exchange failed: {str(e)}")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT tokens.
    """
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if response.user is None or response.session is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return AuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user={
                "id": response.user.id,
                "email": response.user.email
            },
            message="Login successful!"
        )
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        raise HTTPException(status_code=401, detail=f"Login failed: {error_msg}")


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """
    Sign out the current user.
    """
    if not authorization:
        return {"message": "Already logged out"}
    
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        return {"message": "Logged out successfully"}
    except Exception:
        return {"message": "Logged out successfully"}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Refresh the access token using the refresh token.
    """
    try:
        supabase = get_supabase()
        response = supabase.auth.refresh_session(refresh_token)
        
        if response.session is None:
            raise HTTPException(status_code=401, detail="Could not refresh session")
        
        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token refresh failed: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """
    Get the current authenticated user's information.
    """
    return UserResponse(
        id=user["id"],
        email=user["email"],
        created_at=user["created_at"]
    )
