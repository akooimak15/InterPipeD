"""Dump JSON schemas for events to stdout or files.

Usage:
  python3 scripts/dump_event_schemas.py          # print to stdout
  python3 scripts/dump_event_schemas.py outdir  # write files to outdir
"""
import json
import sys
from pathlib import Path

from interpiped.events import schemas


def main(argv: list[str]) -> int:
    outdir = None
    if len(argv) > 1:
        outdir = Path(argv[1])
        outdir.mkdir(parents=True, exist_ok=True)

    schemas_map = schemas.get_event_schemas()

    if outdir is None:
        print(json.dumps(schemas_map, indent=2))
        return 0

    for name, schema in schemas_map.items():
        path = outdir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
