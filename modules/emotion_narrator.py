"""Emotion-aware narration layer.

Detects the dominant emotional tone of the DM's narration with a tiny
classification call, then prints the text with rich color and an emoji
prefix that match the mood. Also exposes helpers for system messages and
formatted dice-roll panels.
"""
from __future__ import annotations

from typing import Any

import ollama
from rich.console import Console
from rich.panel import Panel

EMOTION_LABELS: list[str] = [
    "combat", "magic", "exploration", "social", "dread", "triumph", "neutral",
]

EMOTION_COLORS: dict[str, str] = {
    "combat": "bold red",
    "magic": "bold magenta",
    "exploration": "bold cyan",
    "social": "bold yellow",
    "dread": "bold red3",
    "triumph": "bold green",
    "neutral": "white",
}

EMOTION_EMOJI: dict[str, str] = {
    "combat": "⚔️ ",
    "magic": "🔮",
    "exploration": "🌲",
    "social": "🍺",
    "dread": "💀",
    "triumph": "✅",
    "neutral": "📜",
}

CLASSIFY_PROMPT = """
Classify the emotional tone of this D&D narration with ONE word only.
Choose exactly one from: combat, magic, exploration, social, dread, triumph, neutral

Rules:
- combat: fighting, attacks, weapons, battle, blood, damage
- magic: spells, enchantments, arcane energy, potions, supernatural
- exploration: travel, discovering new places, forests, dungeons, curiosity
- social: conversation, taverns, NPCs talking, bargaining, friendships
- dread: horror, undead, terror, darkness, death, despair, cursed
- triumph: victory, success, defeating an enemy, celebration, achievement
- neutral: anything that doesn't clearly fit above

Text to classify:
{text}

Respond with ONE word only, no punctuation, no explanation.
"""


class EmotionNarrator:
    """Wrap rich console output with emotion-driven coloring."""

    def __init__(self, model: str = "llama3.2:latest") -> None:
        """Store the model used for the lightweight classification call."""
        self.model = model
        self.console = Console()

    def detect_emotion(self, text: str) -> str:
        """Ask the model to label the dominant emotion in one word."""
        if not text.strip():
            return "neutral"
        try:
            # BUG FIX: Use the new f-string prompt format and increase tokens
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "user", "content": CLASSIFY_PROMPT.format(text=text)},
                ],
                options={"temperature": 0.0, "num_predict": 10},
            )
            # ollama-python may return either a dict or a ChatResponse object.
            message = getattr(response, "message", None)
            if message is None and isinstance(response, dict):
                message = response.get("message")
            content = getattr(message, "content", None)
            if content is None and isinstance(message, dict):
                content = message.get("content", "")
            raw = (content or "").strip().lower()
        except Exception as e:
            self.console.print(f"[dim](emotion classifier failed: {e})[/dim]")
            return "neutral"
        self.console.print(f"[dim](classify raw response: {raw!r})[/dim]")
        for label in EMOTION_LABELS:
            if label in raw:
                return label
        return "neutral"

    def narrate(self, text: str) -> str:
        """Detect emotion, print the text with the matching color, return label."""
        emotion = self.detect_emotion(text)
        color = EMOTION_COLORS.get(emotion, "white")
        emoji = EMOTION_EMOJI.get(emotion, "")
        self.console.print(f"[{color}]{emoji} {text}[/{color}]")
        return emotion

    def print_system(self, text: str) -> None:
        """Print a dim system-style message."""
        self.console.print(f"[dim white]{text}[/dim white]")

    def print_roll(self, result: dict[str, Any]) -> None:
        """Render a dice-roll result dict in a colored Panel."""
        if result.get("critical_success"):
            style, title = "bold green", "✨ CRITICAL SUCCESS"
        elif result.get("critical_fail"):
            style, title = "bold red", "💥 CRITICAL FAIL"
        elif result.get("success"):
            style, title = "green", "Success"
        else:
            style, title = "red", "Fail"
        body = (
            f"[bold]{result.get('skill', 'Check')}[/bold]\n"
            f"Rolled: [bold]{result.get('roll')}[/bold]   "
            f"DC: [bold]{result.get('dc')}[/bold]"
        )
        self.console.print(Panel(body, title=title, style=style))
