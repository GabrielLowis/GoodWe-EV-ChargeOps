"""PBKDF2 e JWT da Frente 2, adaptados ao User canônico da Frente 3."""
import datetime
import hashlib
import hmac
import os
import secrets
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from backend.api.database import get_db
from backend.db.models import User

ITERATIONS = 200_000
bearer = HTTPBearer(auto_error=False)


def secret():
    value = os.getenv("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("JWT_SECRET precisa ter pelo menos 32 caracteres; configure o .env")
    return value


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        algorithm, iterations, salt, digest = (stored or "").split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    now = datetime.datetime.now(datetime.UTC)
    return jwt.encode({"sub": str(user.id), "iat": now, "exp": now + datetime.timedelta(hours=8)},
                      secret(), algorithm="HS256")


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(401, "Token ausente")
    try:
        payload = jwt.decode(creds.credentials, secret(), algorithms=["HS256"],
                             options={"require": ["sub", "exp"]})
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Token inválido ou expirado")
    if not user or not user.active:
        raise HTTPException(401, "Usuário indisponível")
    return user


def require_manager(user: User = Depends(get_current_user)) -> User:
    if user.role != "manager":
        raise HTTPException(403, "Acesso restrito ao síndico")
    return user
