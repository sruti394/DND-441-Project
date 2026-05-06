"""Tool definitions and implementations for the DM agent.

Each tool is exposed both as an Ollama tool-calling JSON schema (for the
model to invoke) and as a Python function (which the agent dispatches when
the model asks to call it).
"""
from __future__ import annotations

import random
from typing import Any, Callable

from . import dice_engine
from .character import Character


# --- Tool schemas in Ollama tool-calling format ---------------------------
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": (
                "Roll a d20 skill check or saving throw against a DC. Use for "
                "combat attack rolls, stealth, persuasion, lockpicking, and any "
                "contested action with an uncertain outcome."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "Name of the skill or check, e.g. 'Stealth', 'Persuasion', 'Attack'.",
                    },
                    "dc": {
                        "type": "integer",
                        "description": "Difficulty Class. 5 trivial, 10 easy, 15 medium, 20 hard, 25 very hard.",
                    },
                    "player_name": {
                        "type": "string",
                        "description": "The character making the check.",
                    },
                },
                "required": ["skill", "dc", "player_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_inventory",
            "description": (
                "Add or remove an item from the player's inventory. Call whenever "
                "the player picks up, loses, drops, sells, or consumes an item."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove"],
                        "description": "'add' to give the player an item, 'remove' to take one away.",
                    },
                    "item": {
                        "type": "string",
                        "description": "Name of the item, e.g. 'Healing Potion', 'Rusty Key'.",
                    },
                },
                "required": ["action", "item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "random_encounter",
            "description": (
                "Generate a random monster encounter for a location. Use when the "
                "player wanders into wilderness, dungeon corridors, or other "
                "dangerous areas where monsters might appear."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Where the encounter happens, e.g. 'Whispering Woods'.",
                    },
                    "danger_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Encounter difficulty tier.",
                    },
                },
                "required": ["location", "danger_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "condition_lookup",
            "description": (
                "Look up the mechanical effect of a D&D 5e condition. Use when a "
                "spell or attack inflicts a status condition and the rules text "
                "is needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "condition_name": {
                        "type": "string",
                        "description": "Condition name, e.g. 'Poisoned', 'Stunned', 'Frightened'.",
                    },
                },
                "required": ["condition_name"],
            },
        },
    },
]


# --- Static encounter and condition tables --------------------------------
ENCOUNTER_TABLE: dict[str, list[dict[str, Any]]] = {
    "low": [
        {"name": "Goblin", "hp": 7, "ac": 15, "flavor": "skulks from behind a mossy stone, cackling"},
        {"name": "Giant Rat", "hp": 7, "ac": 12, "flavor": "scuttles from a crack in the wall, eyes red"},
        {"name": "Bandit", "hp": 11, "ac": 12, "flavor": "steps from the shadows with a drawn scimitar"},
        {"name": "Skeleton", "hp": 13, "ac": 13, "flavor": "rises from a heap of bones with a rusted blade"},
    ],
    "medium": [
        {"name": "Orc", "hp": 15, "ac": 13, "flavor": "roars a challenge and hefts a brutal greataxe"},
        {"name": "Wolf Pack (3)", "hp": 11, "ac": 13, "flavor": "circles silently, jaws dripping"},
        {"name": "Giant Spider", "hp": 26, "ac": 14, "flavor": "drops from the ceiling on a strand of silk"},
        {"name": "Zombie", "hp": 22, "ac": 8, "flavor": "shambles forward, jaw hanging loose"},
    ],
    "high": [
        {"name": "Troll", "hp": 84, "ac": 15, "flavor": "ducks under the archway, regenerating a fresh wound"},
        {"name": "Vampire Spawn", "hp": 82, "ac": 15, "flavor": "smiles, teeth flashing in the lantern light"},
        {"name": "Young Red Dragon", "hp": 178, "ac": 18, "flavor": "lands with a thunder of wings, smoke curling from its nostrils"},
    ],
}

CONDITION_TABLE: dict[str, str] = {
    "poisoned": (
        "Poisoned: disadvantage on attack rolls and ability checks for the duration."
    ),
    "stunned": (
        "Stunned: incapacitated, can't move, can speak only falteringly. Auto-fails STR and "
        "DEX saves; attacks against you have advantage."
    ),
    "blinded": (
        "Blinded: can't see, auto-fails any ability check that requires sight; attack rolls "
        "against you have advantage, your attack rolls have disadvantage."
    ),
    "frightened": (
        "Frightened: disadvantage on ability checks and attack rolls while the source of fear "
        "is in line of sight; can't willingly move closer to the source."
    ),
    "charmed": (
        "Charmed: can't attack the charmer or target them with harmful abilities; the charmer "
        "has advantage on social checks against you."
    ),
    "paralyzed": (
        "Paralyzed: incapacitated, can't move or speak. Auto-fails STR and DEX saves; attacks "
        "have advantage and any hit within 5ft is a critical."
    ),
    "prone": (
        "Prone: only movement option is to crawl unless you stand up (costs half your speed). "
        "Disadvantage on attack rolls; melee attacks against you have advantage, ranged have disadvantage."
    ),
    "exhausted": (
        "Exhaustion (6 levels): 1 disadvantage on ability checks; 2 speed halved; 3 disadvantage "
        "on attacks and saves; 4 HP max halved; 5 speed reduced to 0; 6 death."
    ),
}


# --- Tool implementations -------------------------------------------------
def tool_roll_dice(args: dict[str, Any], character: Character) -> str:
    """Run a skill check and return a one-line formatted result."""
    skill = str(args.get("skill", "Check"))
    
    # Robust DC extraction
    dc_raw = args.get("dc", 10)
    if isinstance(dc_raw, dict):
        dc = int(dc_raw.get("value", 10))
    else:
        try:
            dc = int(dc_raw)
        except (ValueError, TypeError):
            dc = 10
            
    player = str(args.get("player_name", character.name))
    result = dice_engine.skill_check(skill, dc)
    return f"[{player}] {result['message']}"


def tool_manage_inventory(args: dict[str, Any], character: Character) -> str:
    """Mutate the character inventory and return a confirmation message."""
    action = str(args.get("action", "")).lower()
    item = str(args.get("item", "")).strip()
    if not item:
        return "Inventory action failed: no item name provided."
    if action == "add":
        character.add_item(item)
        return f"Added '{item}' to {character.name}'s inventory."
    if action == "remove":
        removed = character.remove_item(item)
        if removed:
            return f"Removed '{item}' from {character.name}'s inventory."
        return f"'{item}' was not in {character.name}'s inventory."
    return f"Unknown inventory action: {action!r} (expected 'add' or 'remove')."


def tool_random_encounter(args: dict[str, Any], character: Character) -> str:
    """Pick a monster from the danger-level table and describe the setup."""
    location = str(args.get("location", "the wilds")).lower()
    # BUG 2 Fix: Prevent encounters in safe indoor locations.
    if any(safe in location for safe in ["inn", "tavern", "bar", "flagon"]):
        return "No encounter — this is a safe indoor location."

    danger = str(args.get("danger_level", "low")).lower()
    table = ENCOUNTER_TABLE.get(danger, ENCOUNTER_TABLE["low"])
    monster = random.choice(table)
    return (
        f"Encounter at {location} ({danger} danger): a {monster['name']} "
        f"(HP {monster['hp']}, AC {monster['ac']}) {monster['flavor']}."
    )


def tool_condition_lookup(args: dict[str, Any], character: Character) -> str:
    """Return the mechanical effect of a named condition."""
    name = str(args.get("condition_name", "")).strip().lower()
    if not name:
        return "No condition name provided."
    effect = CONDITION_TABLE.get(name)
    if effect is None:
        known = ", ".join(sorted(c.title() for c in CONDITION_TABLE))
        return f"Unknown condition '{name}'. Known: {known}."
    return effect


# --- Dispatch table -------------------------------------------------------
TOOL_FUNCTIONS: dict[str, Callable[[dict[str, Any], Character], str]] = {
    "roll_dice": tool_roll_dice,
    "manage_inventory": tool_manage_inventory,
    "random_encounter": tool_random_encounter,
    "condition_lookup": tool_condition_lookup,
}
