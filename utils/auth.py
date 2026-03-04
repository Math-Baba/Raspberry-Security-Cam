import hashlib
import hmac

def hash_pin(pin_4: str, salt: str = "pi-surveillance-salt-v1") -> str:
    # PIN 4 chiffres -> hash stable (simple). Tu peux renforcer plus tard (PBKDF2/bcrypt).
    payload = (salt + ":" + pin_4).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def verify_pin(pin_4: str, stored_hash: str) -> bool:
    computed = hash_pin(pin_4)
    return hmac.compare_digest(computed, stored_hash)

def is_valid_pin(pin_4: str) -> bool:
    return isinstance(pin_4, str) and len(pin_4) == 4 and pin_4.isdigit()