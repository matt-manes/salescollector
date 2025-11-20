from datetime import datetime
from typing import Any

from databased import Databased, Rows
from pathier import Pathier

from exceptions import MissingSessionDataException


class SCDatabased(Databased):
    """
    Database implementation.
    """

    def __init__(self) -> None:
        """
        Initialize the database.
        """
        super().__init__(Pathier(__file__).parent / "sc.sqlite3", connection_timeout=30)

    def state_exists(self, state: str) -> bool:
        """
        Checks whether a given state exists in the database.

        Parameters
        ----------
        state : str
            The state string to check for.

        Returns
        -------
        bool
            Whether it exists or not.
        """
        return self.count("states", where=f"state = '{state}'") > 0

    def register_oauth(self, state: str, code_verifier: str) -> None:
        """
        Store oauth details in the database.

        Parameters
        ----------
        state : str
            The state string used for the OAuth instance.
        code_verifier : str
            The code verifier used for the OAuth instance.
        """
        self.insert(
            "states",
            ["state", "code_verifier", "date_added"],
            [[state, code_verifier, datetime.now()]],
        )

    def get_oauth(self, state: str) -> dict[str, str]:
        """
        Get the OAuth details associated with the given state.

        Parameters
        ----------
        state : str
            The state string associated with the OAuth instance.

        Returns
        -------
        dict[str, str]
            A dict containing the keys 'state' and 'code_verifier'.

        Raises
        ------
        MissingSessionDataException
            If there's no database entry matching `state`.
        """
        if not self.state_exists(state):
            raise MissingSessionDataException()
        rows: Rows = self.select(
            "states", ["state", "code_verifier"], where=f"state = '{state}'"
        )
        return rows[0]

    def save_etsy_data(self, shop_id: int, transactions: list[dict[str, Any]]) -> None:
        """
        Save Etsy transaction data to the database.

        Parameters
        ----------
        shop_id : int
            The shop id associated with the transactions.
        transactions : list[dict[str, Any]]
            The transactions to save to the database.
            Each entry should have the keys:
                * listing_id: int
                * product_id: int
                * receipt_id: int
                * transaction_id: int
                * title
                * unit_price
                * quantity
                * total_price
                * sale_date
                * date_added
        """
        date_added: datetime = datetime.now()
        if not self.count("shops", where=f"shop_id = {shop_id}"):
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
                "unit_price",
                "quantity",
                "total_price",
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
                    transaction["unit_price"],
                    transaction["quantity"],
                    transaction["total_price"],
                    transaction["sale_date"],
                    date_added,
                ]
                for transaction in transactions
            ],
        )
