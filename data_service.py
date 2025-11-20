import csv
from datetime import datetime
from typing import Any

from pathier import Pathier

from db import Rows, SCDatabased


class EtsyDataService:
    """
    Handles processing/storing raw Etsy data and producing output in requested format.
    """

    @staticmethod
    def _get_date_patterns() -> list[str]:
        """
        Returns a list of sql wildcard patterns for grouping transactions by month and year.

        Returns
        -------
        list[str]
            A list of strings in the format 'YYYY-MM-%'.
        """
        dates: list[str] = []
        start: int = 2018
        stop: int = 2024
        for year in range(start, stop + 1):
            for month in range(1, 13):
                dates.append(f"{year}-{'0' if month < 10 else ''}{month}-%")
        return dates

    @staticmethod
    def _convert_date(date: str) -> str:
        """
        Convert the given date pattern to the requested format.

        Parameters
        ----------
        date : str
            A date pattern in the format 'YYYY-MM-%'.

        Returns
        -------
        str
            A date in the format 'MM/YY'.
        """
        parts: list[str] = date.split("-")
        year: str = parts[0]
        month: str = parts[1]
        return f"{month.removeprefix('0')}/{year[2:]}"

    @staticmethod
    def _prep_transaction_data(
        shop_id: int, data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Convert data returned from Etsy's API to database schema compatible format.

        Parameters
        ----------
        shop_id : int
            The shop id the given data is for.
        data : list[dict[str, Any]]
            The raw transaction data taken from the Etsy API.

        Returns
        -------
        list[dict[str, Any]]
            The transaction data prepped for database storage.
        """
        transactions: list[dict[str, Any]] = []
        for receipt in data:
            if receipt["seller_user_id"] == shop_id:
                for transaction in receipt["transactions"]:
                    prepped: dict[str, Any] = {}
                    prepped["receipt_id"] = receipt["receipt_id"]
                    prepped["sale_date"] = datetime.fromtimestamp(
                        receipt["created_timestamp"]
                    )
                    prepped["transaction_id"] = transaction["transaction_id"]
                    prepped["title"] = transaction["title"]
                    prepped["quantity"] = transaction["quantity"]
                    prepped["listing_id"] = transaction["listing_id"]
                    prepped["product_id"] = transaction["product_id"]
                    prepped["unit_price"] = float(transaction["price"]["amount"]) / (
                        1.0
                        if transaction["price"]["divisor"] == 0
                        else transaction["price"]["divisor"]
                    )
                    prepped["total_price"] = prepped["unit_price"] * prepped["quantity"]
                    transactions.append(prepped)
        return transactions

    @staticmethod
    def save_transaction_data(shop_id: int, data: list[dict[str, Any]]) -> None:
        """
        Save transaction data taken from the Etsy API to the database.

        Parameters
        ----------
        shop_id : int
            The shop id the given data is for.
        data : list[dict[str, Any]]
            The raw transaction data taken from the Etsy API response.
        """
        data = EtsyDataService._prep_transaction_data(shop_id, data)
        with SCDatabased() as db:
            db.save_etsy_data(shop_id, data)

    @staticmethod
    def get_condensed_data() -> list[dict[str, Any]]:
        """
        Returns
        -------
        list[dict[str, Any]]
            The data stored in the database in the condensed format requested by researcher.
        """
        data: list[dict[str, Any]] = []
        date_patterns: list[str] = EtsyDataService._get_date_patterns()
        with SCDatabased() as db:
            shops: Rows = db.select("shops", ["shop_id"])
            for i, shop in enumerate(shops, 1):
                for date in date_patterns:
                    row: dict[str, Any] = {}
                    row["participant id"] = f"Artist_{i}"
                    row["date"] = EtsyDataService._convert_date(date)
                    sales: Rows = db.select(
                        "sales",
                        ["SUM(total_price) AS revenue", "SUM(quantity) AS sales"],
                        where=f"shop_id = {shop['shop_id']} AND sale_date LIKE '{date}'",
                    )
                    row["revenue"] = (
                        sales[0]["revenue"] if sales[0]["revenue"] else "N/A"
                    )
                    row["sales"] = sales[0]["sales"] if sales[0]["sales"] else "N/A"
                    data.append(row)
        return data

    @staticmethod
    def write_data_to_csv() -> Pathier:
        """
        Write data to a csv file.

        Returns
        -------
        Pathier
            The path to the csv file.
        """
        data: list[dict[str, Any]] = EtsyDataService.get_condensed_data()
        output_path: Pathier = Pathier(__file__).parent / "etsy-sales.csv"
        if not data:
            output_path.touch()
            return output_path
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer: csv.DictWriter[str] = csv.DictWriter(
                file, fieldnames=data[0].keys()
            )
            writer.writeheader()
            writer.writerows(data)
        return output_path
