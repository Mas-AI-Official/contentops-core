"""JSON CLI for the scoped GrowthOps control plane."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.growthops import GrowthStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("action", choices=["status", "skills", "jobs", "enqueue", "prospects", "save-prospect"])
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    store = GrowthStore(args.root)
    payload = json.loads(args.input.read_text(encoding="utf-8")) if args.input else None
    if args.action == "enqueue":
        if payload is None:
            parser.error("enqueue requires --input")
        result = store.enqueue(**payload)
    elif args.action == "save-prospect":
        if payload is None:
            parser.error("save-prospect requires --input")
        result = store.save_prospect(payload)
    else:
        result = getattr(store, args.action)()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
