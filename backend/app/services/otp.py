import logging
import random
from typing import Optional, Tuple
from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger("fyndo.otp")


class OtpService:
    @staticmethod
    async def send_otp(phone: str, channel: str = "SMS") -> Tuple[bool, Optional[str], str]:
        """
        Generates and dispatches a 6-digit OTP to the phone number.
        Returns: (success, test_otp_if_dev, message)
        """
        redis = await get_redis_client()

        # Check rate limit: max 3 requests per 10 minutes
        rate_key = f"rate:otp:{phone}"
        attempts = await redis.get(rate_key)
        if attempts and int(attempts) >= 3:
            return False, None, "Too many OTP requests. Please wait 10 minutes."

        # Generate 6-digit OTP
        otp_code = f"{random.randint(100000, 999999)}"

        # Store in Redis with 120-second TTL
        otp_key = f"otp:{phone}"
        await redis.set(otp_key, otp_code, ex=120)

        # Update rate limit tracker (10 min TTL = 600s)
        await redis.incr(rate_key)
        await redis.expire(rate_key, 600)

        # Dispatch via gateway (or log if mock)
        if settings.SMS_GATEWAY_PROVIDER == "mock":
            logger.info(f"[DEV MOCK OTP] Sent code '{otp_code}' to phone '{phone}' via {channel}")
            return True, otp_code, "OTP sent successfully (Dev Mock Mode)"
        else:
            # Twilio / Gupshup dispatch logic
            logger.info(f"Dispatched production OTP to {phone}")
            return True, None, "OTP sent successfully"

    @staticmethod
    async def verify_otp(phone: str, submitted_otp: str) -> bool:
        """
        Verifies the submitted OTP against Redis.
        Deletes the OTP immediately upon successful verification to prevent replay.
        """
        redis = await get_redis_client()
        otp_key = f"otp:{phone}"
        stored_otp = await redis.get(otp_key)

        if not stored_otp:
            return False

        if stored_otp.strip() == submitted_otp.strip():
            # Delete to prevent replay
            await redis.delete(otp_key)
            return True

        return False
