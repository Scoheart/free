#!/usr/bin/env python3
"""Build the public VPS JSON from stock, Black Friday and free VPS monitor feeds."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__:
    from .vps.feed import build_vps, write_vps
else:
    from vps.feed import build_vps, write_vps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the public VPS JSON from a vps-watch directory")
    parser.add_argument("--in", dest="src", required=True, help="directory with stock-state.json, bf-seen.json, free-vps-seen.json")
    parser.add_argument("--out", required=True, help="output JSON path, e.g. vps/index.json")
    args = parser.parse_args(argv)
    document = build_vps(Path(args.src))
    write_vps(document, Path(args.out))
    stock_providers = document["stock"]["providers"]
    print(
        "Wrote {out} free={free} dmit_plans={dmit} bwh_plans={bwh} bf={bf} leads={leads} updated={updated}".format(
            out=args.out,
            free=len(document["free_vps"]),
            dmit=len(stock_providers[0]["plans"]),
            bwh=len(stock_providers[1]["plans"]),
            bf=len(document["black_friday"]["official"]),
            leads=len(document["black_friday"]["leads"]),
            updated=document["updated_at_beijing"] or "-",
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
