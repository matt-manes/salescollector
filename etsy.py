import os
from datetime import datetime, timedelta
from typing import cast

from etsy_python.v3.auth.OAuth import EtsyOAuth  # type: ignore
from etsy_python.v3.resources.Session import EtsyClient  # type: ignore

import exceptions
from db import SCDatabased


def get_etsy_oauth() -> EtsyOAuth:
    key: str | None = os.getenv("sc_keystring")
    redirect: str | None = os.getenv("sc_oauth-redirect")
    if key is None or redirect is None:
        raise exceptions.MissingEnvException("Missing sc_* keys in .env")
    return EtsyOAuth(
        keystring=key,
        redirect_uri=redirect,
        scopes=["transactions_r", "shops_r"],
    )


def get_etsy_client(token_data: dict[str, str]) -> EtsyClient:
    key: str | None = os.getenv("sc_keystring")
    if not key:
        raise exceptions.MissingEnvException("Missing sc_* keys in .env")
    return EtsyClient(
        keystring=key,
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expiry=datetime.now() + timedelta(seconds=int(token_data["expires_in"])),
    )


def get_authenticated_client(code: str, state: str) -> EtsyClient:
    oauth: EtsyOAuth = get_etsy_oauth()
    with SCDatabased() as db:
        session: dict[str, str] = db.get_oauth(state)
    oauth.state = session["state"]
    oauth.code_verifier = session["code_verifier"]
    oauth.set_authorisation_code(code=code, state=state)
    token_data: dict[str, str] = cast(dict[str, str], oauth.get_access_token())
    return get_etsy_client(token_data)


def get_state() -> str:
    with SCDatabased() as db:
        return db.get_state()


def state_exists(state: str) -> bool:
    with SCDatabased() as db:
        return db.state_exists(state)


def save_oauth(state: str, code_verifier: str):
    with SCDatabased() as db:
        db.register_oauth(state, code_verifier)
