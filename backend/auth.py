import os
import hmac
import hashlib
import base64
import time
from typing import Optional

def get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "cloudshare-insecure-dev-secret-key-change-me")

def generate_recipient_token(file_id: str, recipient_email: str) -> str:
    secret = get_secret_key().encode("utf-8")
    ts = str(int(time.time()))
    payload = f"{recipient_email}:{file_id}:{ts}"
    signature = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    token_str = f"{payload}:{signature}"
    return base64.urlsafe_b64encode(token_str.encode("utf-8")).decode("utf-8")

def verify_recipient_token(token: str, file_id: str) -> Optional[str]:
    secret = get_secret_key().encode("utf-8")
    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        parts = raw.split(":")
        if len(parts) != 4:
            return None
        email, token_file_id, ts, signature = parts
        if token_file_id != file_id:
            return None
        payload = f"{email}:{token_file_id}:{ts}"
        expected_sig = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_sig):
            return email
        return None
    except Exception:
        return None
