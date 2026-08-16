#!/usr/bin/env python3
"""Validate the ONE CAREER league data pack.

Catches the failure modes that break a career simulation before anyone plays it:
a club sitting in two divisions at once, a division whose declared size does not
match its club list, promotion wiring that points nowhere, an abbreviation
collision that would make two rows of a table indistinguishable, and reputation
values that contradict the division's own band.

Usage:
    python3 tools/validate_data.py            # validate, print report
    python3 tools/validate_data.py --strict   # also fail on warnings
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HEX = set("0123456789abcdefABCDEF")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load_world() -> dict:
    return json.loads((DATA / "world.json").read_text(encoding="utf-8"))


def load_packs(world: dict) -> dict[str, dict]:
    packs = {}
    for entry in world["packs"]:
        path = DATA / entry["file"]
        if not path.exists():
            err(f"world.json references missing pack file: {entry['file']}")
            continue
        packs[entry["pack_id"]] = json.loads(path.read_text(encoding="utf-8"))
    return packs


def is_hex_colour(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 7
        and value[0] == "#"
        and all(c in HEX for c in value[1:])
    )


def check_pack(pack_id: str, pack: dict, world_season: str) -> tuple[dict, int]:
    """Returns (club_id -> division_id, club count)."""
    seen_clubs: dict[str, str] = {}
    total = 0

    if pack.get("pack_id") != pack_id:
        err(f"[{pack_id}] pack_id field is '{pack.get('pack_id')}', expected '{pack_id}'")

    if pack.get("season") != world_season:
        err(
            f"[{pack_id}] season '{pack.get('season')}' does not match world season "
            f"'{world_season}'. Mixing seasons inside one world produces impossible "
            f"pyramids (a club promoted AND still in the tier below)."
        )

    columns = pack["columns"]
    idx = {name: i for i, name in enumerate(columns)}
    for required in ("id", "name", "abbr", "rep"):
        if required not in idx:
            err(f"[{pack_id}] columns is missing required column '{required}'")
            return seen_clubs, 0

    division_ids = {d["id"] for d in pack["divisions"]}
    abbrs: Counter[str] = Counter()

    for div in pack["divisions"]:
        div_id = div["id"]
        clubs = div.get("clubs", [])
        generated = div.get("generation", {}).get("mode") == "procedural"

        # --- size -------------------------------------------------------
        if generated:
            if clubs:
                err(
                    f"[{div_id}] declares procedural generation but also ships "
                    f"{len(clubs)} clubs — pick one source of truth."
                )
            else:
                warn(
                    f"[{div_id}] is procedurally generated ({div['team_count']} slots). "
                    f"Import a verified club list before release."
                )
        elif len(clubs) != div["team_count"]:
            err(
                f"[{div_id}] team_count is {div['team_count']} but {len(clubs)} clubs "
                f"are listed."
            )

        # --- promotion / relegation wiring ------------------------------
        for direction in ("promotion", "relegation"):
            move = div.get(direction)
            if not move:
                continue
            target = move.get("to")
            if target is not None and target not in division_ids:
                err(
                    f"[{div_id}] {direction}.to points at '{target}', which is not a "
                    f"division in this pack."
                )
            slots = move.get("automatic", 0) + move.get("playoff", 0)
            if target is None and direction == "promotion" and slots:
                err(f"[{div_id}] is the top division but declares {slots} promotion slots.")
            if slots >= div["team_count"]:
                err(f"[{div_id}] {direction} moves {slots} of {div['team_count']} clubs.")

        # --- club rows ---------------------------------------------------
        band = div.get("reputation_band")
        for row in clubs:
            if len(row) != len(columns):
                err(f"[{div_id}] row has {len(row)} values, expected {len(columns)}: {row[:2]}")
                continue
            total += 1
            club_id = row[idx["id"]]
            name = row[idx["name"]]

            if club_id in seen_clubs:
                err(
                    f"[{pack_id}] club '{club_id}' ({name}) appears in both "
                    f"{seen_clubs[club_id]} and {div_id}. A club cannot be in two "
                    f"tiers in the same season."
                )
            else:
                seen_clubs[club_id] = div_id

            if not club_id.startswith(f"{pack_id}_"):
                err(f"[{div_id}] club id '{club_id}' is not prefixed with '{pack_id}_'")

            abbrs[row[idx["abbr"]]] += 1

            rep = row[idx["rep"]]
            if not isinstance(rep, int) or not 0 <= rep <= 100:
                err(f"[{div_id}] {name}: rep must be an int 0-100, got {rep!r}")
            elif band and not band[0] <= rep <= band[1]:
                warn(
                    f"[{div_id}] {name}: rep {rep} sits outside the division band "
                    f"{band}. Intentional for a fallen giant or a runaway favourite — "
                    f"otherwise a typo."
                )

            for col in ("primary", "secondary"):
                if col in idx and not is_hex_colour(row[idx[col]]):
                    err(f"[{div_id}] {name}: {col} '{row[idx[col]]}' is not a #RRGGBB colour")

            if "founded" in idx:
                founded = row[idx["founded"]]
                if not isinstance(founded, int) or not (founded == 0 or 1800 <= founded <= 2030):
                    err(f"[{div_id}] {name}: founded {founded!r} is out of range")

    for abbr, count in abbrs.items():
        if count > 1:
            warn(
                f"[{pack_id}] abbreviation '{abbr}' is used by {count} clubs. Tables and "
                f"the scorebug will read ambiguously."
            )

    return seen_clubs, total


def main() -> int:
    strict = "--strict" in sys.argv

    world = load_world()
    packs = load_packs(world)

    grand_total = 0
    per_pack: list[tuple[str, int, int]] = []

    for pack_id, pack in packs.items():
        clubs, total = check_pack(pack_id, pack, world["season"])
        grand_total += total
        per_pack.append((pack_id, len(pack["divisions"]), total))

    # Cross-pack: transfer corridors must reference divisions that exist.
    all_divisions = {d["id"] for p in packs.values() for d in p["divisions"]}
    for corridor in world["transfer_corridors"]["corridors"]:
        if corridor["from"] not in all_divisions:
            err(f"transfer corridor from unknown division '{corridor['from']}'")
        for target in corridor["to"]:
            if target not in all_divisions:
                err(f"transfer corridor to unknown division '{target}'")

    for preset in world["career_start_presets"]["presets"]:
        for div in preset["divisions"]:
            if div not in all_divisions:
                err(f"career preset '{preset['id']}' references unknown division '{div}'")

    for pack_id, slots in world["continental_slots"].items():
        if pack_id == "comment":
            continue
        if pack_id not in packs:
            err(f"continental_slots references unloaded pack '{pack_id}'")

    # --- report ---------------------------------------------------------
    print("ONE CAREER — data pack validation")
    print(f"world season: {world['season']}\n")
    print(f"{'pack':<6} {'divisions':>10} {'clubs':>7}")
    print("-" * 25)
    for pack_id, divs, total in sorted(per_pack):
        print(f"{pack_id:<6} {divs:>10} {total:>7}")
    print("-" * 25)
    print(f"{'total':<6} {sum(d for _, d, _ in per_pack):>10} {grand_total:>7}\n")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")

    if errors:
        return 1
    if strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
