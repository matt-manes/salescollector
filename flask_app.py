from pathlib import Path

from flask import Flask

app = Flask(__name__)

pages_path: Path = Path(__file__).parent / "pages"


@app.route("/")
def landing() -> str:
    return (pages_path / "landing.html").read_text(encoding="utf-8")


@app.route("/pretendauth")
def pretendauth() -> str:
    return (pages_path / "pretendauth.html").read_text(encoding="utf-8")
