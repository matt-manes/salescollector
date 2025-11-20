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
from data_service import EtsyDataService
from db import SCDatabased


def get_logger() -> loggi.Logger:
    """
    Returns
    -------
    loggi.Logger
        An Etsy logger.
    """
    return loggi.getLogger("etsy", Pathier(__file__).parent / "logs")


def log_and_raise_api_error(message: str) -> None:
    """
    Log an error message then raise an exception with that message.

    Parameters
    ----------
    message : str
        The error message to log and raise with.

    Raises
    ------
    exceptions.APIException
        Raises an exception with `message`.
    """
    get_logger().error(message)
    raise exceptions.APIException(message)


class OAuthProvider:
    """
    Handles OAuth for Etsy API.
    """

    @staticmethod
    def get_new_oauth() -> EtsyOAuth:
        """
        Get a new OAuth instance scoped for transactions and shops permissions.

        Returns
        -------
        EtsyOAuth
            The new OAuth instance.

        Raises
        ------
        exceptions.MissingEnvException
            If there's no 'sc_keystring' or 'sc_oauth-redirect' in the environment variables.
        """
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
        """
        Generates an authorization url and registers the OAuth state used.

        Returns
        -------
        str
            An authorization url to complete OAuth with.
        """
        oauth: EtsyOAuth = OAuthProvider.get_new_oauth()
        auth_url: str = oauth.get_auth_code()[0]
        OAuthProvider._save_state(oauth)
        return auth_url

    @staticmethod
    def state_exists(state: str) -> bool:
        """
        Whether the given state string exists.
        Used to verify the validity of the received callback.

        Parameters
        ----------
        state : str
            The state string to check.

        Returns
        -------
        bool
            Whether it exists.
        """
        with SCDatabased() as db:
            return db.state_exists(state)

    @staticmethod
    def _save_state(oauth_instance: EtsyOAuth) -> None:
        """
        Save the given OAuth instance to the database.

        Parameters
        ----------
        oauth_instance : EtsyOAuth
            The OAuth instance to save.
        """
        with SCDatabased() as db:
            db.register_oauth(oauth_instance.state, oauth_instance.code_verifier)

    @staticmethod
    def get_saved_oauth(state: str) -> EtsyOAuth:
        """
        Retrieves an OAuth instance from the given state.

        Parameters
        ----------
        state : str
            The previously used state.

        Returns
        -------
        EtsyOAuth
            The saved OAuth instance associated with the given state.

        Raises
        ------
        MissingSessionDataException
            If there's no OAuth entry matching `state`.
        """
        oauth: EtsyOAuth = OAuthProvider.get_new_oauth()
        with SCDatabased() as db:
            session: dict[str, str] = db.get_oauth(state)
        oauth.state = session["state"]
        oauth.code_verifier = session["code_verifier"]
        return oauth


class AuthenticatedClient:
    """
    Make authenticated requests to the Etsy API.
    """

    def __init__(self, token_data: dict[str, str]) -> None:
        """
        Initialize the instance.

        Parameters
        ----------
        token_data : dict[str, str]
            Token data received via OAuth.

        Raises
        ------
        exceptions.MissingEnvException
            If `sc_keystring` doesn't exist in env variable.
        """
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
        """
        Return an `AuthenticatedClient` instance from parameters provided by the Etsy callback.

        Parameters
        ----------
        code : str
            The authorization code received.
        state : str
            The state received.

        Returns
        -------
        Self
            A new instance

        Raises
        ------
        exceptions.MissingSessionDataException
            If there's no OAuth entry matching state.
        """
        oauth: EtsyOAuth = OAuthProvider.get_saved_oauth(state)
        oauth.set_authorisation_code(code=code, state=state)
        token_data: dict[str, str] = cast(dict[str, str], oauth.get_access_token())
        return cls(token_data)

    @cached_property
    def shop_id(self) -> int:
        """
        Returns
        -------
        int
            The shop id of the user that authenticated this instance.
        """
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
        return int(response.message["shop_id"])  # type: ignore

    def get_sales_data(self) -> list[dict[str, Any]]:
        """
        Returns
        -------
        list[dict[str, Any]]
            All available transaction data where this shop was the seller.
        """
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
                        self.shop_id,
                        limit=limit,
                        offset=offset,
                        was_paid=True,
                        was_canceled=False,
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

    def pull_data(self) -> None:
        """
        Retrieve and save transaction data for this seller.
        """
        get_logger().info(f"Pulling sales data for shop '{self.shop_id}'.")
        data: list[dict[str, Any]] = self.get_sales_data()
        EtsyDataService.save_transaction_data(self.shop_id, data)
        get_logger().info(f"Retrieved {len(data)} records for shop '{self.shop_id}'.")
