from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    coupons,
    health,
    media,
    merchants,
    redemptions,
    reels,
    admin,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(redemptions.router, tags=["In-Store POS Redemptions"])
api_router.include_router(merchants.router, tags=["Merchants"])
api_router.include_router(reels.router, tags=["Reels & Feed"])
api_router.include_router(coupons.router, tags=["Coupons & Wallet"])
api_router.include_router(media.router, tags=["Media Uploads"])
api_router.include_router(admin.router, tags=["Admin Moderation"])
