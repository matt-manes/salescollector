import dotenv
import loggi

# etsy_python doesn't have any typing stub files
from flask import Flask, Response, make_response, request
from pathier import Pathier

import etsy
import exceptions
from etsy import AuthenticatedClient, OAuthProvider

app = Flask(__name__)

# TODO Add "The term 'Etsy' is a trademark of Etsy, Inc. This application uses the Etsy API but is not endorsed or certified by Etsy, Inc."
# TODO to home page

# TODO Add route that triggers csv dump

if not Pathier(".env").exists():
    raise exceptions.MissingEnvException("Could not find '.env' file.")
dotenv.load_dotenv(".env")


def load_content(filename: str) -> str:
    pages_dir: Pathier = Pathier(__file__).parent / "pages"
    return (pages_dir / filename).read_text(encoding="utf-8")


def get_logger() -> loggi.Logger:
    return loggi.getLogger("app", Pathier(__file__).parent / "logs")


@app.route("/")
def landing():
    response: Response = make_response(load_content("landing.html"))
    code: str | None = request.args.get("code", None)
    state: str = request.args.get("state", "")
    print(state)
    if code is not None and OAuthProvider.state_exists(state):
        try:
            AuthenticatedClient.from_redirect(code, state).pull_data()
        except Exception:
            etsy.get_logger().exception("Error pulling shop data from Etsy\n")
            # TODO return different content with error message
    if code is not None and not OAuthProvider.state_exists(state):
        get_logger().info(
            f"Url has code param present ('{code}'), but no valid state param ('{state}')."
        )
        # TODO return different content with error message
    return response


@app.route("/authurl")
def get_etsy_auth_url():
    return OAuthProvider.get_auth_url()
