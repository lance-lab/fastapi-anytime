import base64
import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


security = HTTPBasic(auto_error=False)
credentials_cache: dict[str, str] = {}


def load_credentials_cache() -> None:
    from app.database import list_credentials

    credentials_cache.clear()
    credentials_cache.update(list_credentials())


def require_basic_auth(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> str:
    if (
        request.method == "GET"
        and request.url.path in {"/api/admin/status", "/api/healthz"}
    ):
        return "__public__"

    if (
        not credentials_cache
        and request.method == "POST"
        and request.url.path == "/api/admin/credentials"
    ):
        return "__bootstrap__"

    if credentials is None:
        raise_unauthorized()

    password_hash = credentials_cache.get(credentials.username)
    if password_hash and verify_password(credentials.password, password_hash):
        return credentials.username

    # Keep username comparison timing less informative for unknown users.
    for cached_username, cached_password_hash in credentials_cache.items():
        if secrets.compare_digest(credentials.username, cached_username):
            verify_password(credentials.password, cached_password_hash)
            break

    raise_unauthorized()


def raise_unauthorized() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
        headers={"WWW-Authenticate": "Basic"},
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 210_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_digest = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${iterations}${encoded_salt}${encoded_digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_digest = password_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False

        salt = base64.b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.b64decode(encoded_digest.encode("ascii"))
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
    except (ValueError, TypeError):
        return False

    return secrets.compare_digest(actual_digest, expected_digest)
