from pathier import Pathier

from db import SCDatabased

root = Pathier(__file__).parent


def main():
    """ """
    with SCDatabased() as db:
        db.execute_script(root / "schema.sql")


if __name__ == "__main__":
    main()
