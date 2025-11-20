import dotenv
import loggi
from flask import Flask, Response, request, send_file
from pathier import Pathier

import etsy
import exceptions
from data_service import EtsyDataService
from etsy import AuthenticatedClient, OAuthProvider

app = Flask(__name__)

if not (Pathier(__file__).parent / ".env").exists():
    raise exceptions.MissingEnvException("Could not find '.env' file.")
dotenv.load_dotenv(Pathier(__file__).parent / ".env")


def load_content(filename: str) -> str:
    pages_dir: Pathier = Pathier(__file__).parent / "pages"
    return (pages_dir / filename).read_text(encoding="utf-8")


def get_logger() -> loggi.Logger:
    return loggi.getLogger("app", Pathier(__file__).parent / "logs")


@app.route("/")
def landing() -> str:
    code: str | None = request.args.get("code", None)
    state: str = request.args.get("state", "")
    if code is not None and OAuthProvider.state_exists(state):
        try:
            AuthenticatedClient.from_redirect(code, state).pull_data()
        except Exception:
            etsy.get_logger().exception("Error pulling shop data from Etsy\n")
            return load_content("error.html")
        else:
            return load_content("thanks.html")
    if code is not None and not OAuthProvider.state_exists(state):
        get_logger().info(
            f"Url has code param present ('{code}'), but no valid state param ('{state}')."
        )
        return load_content("error.html")
    return load_content("landing.html")


@app.route("/authurl")
def get_etsy_auth_url() -> str:
    return OAuthProvider.get_auth_url()


@app.route("/salesdata")
def get_csv_data() -> Response:
    return send_file(EtsyDataService.write_data_to_csv())
