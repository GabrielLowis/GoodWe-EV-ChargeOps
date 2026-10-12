import os
import hmac
import hashlib
import secrets
import datetime
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import User, ProfileUser

ITERATIONS = 200_000
JWT_ALGORITHM = "HS256"
TOKEN_HOURS = 8


def _secret() -> str:
    # Em producao a variavel JWT_SECRET e obrigatoria. O valor padrao e so para desenvolvimento.
    return os.getenv("JWT_SECRET", "dev-only-secret-change-me-please-0123456789")


def hash_password(password: str) -> str:
    """Guarda o hash (PBKDF2 + salt), nunca a senha."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    except ValueError:
        return False
    return hmac.compare_digest(candidate, digest)


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "profile": user.profile.value,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Token ausente")
    try:
        payload = jwt.decode(creds.credentials, _secret(), algorithms=[JWT_ALGORITHM])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario nao encontrado")
    return user


def require_manager(user: User = Depends(get_current_user)) -> User:
    if user.profile != ProfileUser.Gestor:
        raise HTTPException(status_code=403, detail="Acesso restrito ao gestor")
    return user
