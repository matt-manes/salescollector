from datetime import datetime
from uuid import uuid4

from databased import Databased, Rows

from exceptions import MissingSessionDataException


class SCDatabased(Databased):
    def __init__(self) -> None:
        super().__init__("sc.sqlite3")

    def get_state(self) -> str:
        state: str = str(hash(uuid4()))
        while self.state_exists(state):
            state = str(hash(uuid4()))
        self.insert("states", ["state", "date_added"], [[state, datetime.now()]])
        return state

    def state_exists(self, state: str) -> bool:
        return self.count("states", where=f"state = '{state}'") > 0

    def register_oauth(self, state: str, code_verifier: str):
        self.insert(
            "states",
            ["state", "code_verifier", "date_added"],
            [[state, code_verifier, datetime.now()]],
        )

    def get_oauth(self, state: str) -> dict[str, str]:
        print(state)
        rows: Rows = self.select("states", where=f"state = '{state}'")
        print(self.select("states"))
        print(rows)
        if not rows:
            raise MissingSessionDataException()
        return rows[0]
