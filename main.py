"""Entry point for the AI Dungeon Master.

Handles welcome banner, save/load of the character, the main REPL loop,
and dispatch of the special slash commands (/look, /inventory, /quests,
/stats, /quit).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from modules.character import Character
from modules.dm_agent import DungeonMasterAgent
from modules.emotion_narrator import EmotionNarrator
from modules.rag_engine import RAGEngine

SAVE_PATH = Path("saves/character_save.json")
VALID_CLASSES = ["Fighter", "Rogue", "Wizard", "Cleric"]
console = Console()


def banner() -> None:
    """Print the opening welcome banner."""
    console.print(
        Panel.fit(
            "[bold magenta]⚔  THE CHRONICLES OF ELDENMOOR  ⚔[/bold magenta]\n"
            "[dim]An AI Dungeon Master powered by a local LLM.[/dim]\n"
            "[dim]Type /look, /inventory, /quests, /stats, or /quit at any time.[/dim]",
            border_style="magenta",
        )
    )


def setup_hint() -> None:
    """Tell the user how to install Ollama models if they're missing."""
    console.print(
        Panel(
            "[bold yellow]First-time setup:[/bold yellow]\n"
            "  • Install Ollama:  https://ollama.com\n"
            "  • Pull the chat model:        [cyan]ollama pull llama3.2:latest[/cyan]\n"
            "  • Pull the embedding model:   [cyan]ollama pull nomic-embed-text[/cyan]\n"
            "  • Make sure the Ollama service is running before you continue.",
            border_style="yellow",
        )
    )


def load_save() -> Character | None:
    """Return a saved Character if a save file exists and parses, else None."""
    if not SAVE_PATH.exists():
        return None
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            return Character.from_dict(json.load(f))
    except (OSError, json.JSONDecodeError, KeyError) as e:
        console.print(f"[red]Could not read save file ({e}); starting fresh.[/red]")
        return None


def save_character(character: Character) -> None:
    """Persist the character to disk; warn (do not crash) on failure."""
    try:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(character.to_dict(), f, indent=2)
        console.print(f"[dim]Saved to {SAVE_PATH}[/dim]")
    except OSError as e:
        console.print(f"[red]Failed to save character: {e}[/red]")


def prompt_new_character() -> Character:
    """Interactively ask for the character's name and class."""
    name = ""
    while not name:
        name = console.input("[bold]Your character's name:[/bold] ").strip()
    classes_str = ", ".join(VALID_CLASSES)
    while True:
        chosen = console.input(f"[bold]Choose a class ({classes_str}):[/bold] ").strip().title()
        if chosen in VALID_CLASSES:
            return Character.new(name=name, player_class=chosen)
        console.print(f"[red]'{chosen}' is not one of: {classes_str}[/red]")


def maybe_resume_or_new() -> Character:
    """Detect a save and ask whether to resume or start fresh."""
    saved = load_save()
    if saved is None:
        console.print("[dim]No save detected. Forging a new hero...[/dim]")
        return prompt_new_character()
    answer = console.input(
        f"[bold]Save found for [cyan]{saved.name}[/cyan] the [cyan]{saved.player_class}[/cyan]. "
        f"(c)ontinue or (n)ew? [/bold]"
    ).strip().lower()
    if answer.startswith("n"):
        return prompt_new_character()
    return saved


def handle_slash_command(cmd: str, character: Character, agent: DungeonMasterAgent, narrator: EmotionNarrator) -> bool:
    """Dispatch /commands. Returns True if the loop should exit."""
    cmd = cmd.lower().strip()
    if cmd in ("/quit", "/exit"):
        save_character(character)
        narrator.print_system("The tale pauses... safe travels, adventurer.")
        return True
    if cmd == "/look":
        description = agent.explore_scene()
        narrator.narrate(description)
    elif cmd == "/inventory":
        character.display_inventory()
    elif cmd == "/quests":
        character.display_quests()
    elif cmd == "/stats":
        character.display_stats()
    else:
        narrator.print_system(f"Unknown command: {cmd}. Try /look, /inventory, /quests, /stats, /quit.")
    return False


def game_loop(character: Character, agent: DungeonMasterAgent, narrator: EmotionNarrator) -> None:
    """Main REPL: read input, dispatch, narrate, repeat."""
    description = agent.explore_scene()
    narrator.narrate(description)
    while True:
        try:
            raw = console.input("\n[bold cyan]> [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            save_character(character)
            narrator.print_system("Until next time, adventurer.")
            return
        if not raw:
            continue
        if raw.startswith("/"):
            if handle_slash_command(raw, character, agent, narrator):
                return
            continue
        reply = agent.respond(raw)
        if reply:
            narrator.narrate(reply)


def main() -> int:
    """Top-level entry point — wires components and runs the game loop."""
    banner()
    setup_hint()
    character = maybe_resume_or_new()
    narrator = EmotionNarrator()
    narrator.print_system("Indexing the tomes of Eldenmoor (RAG warmup)...")
    try:
        rag_engine = RAGEngine()
    except Exception as e:
        console.print(
            Panel(
                f"[red]Failed to initialize RAG / Ollama embeddings:[/red]\n{e}\n\n"
                "Verify Ollama is running and that 'nomic-embed-text' is pulled.",
                border_style="red",
            )
        )
        return 1
    agent = DungeonMasterAgent(character=character, rag_engine=rag_engine, narrator=narrator)
    try:
        game_loop(character, agent, narrator)
    finally:
        save_character(character)
    return 0


if __name__ == "__main__":
    sys.exit(main())
