# backend/auth_service.py
import bcrypt
from backend.db_mysql import fetch_one, execute

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False

def register_user(full_name: str, email: str, phone: str, password: str):
    email = (email or "").strip().lower()

    existing = fetch_one("SELECT id FROM users WHERE email=%s", (email,))
    if existing:
        return False, "Email already registered. Please login."

    pw_hash = hash_password(password)
    execute(
        "INSERT INTO users(full_name,email,phone,password_hash) VALUES(%s,%s,%s,%s)",
        (full_name.strip(), email, phone.strip(), pw_hash),
    )
    return True, "Registration successful! Please login."

def login_user(email: str, password: str):
    email = (email or "").strip().lower()
    user = fetch_one("SELECT * FROM users WHERE email=%s", (email,))
    if not user:
        return False, "User not found. Please register.", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid password.", None

    return True, "Login successful.", user
