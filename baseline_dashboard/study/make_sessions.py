"""
make_sessions.py
----------------
Generate session links for a study run.

    python -m study.make_sessions --participants 24 --base-url https://<host>

Each participant gets two links, one per block. Assignment is **counterbalanced,
not merely randomized**: exactly half the participants meet CLUE in block 1 and
half in block 2, so condition never correlates with order. With plain random
assignment a small sample can easily land 9:3, leaving order confounded with
condition and no way to separate the two afterwards.

Which half a given participant falls into is shuffled, so the assignment is not
predictable from the participant number.

Writes `study/sessions.json` (gitignored — it is participant assignment data)
and prints a table to paste into a run sheet.
"""

import argparse
import json
import secrets
import random
from pathlib import Path

from study.session import DEV_TOKENS, REGISTRY_PATH, TOKEN_PARAM

TOKEN_BYTES = 3  # 6 hex chars: unguessable enough for a moderated study


def _token(existing: set[str]) -> str:
    while True:
        token = secrets.token_hex(TOKEN_BYTES)
        if token not in existing:
            existing.add(token)
            return token


def build_registry(count: int, seed: int | None = None) -> dict[str, dict]:
    """
    Token -> {participant, block, clue} for `count` participants.

    Half get CLUE first; the assignment of which half is shuffled.
    """
    if count < 1:
        raise ValueError("need at least one participant")

    rng = random.Random(seed)
    participants = [f"P{i:02d}" for i in range(1, count + 1)]

    # Exactly half see CLUE in block 1 (odd counts put the extra in the
    # baseline-first group, which keeps the split as even as it can be).
    clue_first = [True] * (count // 2) + [False] * (count - count // 2)
    rng.shuffle(clue_first)

    registry: dict[str, dict] = {}
    # Seeded with the dev tokens so a generated one can never collide with them
    # (hex tokens can't today, but that is a property of the format, not a
    # guarantee anyone should have to remember).
    used: set[str] = set(DEV_TOKENS)
    for participant, first in zip(participants, clue_first):
        for block, clue in ((1, first), (2, not first)):
            registry[_token(used)] = {
                "participant": participant,
                "block": block,
                "clue": clue,
            }
    return registry


def links(registry: dict[str, dict], base_url: str) -> list[tuple[str, int, str, str]]:
    """(participant, block, condition, url), ordered for a run sheet."""
    base = base_url.rstrip("/")
    rows = [
        (
            entry["participant"],
            entry["block"],
            "CLUE" if entry["clue"] else "baseline",
            f"{base}/?{TOKEN_PARAM}={token}",
        )
        for token, entry in registry.items()
    ]
    return sorted(rows, key=lambda row: (row[0], row[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participants", type=int, required=True)
    parser.add_argument("--base-url", default="http://localhost:8501")
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Fix the counterbalancing shuffle, for a reproducible run sheet.",
    )
    parser.add_argument(
        "--out", type=Path, default=REGISTRY_PATH,
        help=f"Registry path (default: {REGISTRY_PATH}).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite an existing registry.",
    )
    args = parser.parse_args()

    if args.out.exists() and not args.force:
        raise SystemExit(
            f"{args.out} already exists. Overwriting it would orphan every link "
            f"already handed out — pass --force if that is what you want."
        )

    registry = build_registry(args.participants, seed=args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(registry, indent=2) + "\n")

    rows = links(registry, args.base_url)
    width = max(len(url) for *_, url in rows)
    print(f"\n{'Participant':<12}{'Block':<7}{'Condition':<11}{'Link':<{width}}")
    print("-" * (30 + width))
    for participant, block, condition, url in rows:
        print(f"{participant:<12}{block:<7}{condition:<11}{url:<{width}}")

    first_clue = sum(
        1 for e in registry.values() if e["block"] == 1 and e["clue"]
    )
    print(
        f"\n{len(rows)} links for {args.participants} participants written to "
        f"{args.out}\n{first_clue} start with CLUE, "
        f"{args.participants - first_clue} start with baseline."
    )


if __name__ == "__main__":
    main()
