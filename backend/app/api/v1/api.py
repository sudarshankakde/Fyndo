from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    coupons,
    health,
    media,
    merchant_engagement,
    merchants,
    reel_publishing,
    notifications,
    redemptions,
    reel_engagement,
    reels,
    admin,
    admin_settings,
    ws,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(redemptions.router, tags=["In-Store POS Redemptions"])
api_router.include_router(merchant_engagement.router, tags=["Merchants"])
api_router.include_router(merchants.router, tags=["Merchants"])
api_router.include_router(reel_publishing.router, tags=["Reels & Feed"])
api_router.include_router(reels.router, tags=["Reels & Feed"])
api_router.include_router(reel_engagement.router, tags=["Reels & Feed"])
api_router.include_router(coupons.router, tags=["Coupons & Wallet"])
api_router.include_router(notifications.router, tags=["Notifications"])
api_router.include_router(media.router, tags=["Media Uploads"])
api_router.include_router(admin.router, tags=["Admin Moderation"])
api_router.include_router(admin_settings.router, tags=["Admin Moderation"])
api_router.include_router(ws.router, tags=["Real-time"])
