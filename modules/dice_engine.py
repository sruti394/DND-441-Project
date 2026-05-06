"""Dice engine for the AI Dungeon Master.

Provides single-die rolls, d20 rolls, full skill checks against a DC, and
parsed dice-notation damage rolls (e.g. "2d6+3").
"""
from __future__ import annotations

import random
import re
from typing import Any

# Crit thresholds for d20 — fixed by 5e rules.
CRIT_SUCCESS = 20
CRIT_FAIL = 1


def roll(sides: int) -> int:
    """Roll a single die with the given number of sides."""
    if sides < 1:
        raise ValueError(f"Dice must have at least 1 side, got {sides}")
    return random.randint(1, sides)


def roll_d20() -> int:
    """Roll a single d20."""
    return roll(20)


def skill_check(skill_name: str, dc: int) -> dict[str, Any]:
    """Roll a d20 skill check vs. a Difficulty Class.

    Returns a dict with the raw roll, the DC, success/fail flags, crit flags,
    and a pre-formatted message ready to be shown to the player.
    """
    r = roll_d20()
    crit_success = r == CRIT_SUCCESS
    crit_fail = r == CRIT_FAIL
    success = (r >= dc) or crit_success
    if crit_fail:
        success = False

    if crit_success:
        verdict = "CRITICAL SUCCESS"
    elif crit_fail:
        verdict = "CRITICAL FAIL"
    elif success:
        verdict = "SUCCESS"
    else:
        verdict = "FAIL"

    message = f"{skill_name} check (DC {dc}): rolled {r} → {verdict}"
    return {
        "skill": skill_name,
        "roll": r,
        "dc": dc,
        "success": success,
        "critical_success": crit_success,
        "critical_fail": crit_fail,
        "message": message,
    }


_DICE_PATTERN = re.compile(r"^\s*(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def roll_damage(dice_notation: str) -> int:
    """Parse a string like '2d6+3' or '1d8' or '3d10-1' and return the total."""
    match = _DICE_PATTERN.match(dice_notation)
    if not match:
        raise ValueError(f"Could not parse dice notation: {dice_notation!r}")
    count = int(match.group(1))
    sides = int(match.group(2))
    modifier_str = match.group(3)
    modifier = int(modifier_str.replace(" ", "")) if modifier_str else 0
    if count < 1 or sides < 1:
        raise ValueError(f"Invalid dice notation values: {dice_notation!r}")
    total = sum(roll(sides) for _ in range(count)) + modifier
    return total
