import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.database import list_credentials, verify_password


security = HTTPBasic(auto_error=False)
credentials_cache: dict[str, str] = {}


def load_credentials_cache() -> None:
    credentials_cache.clear()
    credentials_cache.update(list_credentials())


def require_basic_auth(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> str:
    if (
        not credentials_cache
        and request.method == "POST"
        and request.url.path == "/credentials"
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
