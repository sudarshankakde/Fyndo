import base64
import json
import time
import uuid
from typing import Any, Dict, Optional, Tuple
import pyotp


class TotpService:
    @staticmethod
    def generate_secret() -> str:
        """Generates a secure Base32 secret for TOTP computation."""
        return pyotp.random_base32()

    @staticmethod
    def generate_dynamic_qr_payload(
        user_coupon_id: uuid.UUID,
        secret: str,
        user_id: uuid.UUID
    ) -> Tuple[str, str, int, str]:
        """
        Generates:
        - qr_payload: Base64URL-encoded token packet
        - totp_token: 6-digit dynamic token
        - seconds_remaining: Remaining time in current 60s window
        - backup_offline_pin: 4-digit slice for emergency checkout
        """
        totp = pyotp.TOTP(secret, interval=60)
        current_token = totp.now()

        # Calculate remaining seconds in current 60s time step
        current_epoch = int(time.time())
        seconds_remaining = 60 - (current_epoch % 60)

        # Generate 4-digit backup PIN from token
        backup_offline_pin = current_token[:4]

        packet: Dict[str, Any] = {
            "claim_id": str(user_coupon_id),
            "totp": current_token,
            "uid": str(user_id),
            "ts": current_epoch
        }

        # Encode as URL-safe base64 string
        encoded_payload = base64.urlsafe_b64encode(
            json.dumps(packet).encode("utf-8")
        ).decode("utf-8")

        return encoded_payload, current_token, seconds_remaining, backup_offline_pin

    @staticmethod
    def parse_qr_payload(qr_payload: str) -> Optional[Dict[str, Any]]:
        """Parses and validates the Base64 dynamic QR payload."""
        try:
            decoded = base64.urlsafe_b64decode(qr_payload.encode("utf-8")).decode("utf-8")
            return json.loads(decoded)
        except Exception:
            return None

    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        """
        Verifies the TOTP token strictly within its active 60s interval.
        valid_window=0 ensures expired tokens from past windows are strictly rejected.
        """
        totp = pyotp.TOTP(secret, interval=60)
        return totp.verify(token, valid_window=0)

    @staticmethod
    def verify_backup_pin(secret: str, pin: str) -> bool:
        totp = pyotp.TOTP(secret, interval=60)
        for offset in (-1, 0, 1):
            token = totp.at(int(time.time()) + offset * 60)
            if token[:4] == pin:
                return True
        return False
