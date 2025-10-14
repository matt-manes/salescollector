import loggi
import requests
from pathier import Pathier

import exceptions


class EtsyRequests:
    """Static class for making requests to the Etsy API."""

    _default_headers: dict[str, str] | None = None
    _logger: loggi.Logger = loggi.getLogger("etsy", "logs")

    @staticmethod
    def get_default_headers() -> dict[str, str]:
        """
        Returns the default headers for API requests.
        Currently consists of just 'x-api-key'.

        Returns
        -------
        dict[str, str]
            The default headers.

        Raises
        ------
        exceptions.MissingSecretException
            If the file `secret.toml` doesn't exist or is missing a 'keystring' field.
        """
        if not EtsyRequests._default_headers:
            secrets_path: Pathier = Pathier("secrets.toml")
            if not secrets_path.exists():
                raise exceptions.MissingSecretException(
                    "Could not find file 'secrets.toml'"
                )
            secrets: dict[str, str] = secrets_path.loads()
            if "keystring" not in secrets:
                raise exceptions.MissingSecretException(
                    "Missing 'keystring' field in 'secrets.toml'"
                )
            EtsyRequests._default_headers = {"x-api-key": secrets["keystring"]}
        return EtsyRequests._default_headers

    @staticmethod
    def get_logger() -> loggi.Logger:
        """
        Get a logger to use with requests.

        Returns
        -------
        loggi.Logger
            The request logger.
        """
        return EtsyRequests._logger

    @staticmethod
    def ping() -> requests.Response:
        """
        Ping the Etsy server.

        Returns
        -------
        requests.Response
            The server response.
        """
        logger: loggi.Logger = EtsyRequests.get_logger()
        url: str = "https://api.etsy.com/v3/application/openapi-ping"
        logger.info(f"Pinging Etsy at {url}")
        response: requests.Response = requests.get(
            url, headers=EtsyRequests.get_default_headers()
        )
        logger.info(f"Ping completed with response code '{response.status_code}'")
        return response
