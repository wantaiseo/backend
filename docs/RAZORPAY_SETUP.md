# Razorpay Payment Gateway Integration - Setup Guide

## ✅ Implementation Complete

The Razorpay payment gateway has been fully integrated into your CiteKit tool. Here's what was added:

### Backend Changes
- **`payments.py`** - New payment module with Razorpay SDK integration
- **`config.py`** - Added Razorpay configuration settings
- **`database.py`** - Added payment_orders table methods
- **`main.py`** - Included payments router
- **`requirements.txt`** - Added `razorpay>=1.4.1`
- **`payment_orders_setup.sql`** - Supabase migration script

### Frontend Changes
- **`PaymentModal.jsx`** - Complete rewrite with Razorpay checkout
- **`api.js`** - Added `createPaymentOrder()` and `verifyPayment()` functions
- **`Compile.jsx`** - Updated to use new payment flow

---

## 🔧 Setup Steps (Required)

### Step 1: Run Supabase Migration

Go to your Supabase Dashboard → SQL Editor and run the contents of:
```
backend/payment_orders_setup.sql
```

This creates the `payment_orders` table with proper RLS policies.

### Step 2: Add Razorpay Credentials to Backend `.env`

```env
# Razorpay Payment Gateway
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxx

# Pricing (₹420 ≈ $5)
PAYMENT_AMOUNT_PAISE=42000
PAYMENT_CURRENCY=INR
```

**Get your keys from:** https://dashboard.razorpay.com/app/keys

### Step 3: Add Razorpay Key to Frontend `.env`

```env
VITE_RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
```

### Step 4: Restart Services

```bash
# Stop existing backend
# Then restart
cd backend
..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (if not running)
cd frontend
npm run dev
```

---

## 🧪 Testing the Payment Flow

### Test Card Details (Razorpay Test Mode)
- **Card Number:** `4111 1111 1111 1111`
- **Expiry:** Any future date (e.g., `12/25`)
- **CVV:** Any 3 digits (e.g., `123`)
- **Name:** Any name
- **OTP (if asked):** Use the test OTP flow

### Test Flow
1. Run a compilation job
2. Wait for it to complete
3. Click "Unlock Your Kit" button
4. Complete payment in Razorpay modal
5. Download should be enabled after successful payment

---

## 📊 API Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/payment/create-order` | POST | Create Razorpay order |
| `/payment/verify` | POST | Verify payment signature |
| `/payment/webhook` | POST | Handle Razorpay webhooks |
| `/payment/status/{job_id}` | GET | Check payment status |

---

## 🔒 Security Features

1. **HMAC-SHA256 Signature Verification** - All payments verified server-side
2. **Webhook Validation** - Backup confirmation via signed webhooks
3. **Idempotent Orders** - Duplicate requests return existing order
4. **User Authorization** - Only job owner can pay for their job
5. **Amount Control** - Backend controls price, not frontend

---

## 🌍 Configuring for International Payments

To charge $5 USD instead of ₹420 INR:

```env
# In backend .env
PAYMENT_AMOUNT_PAISE=500  # $5 = 500 cents
PAYMENT_CURRENCY=USD
```

Note: You'll need to enable international payments in your Razorpay dashboard.

---

## 🚀 Production Webhook Setup

1. Go to Razorpay Dashboard → Settings → Webhooks
2. Add new webhook with URL: `https://your-api-domain.com/payment/webhook`
3. Select events: `payment.captured`, `payment.failed`
4. Copy the webhook secret to your `.env`:
   ```
   RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
   ```

---

## ❓ Troubleshooting

### "Razorpay credentials not configured"
- Check that `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are in your backend `.env`

### "Failed to load Razorpay"
- Check network connectivity
- Ensure `VITE_RAZORPAY_KEY_ID` is in frontend `.env`

### Payment shows in Razorpay but not updating locally
- Check webhook configuration
- Verify the `/payment/verify` call succeeds

### Database errors
- Ensure you ran the `payment_orders_setup.sql` migration
- Check RLS policies are enabled

---

## 📁 Files Changed

```
backend/
├── payments.py              [NEW] Razorpay integration module
├── payment_orders_setup.sql [NEW] Supabase migration
├── config.py               [MODIFIED] Added Razorpay config
├── database.py             [MODIFIED] Added payment methods
├── main.py                 [MODIFIED] Added payments router
├── requirements.txt        [MODIFIED] Added razorpay
└── .env.example           [MODIFIED] Added Razorpay vars

frontend/
├── src/
│   ├── components/
│   │   └── PaymentModal.jsx [REWRITTEN] Real Razorpay checkout
│   ├── lib/
│   │   └── api.js          [MODIFIED] Added payment functions
│   └── pages/
│       └── Compile.jsx     [MODIFIED] Updated payment flow
└── .env.example           [MODIFIED] Added Razorpay key
```
