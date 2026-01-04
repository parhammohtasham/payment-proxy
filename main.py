"""
Zibal Payment Callback Proxy
A microservice that receives Zibal payment callbacks and forwards them to the ticketing API
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi import status as http_status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
import httpx
import logging
from typing import Optional
from datetime import datetime
import hashlib
import hmac
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Zibal Payment Gateway Proxy",
    description="""
    # Zibal Payment Gateway Proxy Service
    
    A FastAPI microservice that acts as a secure proxy between Zibal payment gateway and your main application API.
    
    ## Key Features
    
    - **Receives callbacks from Zibal**: Handles payment callbacks after transaction completion
    - **Verifies payments with Zibal**: Validates transactions using Zibal's verification API
    - **High security**: Uses HMAC-SHA256 signatures for webhook authentication
    - **Comprehensive logging**: Logs all payment processing steps for debugging
    - **Automatic redirects**: Redirects users to appropriate success/failure pages
    
    ## Payment Flow
    
    1. User initiates payment on your main application
    2. Zibal processes the payment
    3. Zibal sends callback to this proxy service
    4. Proxy verifies payment with Zibal API
    5. Proxy forwards verified result to your main API via webhook
    6. User is redirected to success or failure page
    
    ## Security
    
    All requests sent to your main API are signed with HMAC-SHA256 for authentication.
    """,
    version="1.0.0",
    docs_url=None,  # Disable default Swagger
    redoc_url=None  # Disable ReDoc
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # در production محدود کنید
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Scalar API Documentation
@app.get("/docs", include_in_schema=False)
async def scalar_html():
    """API documentation with Scalar interface"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )


def create_signature(data: dict) -> str:
    """Create HMAC signature for webhook security"""
    message = f"{data['trackId']}:{data['success']}:{data['status']}"
    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


@app.get("/")
async def root():
    """
    Service home page
    
    This endpoint displays general service information and its status.
    """
    return {
        "service": "Zibal Payment Proxy",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "callback": "/api/zibal/callback",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """
    Service health check
    
    This endpoint is used by monitoring systems to check service status.
    
    Returns:
        dict: Service health status
    """
    return {"status": "healthy"}


@app.get("/redirect/{trackId}")
async def redirect_to_zibal(trackId: str):
    """
    Redirect user to Zibal payment gateway
    
    This endpoint solves the "unauthorized domain" issue with Zibal.
    
    ## Problem:
    Zibal checks the Referrer header. If a user is redirected directly from your frontend
    to `gateway.zibal.ir`, Zibal may reject it with "unauthorized domain" error.
    
    ## Solution:
    User is first redirected to this endpoint, then this endpoint redirects to Zibal.
    This way, the Referrer for Zibal becomes your registered domain which is in the
    allowed domains list.
    
    ## Flow:
    1. Frontend: User clicks "Pay"
    2. Browser: Redirects to your registered domain (this proxy)
    3. This endpoint: Redirects to `gateway.zibal.ir/start/{trackId}`
    4. Zibal: Referrer = your registered domain ✅
    
    Args:
        trackId: Transaction ID from Zibal
        
    Returns:
        RedirectResponse: 303 redirect to Zibal gateway
    """
    zibal_gateway_url = f"{settings.ZIBAL_PAYMENT_URL}{trackId}"
    
    logger.info("="*100)
    logger.info("🔀 REDIRECT REQUEST RECEIVED")
    logger.info(f"📋 TrackId: {trackId}")
    logger.info(f"🎯 Redirecting to: {zibal_gateway_url}")
    logger.info("="*100)
    
    return RedirectResponse(
        url=zibal_gateway_url,
        status_code=http_status.HTTP_303_SEE_OTHER
    )


@app.get("/api/zibal/callback")
async def zibal_callback(
    trackId: str,
    success: int,
    status: int,
    orderId: Optional[str] = None
):
    """
    Receive callback from Zibal payment gateway
    
    This endpoint is called by Zibal payment gateway after payment completion.
    
    ## Workflow:
    
    1. **Receive callback**: Gets parameters sent by Zibal
    2. **Verify payment**: Sends verification request to Zibal API
    3. **Forward to main API**: Forwards verified result to your main API with security signature
    4. **Redirect user**: Redirects user to success or failure page
    
    ## Parameters:
    
    - **trackId**: Unique transaction ID in Zibal
    - **success**: Payment success status (1 = success, 0 = failed)
    - **status**: Transaction status code
    - **orderId**: Order ID (optional)
    
    ## Response:
    
    303 redirect to success or failure page in your frontend
    
    ## Security Notes:
    
    - All requests are signed with HMAC-SHA256
    - Double verification: both from Zibal and in your main API
    - Complete logging of all steps for monitoring and debugging
    """
    logger.info("="*100)
    logger.info("🔔 ZIBAL CALLBACK RECEIVED AT PROXY")
    logger.info(f"📋 Parameters:")
    logger.info(f"   - trackId: {trackId}")
    logger.info(f"   - success: {success}")
    logger.info(f"   - status: {status}")
    logger.info(f"   - orderId: {orderId}")
    logger.info("="*100)
    
    try:
        # Step 1: Verify payment with Zibal
        logger.info("🔄 Verifying payment with Zibal...")
        
        async with httpx.AsyncClient() as client:
            verify_data = {
                "merchant": settings.ZIBAL_MERCHANT_ID,
                "trackId": int(trackId)
            }
            
            logger.info(f"📤 Sending verify request: {verify_data}")
            
            verify_response = await client.post(
                settings.ZIBAL_VERIFY_URL,
                json=verify_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                timeout=15.0
            )
            
            verify_result = verify_response.json()
            logger.info(f"📥 Zibal verify response: {verify_result}")
            
            # Step 2: Forward to ticketing API
            logger.info("📨 Forwarding to ticketing API...")
            
            # Prepare webhook data
            webhook_data = {
                "trackId": trackId,
                "success": success,
                "status": status,
                "orderId": orderId,
                "verifyResult": verify_result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add signature for security
            signature = create_signature(webhook_data)
            
            webhook_response = await client.post(
                f"{settings.TICKETING_API_URL}/api/v1/payments/zibal-webhook",
                json=webhook_data,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature
                },
                timeout=15.0
            )
            
            webhook_result = webhook_response.json()
            logger.info(f"✅ Ticketing API response: {webhook_result}")
            
            # Step 3: Redirect user
            if verify_result.get("result") == 100 and webhook_result.get("success"):
                # Payment successful
                logger.info("🎉 Payment successful - redirecting to success page")
                redirect_url = (
                    f"{settings.TICKETING_FRONTEND_URL}/payment/success"
                    f"?ref_id={webhook_result.get('ref_number')}"
                    f"&reservation_id={webhook_result.get('reservation_id')}"
                )
            else:
                # Payment failed
                logger.info("❌ Payment failed - redirecting to failure page")
                error_msg = verify_result.get("message", "Unknown error")
                redirect_url = (
                    f"{settings.TICKETING_FRONTEND_URL}/payment/failed"
                    f"?error={error_msg}"
                    f"&trackId={trackId}"
                )
            
            logger.info(f"🔀 Redirecting to: {redirect_url}")
            logger.info("="*100)
            
            return RedirectResponse(
                url=redirect_url,
                status_code=http_status.HTTP_303_SEE_OTHER
            )
            
    except httpx.RequestError as e:
        logger.error(f"❌ Network error: {str(e)}")
        return RedirectResponse(
            url=f"{settings.TICKETING_FRONTEND_URL}/payment/failed?error=Connection+error",
            status_code=http_status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return RedirectResponse(
            url=f"{settings.TICKETING_FRONTEND_URL}/payment/failed?error=System+error",
            status_code=http_status.HTTP_303_SEE_OTHER
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
