# API Reference

Complete API documentation for CiteKit.

## Base URL

- **Local**: `http://localhost:8000`
- **Production**: `https://your-api-url.run.app`

## Authentication

All protected endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <supabase_access_token>
```

---

## Endpoints

### Health Check

#### GET /health
Full health check with dependency status.

**Response:**
```json
{
  "status": "healthy",
  "service": "geo-compiler",
  "version": "1.0.0",
  "uptime_seconds": 3600.5,
  "dependencies": {
    "celery": {"status": "healthy", "workers": 2},
    "database": {"status": "healthy"}
  }
}
```

#### GET /health/live
Simple liveness probe.

**Response:**
```json
{"status": "alive"}
```

#### GET /health/ready
Readiness probe (checks database).

**Response:**
```json
{"status": "ready"}
```

---

### Authentication

#### GET /auth/google
Redirect to Google OAuth.

**Query Parameters:**
- `redirect_url` (optional): URL to redirect after login

#### GET /auth/callback
OAuth callback handler. Redirects to frontend with tokens.

#### GET /auth/me
Get current user info.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "avatar": "https://...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /auth/logout
Logout current user.

---

### Compilation

#### POST /compile
Start a new compilation job.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "url": "https://example.com",
  "crawl_depth": "auto",
  "include_subdomains": false,
  "competitors": [],
  "payment_id": null
}
```

**Parameters:**
- `url` (required): Website URL to compile
- `crawl_depth`: "shallow" (20 pages), "auto" (50), "deep" (100)
- `include_subdomains`: Include subdomains in crawl
- `competitors`: List of competitor URLs for benchmarking
- `payment_id`: Payment ID if pre-paid

**Response:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Compilation job started..."
}
```

#### GET /status/{job_id}
Get job status and progress.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "synthesizing",
  "progress": 65,
  "total_pages": 42,
  "url": "https://example.com",
  "geo_score": null,
  "result_path": null,
  "error": null,
  "is_paid": false,
  "logs": [
    "🚀 Let's make example.com AI-ready!",
    "🔍 Mapping your digital footprint...",
    "📊 Discovered 42 pages worth of knowledge"
  ]
}
```

**Status Values:**
- `pending` - Job queued
- `discovering` - Finding pages
- `extracting` - Extracting content
- `classifying` - AI classification
- `synthesizing` - Generating output
- `packaging` - Creating ZIP
- `completed` - Done
- `failed` - Error occurred
- `cancelled` - User cancelled

#### GET /preview/{job_id}
Get preview of compilation results.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "status": "completed",
  "audit": {
    "score": {
      "total": 72,
      "grade": "B",
      "breakdown": {
        "crawler_access": 18,
        "structured_data": 15,
        "content_signals": 22,
        "technical": 17
      }
    },
    "issues": [...]
  },
  "json": {...},
  "markdown": "# LLM.txt content...",
  "facts": {...}
}
```

#### GET /download/{job_id}
Download compiled ZIP package.

**Headers:** `Authorization: Bearer <token>`

**Requirements:**
- Job must be completed
- User must own the job
- Payment must be verified

**Response:** ZIP file or redirect to storage URL

#### POST /cancel/{job_id}
Cancel a running job.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "status": "cancelled",
  "message": "Job cancellation initiated"
}
```

#### GET /jobs
List user's compilation jobs.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `limit` (default: 10): Max jobs to return

**Response:**
```json
[
  {
    "job_id": "uuid",
    "url": "https://example.com",
    "status": "completed",
    "progress": 100,
    "geo_score": 72,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### Payments

#### POST /payments/create-order
Create Razorpay payment order.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "job_id": "uuid"
}
```

**Response:**
```json
{
  "order_id": "order_xxx",
  "amount": 42000,
  "currency": "INR",
  "key_id": "rzp_live_xxx"
}
```

#### POST /payments/verify
Verify payment after completion.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "razorpay_order_id": "order_xxx",
  "razorpay_payment_id": "pay_xxx",
  "razorpay_signature": "xxx"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Payment verified",
  "job_id": "uuid"
}
```

#### POST /payments/webhook
Razorpay webhook handler.

**Headers:** `X-Razorpay-Signature: <signature>`

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

### HTTP Status Codes
- `400` - Bad Request
- `401` - Unauthorized
- `402` - Payment Required
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

---

## Rate Limits

- **Default**: 60 requests/minute, 1000 requests/hour
- Rate limit headers included in response:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
