from pathier import Pathier

from db import SCDatabased


def main() -> None:
    """Initialize the database using the 'schema.sql' file."""
    with SCDatabased() as db:
        db.execute_script(Pathier(__file__).parent / "schema.sql")


if __name__ == "__main__":
    main()
