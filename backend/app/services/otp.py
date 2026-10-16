import logging
import secrets
from typing import Optional, Tuple
from app.core.config import settings
from app.core.redis import get_redis_client

logger = logging.getLogger("fyndo.otp")

OTP_TTL_SECONDS = 120
OTP_SEND_WINDOW_SECONDS = 600
OTP_SEND_LIMIT = 3
OTP_MAX_VERIFY_ATTEMPTS = 5


class OtpService:
    @staticmethod
    async def send_otp(phone: str, channel: str = "SMS") -> Tuple[bool, Optional[str], str]:
        """
        Generates and dispatches a 6-digit OTP to the phone number.
        Returns: (success, test_otp_if_dev, message)
        """
        if settings.ENVIRONMENT.lower() == "production" and settings.SMS_GATEWAY_PROVIDER.lower() == "mock":
            logger.error("Mock OTP provider is disabled while ENVIRONMENT=production")
            return False, None, "OTP delivery is not configured for production."

        redis = await get_redis_client()

        # Atomic fixed-window rate limit: max 3 requests per 10 minutes.
        rate_key = f"rate:otp:{phone}"
        attempts = await redis.incr(rate_key)
        if attempts == 1:
            await redis.expire(rate_key, OTP_SEND_WINDOW_SECONDS)
        if attempts > OTP_SEND_LIMIT:
            return False, None, "Too many OTP requests. Please wait 10 minutes."

        # Cryptographically secure 6-digit code (was `random.randint`).
        otp_code = f"{secrets.randbelow(1_000_000):06d}"

        # Store in Redis with a short TTL so codes cannot be brute-forced later.
        otp_key = f"otp:{phone}"
        await redis.set(otp_key, otp_code, ex=OTP_TTL_SECONDS)
        # A fresh code resets the failed-attempt counter.
        await redis.delete(f"otp_attempts:{phone}")

        # Dispatch via gateway (or log if mock)
        if settings.SMS_GATEWAY_PROVIDER.lower() == "mock":
            logger.info(f"[DEV MOCK OTP] Sent code '{otp_code}' to phone '{phone}' via {channel}")
            return True, otp_code, "OTP sent successfully (Dev Mock Mode)"
        else:
            # Twilio / Gupshup dispatch logic
            logger.info(f"Dispatched production OTP to {phone}")
            return True, None, "OTP sent successfully"

    @staticmethod
    async def verify_otp(phone: str, submitted_otp: str) -> bool:
        """
        Verifies the submitted OTP against Redis using a constant-time compare.
        Deletes the OTP immediately upon success to prevent replay, and locks
        the code out after too many failed attempts.
        """
        redis = await get_redis_client()
        otp_key = f"otp:{phone}"
        attempt_key = f"otp_attempts:{phone}"

        failed = await redis.get(attempt_key)
        if failed and int(failed) >= OTP_MAX_VERIFY_ATTEMPTS:
            await redis.delete(otp_key)
            logger.warning(f"OTP verification locked out for {phone} after repeated failures.")
            return False

        stored_otp = await redis.get(otp_key)
        if not stored_otp:
            return False
        if isinstance(stored_otp, bytes):
            stored_otp = stored_otp.decode()

        if secrets.compare_digest(stored_otp.strip(), submitted_otp.strip()):
            # Delete to prevent replay.
            await redis.delete(otp_key)
            await redis.delete(attempt_key)
            return True

        attempts = await redis.incr(attempt_key)
        if attempts == 1:
            await redis.expire(attempt_key, OTP_SEND_WINDOW_SECONDS)
        return False

