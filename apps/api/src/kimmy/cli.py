import argparse
import asyncio
import json

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.config import get_settings
from kimmy.database import create_engine
from kimmy.fleet.repository import FleetRepository
from kimmy.fleet.schemas import Period
from kimmy.fleet.service import FleetService
from kimmy.main import app
from kimmy.schemas import FleetId
from kimmy.seed import SEED_END, SEED_START, SeedNotEmptyError, seed_fleet


def export_openapi() -> None:
    """Export contracts offline without loading database credentials."""
    schema = app.openapi()
    schema["components"]["schemas"]["FleetId"] = TypeAdapter(FleetId).json_schema()
    print(json.dumps(schema, indent=2))


async def run_fleet(args: argparse.Namespace) -> None:
    engine = create_engine(get_settings())
    try:
        if args.command == "seed":
            print(json.dumps(await seed_fleet(engine), indent=2))
        else:
            period = Period(start=args.start, end=args.end)
            async with AsyncSession(engine) as session:
                async with session.begin():
                    # One coherent snapshot across all report queries.
                    await session.execute(
                        text(
                            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                        )
                    )
                    report = await FleetService(FleetRepository(session)).report(
                        args.unit,
                        period,
                        int(args.depot) if args.depot is not None else None,
                    )
                    print(report.model_dump_json(indent=2))
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline OpenAPI export and fleet administration commands."
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("openapi")
    commands.add_parser("seed")
    report = commands.add_parser("fleet-report")
    report.add_argument("--unit", default="KM-001")
    report.add_argument("--start", default=SEED_START.isoformat())
    report.add_argument("--end", default=SEED_END.isoformat())
    report.add_argument("--depot", type=TypeAdapter(FleetId).validate_python)
    args = parser.parse_args()
    if args.command in {None, "openapi"}:
        export_openapi()
    else:
        try:
            asyncio.run(run_fleet(args))
        except (SeedNotEmptyError, ValueError) as error:
            parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
