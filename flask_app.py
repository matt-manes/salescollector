import dotenv

# etsy_python doesn't have any typing stub files
from etsy_python.v3.auth.OAuth import EtsyOAuth  # type: ignore
from flask import Flask, Response, make_response, request
from pathier import Pathier

import etsy
import exceptions

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


@app.route("/")
def landing():
    response: Response = make_response(load_content("landing.html"))
    code: str | None = request.args.get("code", None)
    state: str = request.args.get("state", "")
    print(state)
    if code is not None and etsy.state_exists(state):
        try:
            etsy.pull_data(code, state)
        except Exception:
            etsy.get_logger().exception("Error pulling shop data from Etsy\n")
            # TODO return different content with error message
    return response


@app.route("/authurl")
def get_etsy_auth_url():
    oauth: EtsyOAuth = etsy.get_oauth()
    auth_url: str
    state: str
    auth_url, state = oauth.get_auth_code()
    etsy.save_oauth(state, oauth.code_verifier)
    return auth_url
