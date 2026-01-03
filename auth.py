"""
CiteKit – Authentication Module
Uses Supabase Auth for secure user management
"""

from datetime import datetime, timezone
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

class GoogleLoginRequest(BaseModel):
    redirect_url: Optional[str] = None

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
    print(f"🔔 [SIGNUP] Received signup request for: {request.email}")
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })
        
        if response.user is None:
            raise HTTPException(status_code=400, detail="Signup failed. Please try again.")
        
        # Check if user already exists (Supabase returns user but with empty identities for existing users)
        # Also check if email was already confirmed (means existing user)
        user_identities = getattr(response.user, 'identities', None)
        email_confirmed = getattr(response.user, 'email_confirmed_at', None)
        
        # If identities is empty list or email already confirmed, user exists
        if (user_identities is not None and len(user_identities) == 0) or email_confirmed:
            print(f"ℹ️ [SIGNUP] User already exists: {request.email}")
            raise HTTPException(
                status_code=400, 
                detail="An account with this email already exists. Please log in instead."
            )
        
        print(f"✅ [SIGNUP] User created successfully: {request.email}")
        
        # Send welcome email (non-blocking)
        try:
            print(f"📧 [SIGNUP] Attempting to send welcome email...")
            from email_service import get_email_service
            email_service = get_email_service()
            result = email_service.send_welcome_email(to_email=request.email)
            print(f"📧 [SIGNUP] Welcome email result: {result}")
        except Exception as email_err:
            print(f"⚠️ [SIGNUP] Welcome email EXCEPTION: {email_err}")
        
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
    except HTTPException:
        # Re-raise HTTP exceptions as-is (e.g., user already exists)
        raise
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower():
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
        raise HTTPException(status_code=400, detail=f"Signup failed: {error_msg}")


@router.post("/login/google")
async def login_google(request: Optional[GoogleLoginRequest] = None):
    """
    Get the OAuth URL for Google login.
    Uses implicit flow to return tokens directly in URL hash.
    """
    try:
        supabase = get_supabase()
        settings = get_settings()
        
        # Determine Redirect URL
        if request and request.redirect_url:
            redirect_url = request.redirect_url
        else:
            # Use FRONTEND_URL from env, fallback to Production (wantaiseo.com)
            frontend_url = getattr(settings, 'frontend_url', None) or "https://wantaiseo.com"
            redirect_url = f"{frontend_url}/auth/callback"
        
        # Use implicit flow - tokens come directly in URL hash
        # This avoids PKCE code verifier issues between frontend and backend
        data = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url,
                "skip_browser_redirect": True,  # We handle redirect ourselves
                "query_params": {
                    "response_type": "token"  # Force implicit flow (tokens in hash)
                }
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
        
        # Check if new user (approximate via created_at timestamp)
        # Send welcome email only if account is fresher than 2 minutes
        try:
            # Handle string vs datetime object form of created_at
            created_at_str = str(response.user.created_at)
            # Basic ISO parsing (works for Supabase format like 2023-10-10T10:10:10.123Z)
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            
            # Helper for current UTC time
            now = datetime.now(timezone.utc)
            
            if (now - created_at).total_seconds() < 120:
                print(f"🎉 New Google User Detected: {response.user.email}")
                from email_service import get_email_service
                get_email_service().send_welcome_email(to_email=response.user.email)
            else:
                age = int((now - created_at).total_seconds())
                print(f"ℹ️ Google Login: User {response.user.email} is not new (Age: {age}s).")
        except Exception as e:
            print(f"⚠️ Failed to check new user status: {e}")

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


@router.post("/check-welcome")
async def check_welcome_email(user: dict = Depends(get_current_user)):
    """
    Trigger welcome email if user is new (Implicit Flow support).
    """
    try:
        # Handle string vs datetime object form of created_at
        created_at_str = str(user.get("created_at"))
        # Basic ISO parsing (works for Supabase format like 2023-10-10T10:10:10.123Z)
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        
        # Helper for current UTC time
        now = datetime.now(timezone.utc)
        
        # If created in last 2 minutes
        if (now - created_at).total_seconds() < 120:
            print(f"🎉 New User Detected (Check Endpoint): {user['email']}")
            from email_service import get_email_service
            get_email_service().send_welcome_email(to_email=user["email"])
            return {"status": "sent", "message": "Welcome email sent"}
        else:
            age = int((now - created_at).total_seconds())
            print(f"ℹ️ Welcome Check: User {user['email']} is not new (Age: {age}s). Skipping email.")
            return {"status": "skipped", "message": "User not new"}
        
    except Exception as e:
        print(f"⚠️ Welcome check failed: {e}")
        return {"status": "error", "message": str(e)}


# ============================================
# PASSWORD RESET
# ============================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    access_token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Send password reset email via Supabase.
    """
    try:
        supabase = get_supabase()
        settings = get_settings()
        
        # Get frontend URL for redirect
        frontend_url = settings.frontend_url or "https://wantaiseo.com"
        redirect_url = f"{frontend_url}/reset-password"
        
        # Trigger Supabase password reset email
        supabase.auth.reset_password_email(
            request.email,
            options={
                "redirect_to": redirect_url
            }
        )
        
        return {
            "success": True,
            "message": "If an account exists with this email, you will receive a password reset link."
        }
    except Exception as e:
        # Don't reveal if email exists or not (security)
        print(f"⚠️ Password reset request failed: {e}")
        return {
            "success": True,
            "message": "If an account exists with this email, you will receive a password reset link."
        }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password using access token from email link.
    """
    try:
        supabase = get_supabase()
        
        # Set session with the access token from the email link
        # Then update the password
        response = supabase.auth.update_user({
            "password": request.new_password
        })
        
        if response.user is None:
            raise HTTPException(status_code=400, detail="Password reset failed. The link may have expired.")
        
        return {
            "success": True,
            "message": "Password updated successfully! You can now log in with your new password."
        }
    except Exception as e:
        error_msg = str(e)
        print(f"⚠️ Password reset failed: {error_msg}")
        raise HTTPException(status_code=400, detail="Password reset failed. Please request a new reset link.")

