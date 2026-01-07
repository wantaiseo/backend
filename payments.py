"""
CiteKit – Razorpay Payment Gateway Integration
Handles order creation, payment verification, and webhook processing
"""

import hmac
import hashlib
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel
import razorpay

from config import get_settings
from database import get_database
from auth import get_current_user

router = APIRouter(prefix="/payment", tags=["Payments"])

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

# Pricing by country
PRICING_CONFIG = {
    "IN": {"amount": 90000, "currency": "INR"},  # ₹900 in paise
    "DEFAULT": {"amount": 1000, "currency": "USD"},  # $10 in cents
}


class CreateOrderRequest(BaseModel):
    job_id: str
    country: Optional[str] = None  # Country code for pricing (e.g., 'IN' for India)


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str  # Frontend needs this to open checkout


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    job_id: str


class PaymentStatusResponse(BaseModel):
    job_id: str
    is_paid: bool
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    paid_at: Optional[str] = None


# ============================================
# RAZORPAY CLIENT
# ============================================

def get_razorpay_client() -> razorpay.Client:
    """Get configured Razorpay client"""
    settings = get_settings()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(
            status_code=500, 
            detail="Razorpay credentials not configured"
        )
    return razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))


# ============================================
# PAYMENT ENDPOINTS
# ============================================

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_payment_order(
    request: CreateOrderRequest,
    user: dict = Depends(get_current_user)
):
    """
    Create a Razorpay order for a job.
    Returns order details needed to open Razorpay checkout.
    """
    settings = get_settings()
    db = get_database()
    
    # 1. Verify job exists and belongs to user
    job = await db.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 2. Check job status - only allow payment for completed jobs
    if job.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot pay for job with status '{job.status}'. Job must be completed."
        )
    
    # 3. Check if job already has a payment
    if job.payment_id:
        raise HTTPException(status_code=400, detail="Job already paid")
    
    # 3. Check for existing pending order (idempotency)
    existing_order = await db.get_pending_payment_order(request.job_id)
    if existing_order:
        return CreateOrderResponse(
            order_id=existing_order["razorpay_order_id"],
            amount=existing_order["amount"],
            currency=existing_order["currency"],
            key_id=settings.razorpay_key_id
        )
    
    # 4. Create new Razorpay order
    client = get_razorpay_client()
    
    # Get pricing based on country (defaults to USD if not India)
    country = (request.country or "").upper()
    pricing = PRICING_CONFIG.get(country, PRICING_CONFIG["DEFAULT"])
    amount = pricing["amount"]
    currency = pricing["currency"]
    
    order_data = {
        "amount": amount,
        "currency": currency,
        "receipt": f"geo_{request.job_id[:8]}",
        "notes": {
            "job_id": request.job_id,
            "user_id": user["id"],
            "product": "CiteKit Kit",
            "country": country or "UNKNOWN"
        }
    }
    
    try:
        razorpay_order = client.order.create(data=order_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")
    
    # 5. Store order in database
    await db.create_payment_order(
        job_id=request.job_id,
        user_id=user["id"],
        razorpay_order_id=razorpay_order["id"],
        amount=amount,
        currency=currency
    )
    
    return CreateOrderResponse(
        order_id=razorpay_order["id"],
        amount=amount,
        currency=currency,
        key_id=settings.razorpay_key_id
    )


@router.post("/verify")
async def verify_payment(
    request: VerifyPaymentRequest,
    user: dict = Depends(get_current_user)
):
    """
    Verify payment signature after Razorpay checkout.
    This is the primary payment confirmation method.
    """
    settings = get_settings()
    db = get_database()
    
    # 1. Verify job ownership
    job = await db.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 2. Get order from database
    order = await db.get_payment_order_by_razorpay_id(request.razorpay_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["job_id"] != request.job_id:
        raise HTTPException(status_code=400, detail="Order/Job mismatch")
    
    # 2.1 SECURITY: Verify order belongs to the same user
    if order["user_id"] != user["id"]:
        print(f"⚠️ User {user['id']} tried to verify order belonging to {order['user_id']}")
        raise HTTPException(status_code=403, detail="Order does not belong to you")
    
    # 2.2 SECURITY: Check if order is already paid (prevent replay attacks)
    if order["status"] == "paid":
        # Already paid - return success but don't process again
        return {
            "success": True,
            "message": "Payment already verified",
            "payment_id": order.get("razorpay_payment_id"),
            "job_id": request.job_id
        }
    
    # 3. Verify signature using HMAC-SHA256
    # Per Razorpay docs: Use order_id from YOUR SERVER, not the one returned by checkout
    # This ensures the order_id hasn't been tampered with
    server_order_id = order["razorpay_order_id"]  # From our database
    
    # Signature = HMAC_SHA256(order_id + "|" + payment_id, secret)
    signature_payload = f"{server_order_id}|{request.razorpay_payment_id}"
    
    expected_signature = hmac.new(
        key=settings.razorpay_key_secret.encode('utf-8'),
        msg=signature_payload.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, request.razorpay_signature):
        # Log failed verification for security monitoring
        print(f"⚠️ Payment signature mismatch for order {server_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    
    # 4. Update payment order status (only if still in 'created' state)
    # This is idempotent - if webhook already updated it, this is a no-op
    if order["status"] != "paid":
        await db.update_payment_order_status(
            razorpay_order_id=request.razorpay_order_id,
            status="paid",
            razorpay_payment_id=request.razorpay_payment_id
        )
    
    # 5. Update job with payment ID (only if not already set)
    if not job.payment_id:
        await db.update_job(request.job_id, payment_id=request.razorpay_payment_id)
    
    print(f"✅ Payment verified: {request.razorpay_payment_id} for job {request.job_id}")
    
    # 6. Send confirmation email with download link and invoice
    try:
        from email_service import get_email_service
        
        # User email is already in the auth context from get_current_user
        user_email = user.get("email")
        
        if user_email and job.result_path:
            email_service = get_email_service()
            email_service.send_payment_confirmation(
                to_email=user_email,
                job_id=request.job_id,
                domain=job.url.replace("https://", "").replace("http://", "").split("/")[0],
                download_url=job.result_path,
                payment_id=request.razorpay_payment_id,
                amount_paise=order.get("amount", 84000),
                currency=order.get("currency", "INR"),
                geo_score=job.geo_score
            )
    except Exception as e:
        # Don't fail payment verification if email fails
        print(f"⚠️ Email notification failed (non-critical): {e}")
    
    return {
        "success": True,
        "message": "Payment verified successfully",
        "payment_id": request.razorpay_payment_id,
        "job_id": request.job_id
    }


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: Optional[str] = Header(None, alias="X-Razorpay-Event-Id")
):
    """
    Handle Razorpay webhook notifications.
    This is server-to-server and should be treated as source of truth.
    
    IMPORTANT: Must respond with 2XX within 5 seconds or Razorpay will retry.
    """
    settings = get_settings()
    db = get_database()
    
    # 0. Log incoming webhook for debugging
    print(f"📨 Webhook received - Event ID: {x_razorpay_event_id}")
    
    # 1. Get RAW body for signature verification (don't parse first!)
    body = await request.body()
    
    # 2. Verify webhook signature (REQUIRED for production)
    if settings.razorpay_webhook_secret:
        if not x_razorpay_signature:
            print("⚠️ Webhook missing signature header")
            raise HTTPException(status_code=400, detail="Missing signature header")
        
        expected_signature = hmac.new(
            key=settings.razorpay_webhook_secret.encode('utf-8'),
            msg=body,  # Use raw bytes, NOT decoded string
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_signature, x_razorpay_signature):
            print(f"⚠️ Webhook signature verification failed")
            print(f"   Expected: {expected_signature[:20]}...")
            print(f"   Received: {x_razorpay_signature[:20]}...")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
        
        print("✅ Webhook signature verified")
    else:
        print("⚠️ RAZORPAY_WEBHOOK_SECRET not configured - skipping signature check")
    
    # 3. Parse webhook payload (AFTER signature verification)
    try:
        payload = json.loads(body.decode('utf-8'))
    except json.JSONDecodeError as e:
        print(f"⚠️ Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event = payload.get("event")
    print(f"📌 Processing event: {event}")
    
    # 4. Handle payment.captured event
    if event == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        
        razorpay_payment_id = payment_entity.get("id")
        razorpay_order_id = payment_entity.get("order_id")
        amount = payment_entity.get("amount")
        
        print(f"   Payment ID: {razorpay_payment_id}")
        print(f"   Order ID: {razorpay_order_id}")
        print(f"   Amount: {amount} paise")
        
        if razorpay_order_id and razorpay_payment_id:
            # Get order from database
            order = await db.get_payment_order_by_razorpay_id(razorpay_order_id)
            
            if not order:
                print(f"⚠️ Order not found in database: {razorpay_order_id}")
                # Still return 200 to prevent Razorpay retries
                return {"status": "ok", "message": "Order not found"}
            
            if order["status"] != "paid":
                # Update order status
                await db.update_payment_order_status(
                    razorpay_order_id=razorpay_order_id,
                    status="paid",
                    razorpay_payment_id=razorpay_payment_id
                )
                
                # Update job payment ID
                await db.update_job(order["job_id"], payment_id=razorpay_payment_id)
                
                print(f"✅ Webhook: Payment captured for order {razorpay_order_id}")
            else:
                print(f"ℹ️ Order already paid, skipping update")
    
    # 5. Handle payment.failed event
    elif event == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        razorpay_order_id = payment_entity.get("order_id")
        error_reason = payment_entity.get("error_reason", "Unknown")
        
        print(f"   Order ID: {razorpay_order_id}")
        print(f"   Failure reason: {error_reason}")
        
        if razorpay_order_id:
            order = await db.get_payment_order_by_razorpay_id(razorpay_order_id)
            if order and order["status"] == "created":
                await db.update_payment_order_status(
                    razorpay_order_id=razorpay_order_id,
                    status="failed"
                )
                print(f"❌ Webhook: Payment failed for order {razorpay_order_id}")
    
    # 6. Handle order.paid event (alternative confirmation)
    elif event == "order.paid":
        order_entity = payload.get("payload", {}).get("order", {}).get("entity", {})
        razorpay_order_id = order_entity.get("id")
        
        print(f"   Order ID: {razorpay_order_id}")
        
        if razorpay_order_id:
            order = await db.get_payment_order_by_razorpay_id(razorpay_order_id)
            if order and order["status"] != "paid":
                # Get payment ID from payments array
                payments = order_entity.get("payments", {})
                if payments:
                    payment_items = list(payments.items())
                    if payment_items:
                        razorpay_payment_id = payment_items[0][0]
                        await db.update_payment_order_status(
                            razorpay_order_id=razorpay_order_id,
                            status="paid",
                            razorpay_payment_id=razorpay_payment_id
                        )
                        await db.update_job(order["job_id"], payment_id=razorpay_payment_id)
                        print(f"✅ Webhook: Order paid {razorpay_order_id}")
    
    else:
        print(f"ℹ️ Unhandled event type: {event}")
    
    # Always return 200 quickly to prevent retries
    return {"status": "ok"}


@router.get("/status/{job_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    job_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get payment status for a job.
    """
    db = get_database()
    
    # 1. Verify job exists and belongs to user
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 2. Get payment order details
    order = await db.get_payment_order_by_job_id(job_id)
    
    if not order:
        return PaymentStatusResponse(
            job_id=job_id,
            is_paid=bool(job.payment_id),
            payment_id=job.payment_id
        )
    
    return PaymentStatusResponse(
        job_id=job_id,
        is_paid=order["status"] == "paid",
        payment_id=order.get("razorpay_payment_id"),
        order_id=order.get("razorpay_order_id"),
        amount=order.get("amount"),
        currency=order.get("currency"),
        paid_at=order.get("paid_at")
    )


# ============================================
# TRIAL CODE ENDPOINTS
# ============================================

class RedeemTrialCodeRequest(BaseModel):
    code: str
    job_id: str


class RedeemTrialCodeResponse(BaseModel):
    success: bool
    message: str


@router.post("/redeem-trial-code", response_model=RedeemTrialCodeResponse)
async def redeem_trial_code(
    request: RedeemTrialCodeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Redeem a trial code to unlock a job's download.
    
    Trial codes are distributed for:
    - Early adopters / testimonials
    - Promotional campaigns
    - Influencer partnerships
    """
    from trial_codes import redeem_trial_code as redeem_code
    
    db = get_database()
    
    # 1. Verify job exists and belongs to user
    job = await db.get_job(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 2. Check if already paid
    if job.payment_id:
        return RedeemTrialCodeResponse(
            success=True,
            message="This audit is already unlocked!"
        )
    
    # 3. Attempt to redeem the code
    success, message = await redeem_code(
        db=db,
        code=request.code,
        user_id=user["id"],
        job_id=request.job_id,
        user_email=user.get("email")
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return RedeemTrialCodeResponse(
        success=True,
        message=message
    )


@router.get("/check-trial-code/{code}")
async def check_trial_code(code: str):
    """
    Check if a trial code is valid (without redeeming it).
    Public endpoint so users can verify before signing up.
    """
    from trial_codes import get_trial_code, is_code_valid
    
    db = get_database()
    
    trial_code = await get_trial_code(db, code)
    
    if not trial_code:
        return {"valid": False, "message": "Invalid code"}
    
    is_valid, reason = is_code_valid(trial_code)
    
    return {
        "valid": is_valid,
        "message": reason if not is_valid else "Code is valid!",
        "uses_remaining": max(0, trial_code.max_uses - trial_code.current_uses) if trial_code.code_type != "unlimited" else "unlimited"
    }

