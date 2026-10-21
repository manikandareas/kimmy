import json

from pydantic import TypeAdapter

from kimmy.main import app
from kimmy.schemas import FleetId


def main() -> None:
    """Export contracts offline without loading database credentials."""
    schema = app.openapi()
    schema["components"]["schemas"]["FleetId"] = TypeAdapter(FleetId).json_schema()
    print(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
