import csv
from typing import Any

from pathier import Pathier

from db import Rows, SCDatabased


class DataWriter:

    @staticmethod
    def get_date_patterns() -> list[str]:
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
    def convert_date(date: str) -> str:
        parts: list[str] = date.split("-")
        year: str = parts[0]
        month: str = parts[1]
        return f"{month.removeprefix('0')}/{year[2:]}"

    @staticmethod
    def get_data() -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        date_patterns: list[str] = DataWriter.get_date_patterns()
        with SCDatabased() as db:
            shops: Rows = db.select("shops", ["shop_id"])
            for i, shop in enumerate(shops, 1):
                for date in date_patterns:
                    row: dict[str, Any] = {}
                    row["participant id"] = f"Artist_{i}"
                    row["date"] = DataWriter.convert_date(date)
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
    def write_to_csv() -> Pathier:
        data: list[dict[str, Any]] = DataWriter.get_data()
        output_path: Pathier = Pathier(__file__).parent / "etsy-sales.csv"
        with output_path.open("w", newline="", encoding="utf-8") as file:
            writer: csv.DictWriter[str] = csv.DictWriter(
                file, fieldnames=data[0].keys()
            )
            writer.writeheader()
            writer.writerows(data)
        return output_path
