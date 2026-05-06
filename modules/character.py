"""Character model for the AI Dungeon Master.

Holds player state (HP, gold, inventory, quests, current scene) and
provides rich-formatted display helpers for stats, inventory, and quests.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# HP per starting class as specified in the project requirements.
STARTING_HP: dict[str, int] = {
    "Fighter": 12,
    "Rogue": 8,
    "Wizard": 6,
    "Cleric": 10,
}

# Default starter inventory, kept identical for every class to keep
# things simple — the DM can grant class-flavored items in narration.
DEFAULT_INVENTORY: list[str] = ["Torch", "Hempen Rope (50ft)", "Rations (3 days)"]

DEFAULT_SCENE = "The Rusty Flagon Inn"

_console = Console()


@dataclass
class Character:
    """Player character with persistent stats, inventory, and quest log."""

    name: str
    player_class: str
    hp: int = 10
    max_hp: int = 10
    level: int = 1
    gold: int = 25
    inventory: list[str] = field(default_factory=lambda: list(DEFAULT_INVENTORY))
    quests: list[dict[str, Any]] = field(default_factory=list)
    current_scene: str = DEFAULT_SCENE

    @classmethod
    def new(cls, name: str, player_class: str) -> "Character":
        """Build a fresh character with class-appropriate starting HP."""
        hp = STARTING_HP.get(player_class, 10)
        return cls(name=name, player_class=player_class, hp=hp, max_hp=hp)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the character to a JSON-friendly dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        """Rebuild a character from a previously serialized dict."""
        return cls(
            name=data["name"],
            player_class=data["player_class"],
            hp=int(data.get("hp", 10)),
            max_hp=int(data.get("max_hp", 10)),
            level=int(data.get("level", 1)),
            gold=int(data.get("gold", 0)),
            inventory=list(data.get("inventory", [])),
            quests=list(data.get("quests", [])),
            current_scene=str(data.get("current_scene", DEFAULT_SCENE)),
        )

    def add_item(self, item: str) -> None:
        """Append an item to the character's inventory."""
        self.inventory.append(item)

    def remove_item(self, item: str) -> bool:
        """Remove the first matching inventory entry. Returns True if removed."""
        for existing in self.inventory:
            if existing.lower() == item.lower():
                self.inventory.remove(existing)
                return True
        return False

    def add_quest(self, title: str, objectives: list[str]) -> None:
        """Append a new quest with a list of textual objectives."""
        self.quests.append(
            {
                "title": title,
                "objectives": [{"text": o, "completed": False} for o in objectives],
                "completed": False,
            }
        )

    def complete_objective(self, quest_title: str, objective: str) -> bool:
        """Mark a single objective complete; close the quest if all are done."""
        for quest in self.quests:
            if quest["title"].lower() != quest_title.lower():
                continue
            for obj in quest["objectives"]:
                if obj["text"].lower() == objective.lower():
                    obj["completed"] = True
            if all(o["completed"] for o in quest["objectives"]):
                quest["completed"] = True
            return True
        return False

    def display_stats(self) -> None:
        """Render character stats as a rich Table."""
        table = Table(title=f"{self.name} the {self.player_class}", show_header=True)
        table.add_column("Stat", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_row("Class", self.player_class)
        table.add_row("Level", str(self.level))
        table.add_row("HP", f"{self.hp} / {self.max_hp}")
        table.add_row("Gold", f"{self.gold} gp")
        table.add_row("Scene", self.current_scene)
        table.add_row("Items", str(len(self.inventory)))
        table.add_row("Active Quests", str(sum(1 for q in self.quests if not q["completed"])))
        _console.print(table)

    def display_inventory(self) -> None:
        """Render the inventory list inside a rich Panel."""
        if not self.inventory:
            _console.print(Panel("Your pack is empty.", title="Inventory", style="yellow"))
            return
        body = "\n".join(f"  • {item}" for item in self.inventory)
        _console.print(Panel(body, title=f"Inventory ({len(self.inventory)})", style="yellow"))

    def display_quests(self) -> None:
        """Render the quest log with per-objective completion marks."""
        if not self.quests:
            _console.print(Panel("No quests yet. The road ahead is open.", title="Quests", style="green"))
            return
        lines: list[str] = []
        for q in self.quests:
            mark = "[green]✔[/green]" if q["completed"] else "[yellow]●[/yellow]"
            lines.append(f"{mark} [bold]{q['title']}[/bold]")
            for obj in q["objectives"]:
                sub = "[green]✔[/green]" if obj["completed"] else "[dim]○[/dim]"
                lines.append(f"    {sub} {obj['text']}")
        _console.print(Panel("\n".join(lines), title="Quests", style="green"))
