import os
from datetime import datetime, timedelta
from functools import cached_property
from typing import Any, cast

import loggi

# type ignores b/c etsy_python has no "typed" stub file
from etsy_python.v3.auth.OAuth import EtsyOAuth  # type: ignore
from etsy_python.v3.exceptions import RequestException  # type: ignore
from etsy_python.v3.resources import ReceiptResource  # type: ignore
from etsy_python.v3.resources import Response, UserResource  # type: ignore
from etsy_python.v3.resources.Session import EtsyClient  # type: ignore
from pathier import Pathier
from typing_extensions import Self

import exceptions
from db import SCDatabased

root = Pathier(__file__).parent


def get_logger() -> loggi.Logger:
    return loggi.getLogger("etsy", root / "logs")


def log_and_raise_api_error(message: str) -> exceptions.APIException:
    get_logger().error(message)
    raise exceptions.APIException(message)


class OAuthProvider:
    @staticmethod
    def get_new_oauth() -> EtsyOAuth:
        key: str | None = os.getenv("sc_keystring")
        redirect: str | None = os.getenv("sc_oauth-redirect")
        if key is None or redirect is None:
            raise exceptions.MissingEnvException("Missing sc_* keys in .env")
        return EtsyOAuth(
            keystring=key,
            redirect_uri=redirect,
            scopes=["transactions_r", "shops_r"],
        )

    @staticmethod
    def get_auth_url() -> str:
        oauth: EtsyOAuth = OAuthProvider.get_new_oauth()
        auth_url: str = oauth.get_auth_code()[0]
        OAuthProvider.save_state(oauth)
        return auth_url

    @staticmethod
    def state_exists(state: str) -> bool:
        with SCDatabased() as db:
            return db.state_exists(state)

    @staticmethod
    def save_state(oauth_instance: EtsyOAuth) -> None:
        with SCDatabased() as db:
            db.register_oauth(oauth_instance.state, oauth_instance.code_verifier)

    @staticmethod
    def get_saved_oauth(state: str) -> EtsyOAuth:
        oauth: EtsyOAuth = OAuthProvider.get_new_oauth()
        with SCDatabased() as db:
            session: dict[str, str] = db.get_oauth(state)
        oauth.state = session["state"]
        oauth.code_verifier = session["code_verifier"]
        return oauth


class AuthenticatedClient:
    def __init__(self, token_data: dict[str, str]) -> None:
        key: str | None = os.getenv("sc_keystring")
        self._shop_id: str | None = None
        if not key:
            raise exceptions.MissingEnvException("Missing sc_* keys in .env")
        self.client: EtsyClient = EtsyClient(
            keystring=key,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expiry=datetime.now() + timedelta(seconds=int(token_data["expires_in"])),
        )

    @classmethod
    def from_redirect(cls, code: str, state: str) -> Self:
        oauth: EtsyOAuth = OAuthProvider.get_saved_oauth(state)
        oauth.set_authorisation_code(code=code, state=state)
        token_data: dict[str, str] = cast(dict[str, str], oauth.get_access_token())
        return cls(token_data)

    @cached_property
    def shop_id(self) -> str:
        user: UserResource = UserResource(self.client)
        try:
            # etsy_python mistyped resource objects to either return
            # the resource or a `RequestException`, but the code
            # for `Session` actually raises the exception or
            # returns the response smh
            response: Response = cast(Response, user.get_me())
        except RequestException as e:
            log_and_raise_api_error(f"Getting shop id failed: {e}")
        # type ignore b/c etsy_python mistyped `message` field as `str`
        # even though it's `dict[str, Any]` for any successful request that returns data
        return response.message["shop_id"]  # type: ignore

    def get_sales_data(self) -> list[dict[str, Any]]:
        receipts: ReceiptResource = ReceiptResource(self.client)
        offset: int = 0
        limit: int = 100
        total: int = -1
        results: list[dict[str, Any]] = []
        # don't know total until we get the first response
        while total == -1 or len(results) < total:
            try:
                response: Response = cast(
                    Response,
                    receipts.get_shop_receipts(
                        int(self.shop_id), limit=limit, offset=offset
                    ),
                )
            except RequestException as e:
                message = f"Failure to get receipts for shop id '{self.shop_id}'\n{offset=}\n{total=}\n{len(results)=}\n{e}"
                log_and_raise_api_error(message)
            else:
                # etsy_python mistyped `message` field as `str`
                # even though it's `dict[str, Any]` for any successful request that returns data
                data: dict[str, Any] = cast(dict[str, Any], response.message)
                total = data["count"]
                results.extend(data["results"])
                offset += limit
        return results

    def prep_transaction_data(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        transactions: list[dict[str, Any]] = []
        for receipt in data:
            if receipt["seller_user_id"] == self.shop_id:
                for transaction in receipt["transactions"]:
                    prepped: dict[str, Any] = {}
                    prepped["receipt_id"] = receipt["receipt_id"]
                    prepped["sale_date"] = datetime.fromtimestamp(
                        receipt["created_timestamp"]
                    )
                    prepped["transaction_id"] = transaction["transaction_id"]
                    prepped["title"] = transaction["title"]
                    prepped["quantity"] = transaction["quantity"]
                    prepped["listing_id"] = transaction["listing_id"]
                    prepped["product_id"] = transaction["product_id"]
                    prepped["price"] = float(transaction["price"]["amount"]) / (
                        1.0
                        if transaction["price"]["divisor"] == 0
                        else transaction["price"]["divisor"]
                    )
                    transactions.append(prepped)
        return transactions

    def pull_data(self) -> None:
        get_logger().info(f"Pulling sales data for shop '{self.shop_id}'.")
        data: list[dict[str, Any]] = self.get_sales_data()
        data = self.prep_transaction_data(data)
        with SCDatabased() as db:
            db.save_etsy_data(self.shop_id, data)
        get_logger().info(f"Retrieved {len(data)} records for shop '{self.shop_id}'.")
