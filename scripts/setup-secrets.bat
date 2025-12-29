@echo off
REM ============================================
REM Setup GCP Secrets for Cloud Run (Windows)
REM ============================================

setlocal enabledelayedexpansion

set PROJECT_ID=your-project-id

if "%PROJECT_ID%"=="your-project-id" (
    echo [ERROR] Please edit this script and set PROJECT_ID
    exit /b 1
)

echo Setting up secrets for project: %PROJECT_ID%
echo.

echo Creating secrets... (paste values when prompted)
echo.

echo Creating GEMINI_API_KEY...
gcloud secrets create GEMINI_API_KEY --project=%PROJECT_ID% 2>nul
echo Enter Gemini API Key:
set /p GEMINI_KEY=
echo %GEMINI_KEY%| gcloud secrets versions add GEMINI_API_KEY --data-file=- --project=%PROJECT_ID%

echo Creating SUPABASE_URL...
gcloud secrets create SUPABASE_URL --project=%PROJECT_ID% 2>nul
echo Enter Supabase URL:
set /p SUPABASE_URL_VAL=
echo %SUPABASE_URL_VAL%| gcloud secrets versions add SUPABASE_URL --data-file=- --project=%PROJECT_ID%

echo Creating SUPABASE_KEY...
gcloud secrets create SUPABASE_KEY --project=%PROJECT_ID% 2>nul
echo Enter Supabase Key:
set /p SUPABASE_KEY_VAL=
echo %SUPABASE_KEY_VAL%| gcloud secrets versions add SUPABASE_KEY --data-file=- --project=%PROJECT_ID%

echo Creating REDIS_URL...
gcloud secrets create REDIS_URL --project=%PROJECT_ID% 2>nul
echo Enter Redis URL:
set /p REDIS_URL_VAL=
echo %REDIS_URL_VAL%| gcloud secrets versions add REDIS_URL --data-file=- --project=%PROJECT_ID%

echo Creating RAZORPAY_KEY_ID...
gcloud secrets create RAZORPAY_KEY_ID --project=%PROJECT_ID% 2>nul
echo Enter Razorpay Key ID:
set /p RAZORPAY_ID=
echo %RAZORPAY_ID%| gcloud secrets versions add RAZORPAY_KEY_ID --data-file=- --project=%PROJECT_ID%

echo Creating RAZORPAY_KEY_SECRET...
gcloud secrets create RAZORPAY_KEY_SECRET --project=%PROJECT_ID% 2>nul
echo Enter Razorpay Key Secret:
set /p RAZORPAY_SECRET=
echo %RAZORPAY_SECRET%| gcloud secrets versions add RAZORPAY_KEY_SECRET --data-file=- --project=%PROJECT_ID%

echo Creating RAZORPAY_WEBHOOK_SECRET...
gcloud secrets create RAZORPAY_WEBHOOK_SECRET --project=%PROJECT_ID% 2>nul
echo Enter Razorpay Webhook Secret:
set /p WEBHOOK_SECRET=
echo %WEBHOOK_SECRET%| gcloud secrets versions add RAZORPAY_WEBHOOK_SECRET --data-file=- --project=%PROJECT_ID%

echo.
echo ========================================
echo  All secrets configured!
echo ========================================
echo.
echo Verify with: gcloud secrets list --project=%PROJECT_ID%

endlocal
