from typing import cast

import dotenv
from etsy_python.v3.auth.OAuth import EtsyOAuth  # type: ignore
from etsy_python.v3.resources import User  # type: ignore
from etsy_python.v3.resources.Receipt import ReceiptResource  # type: ignore
from etsy_python.v3.resources.Session import EtsyClient  # type: ignore
from flask import Flask, Response, make_response, request
from pathier import Pathier

import etsy
import exceptions

app = Flask(__name__)

if not Pathier(".env").exists():
    raise exceptions.MissingEnvException("Could not find '.env' file.")
dotenv.load_dotenv(".env")


def load_content(filename: str) -> str:
    pages_dir: Pathier = Pathier(__file__).parent / "pages"
    return (pages_dir / filename).read_text(encoding="utf-8")


def pull_data(code: str, state: str):
    client: EtsyClient = etsy.get_authenticated_client(code, state)
    user = User.UserResource(client)
    # etsy_python lib has type errors
    # this ugliness ain't my fault
    shop_id: str = cast(str, user.get_me().message["shop_id"])  # type: ignore
    data = ReceiptResource(client).get_shop_receipts(int(shop_id))
    print(data)
    # TODO save data to database


@app.route("/")
def landing():
    response: Response = make_response(load_content("landing.html"))
    code: str | None = request.args.get("code", None)
    state: str = request.args.get("state", "")
    print(state)
    if code is not None and etsy.state_exists(state):
        pull_data(code, state)
    return response


@app.route("/authurl")
def get_etsy_auth_url():
    oauth: EtsyOAuth = etsy.get_etsy_oauth()
    auth_url, state = oauth.get_auth_code()
    etsy.save_oauth(state, oauth.code_verifier)
    return auth_url
