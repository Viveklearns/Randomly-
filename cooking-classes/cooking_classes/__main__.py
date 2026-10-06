"""CLI: python -m cooking_classes [--sources web_search,reddit] [--dry-run]"""

import argparse
import json
import logging

from .config import load_config
from .pipeline import run


def main() -> None:
    ap = argparse.ArgumentParser(description="Find Bergen County, NJ cooking classes.")
    ap.add_argument("--config", help="path to config.toml")
    ap.add_argument("--sources", help="comma list: web_search,reddit,instagram,pages,manual")
    ap.add_argument("--dry-run", action="store_true",
                    help="collect and filter only; print candidates, no extraction calls")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    stats = run(load_config(args.config),
                only=args.sources.split(",") if args.sources else None,
                dry_run=args.dry_run)
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
