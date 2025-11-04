from datetime import datetime
from typing import Any

from databased import Databased, Rows

from exceptions import MissingSessionDataException


class SCDatabased(Databased):
    def __init__(self) -> None:
        super().__init__("sc.sqlite3")

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

    def save_etsy_data(self, shop_id: str, transactions: list[dict[str, Any]]) -> None:
        date_added: datetime = datetime.now()
        if not self.count("shops", where=f"shop_id = '{shop_id}'"):
            self.insert("shops", ["shop_id", "date_added"], [[shop_id, date_added]])
        self.insert(
            "sales",
            [
                "listing_id",
                "product_id",
                "receipt_id",
                "transaction_id",
                "shop_id",
                "title",
                "price",
                "sale_date",
                "date_added",
            ],
            [
                [
                    transaction["listing_id"],
                    transaction["product_id"],
                    transaction["receipt_id"],
                    transaction["transaction_id"],
                    shop_id,
                    transaction["title"],
                    transaction["price"],
                    transaction["sale_date"],
                    date_added,
                ]
                for transaction in transactions
            ],
        )
