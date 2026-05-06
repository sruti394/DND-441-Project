"""Dungeon Master agent.

Wires together the LLM, RAG knowledge base, dice tools, and emotion-aware
narration into a single agent that processes one player turn at a time.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import ollama

from .character import Character
from .emotion_narrator import EmotionNarrator
from .rag_engine import RAGEngine
from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

CONFIG_PATH = Path("config/dm_config.json")
HISTORY_LIMIT = 20
HISTORY_CONTEXT_TURNS = 6

REQUIRED_TOOL_ARGS: dict[str, list[str]] = {
    "roll_dice": ["skill", "dc", "player_name"],
    "manage_inventory": ["action", "item"],
    "random_encounter": ["location", "danger_level"],
    "condition_lookup": ["condition_name"],
}


class DungeonMasterAgent:
    """Orchestrates plan → retrieve → respond → tool-call loop for one turn."""

    def __init__(
        self,
        character: Character,
        rag_engine: RAGEngine,
        narrator: EmotionNarrator,
    ) -> None:
        """Store references and load the DM config from disk."""
        self.character = character
        self.rag = rag_engine
        self.narrator = narrator
        self.config = self._load_config()
        self.model: str = self.config.get("model", "llama3.2:latest")
        self.system_prompt: str = self.config.get("system_prompt", "You are a DM.")
        self.temperature: float = float(self.config.get("temperature", 0.75))
        self.max_tokens: int = int(self.config.get("max_tokens", 400))
        self.seed: int = int(self.config.get("seed", 441))
        self.conversation_history: list[dict[str, str]] = []

    def _load_config(self) -> dict[str, Any]:
        """Read the DM config JSON or fall back to safe defaults."""
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[DM] WARNING: {CONFIG_PATH} not found, using defaults.")
            return {}
        except json.JSONDecodeError as e:
            print(f"[DM] ERROR parsing {CONFIG_PATH}: {e}. Using defaults.")
            return {}

    def _plan(self, player_input: str) -> str:
        """Run a fast, cool reasoning pass and return the DM's internal plan."""
        plan_system = (
            "You are the Dungeon Master's inner voice. In 2-4 short sentences, "
            "reason through: (1) what the player is attempting; (2) whether a "
            "tool call is needed and which one of [roll_dice, manage_inventory, "
            "random_encounter, condition_lookup]; (3) what narrative direction "
            "best serves the story. Be concise. Do not narrate the outcome."
        )
        scene = f"Current scene: {self.character.current_scene}. Character: {self.character.name} the {self.character.player_class}."
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": plan_system},
                    {"role": "user", "content": f"{scene}\nPlayer says: {player_input}"},
                ],
                options={"temperature": 0.3, "num_predict": 200},
            )
            return (response.get("message") or {}).get("content", "").strip()
        except Exception as e:
            return f"(planning failed: {e})"

    def _build_prompt(self, player_input: str) -> list[dict[str, str]]:
        """Assemble the full message list for the main chat completion."""
        scene_header = (
            f"=== Scene ===\n{self.character.current_scene}\n"
            f"=== Character ===\n{self.character.name} the {self.character.player_class} "
            f"(HP {self.character.hp}/{self.character.max_hp}, "
            f"Level {self.character.level}, Gold {self.character.gold})"
        )
        knowledge = self.rag.query(player_input, n_results=3)
        plan = self._plan(player_input)
        context_blocks = [scene_header]
        if knowledge:
            context_blocks.append(f"=== Relevant Knowledge ===\n{knowledge}")
        if plan:
            context_blocks.append(f"=== DM's internal reasoning ===\n{plan}")
        system_message = {
            "role": "system",
            "content": self.system_prompt + "\n\n" + "\n\n".join(context_blocks),
        }
        recent_history = self.conversation_history[-HISTORY_CONTEXT_TURNS:]
        return [system_message, *recent_history, {"role": "user", "content": player_input}]

    def process_tool_call(self, tool_name: str, args: dict[str, Any]) -> str:
        """Dispatch to the matching tool function from tools.py."""
        fn = TOOL_FUNCTIONS.get(tool_name)
        if fn is None:
            return f"(unknown tool: {tool_name})"
        if not isinstance(args, dict):
            return f"(tool {tool_name} called with non-object arguments: {args!r})"
        required = REQUIRED_TOOL_ARGS.get(tool_name, [])
        missing = [
            key for key in required
            if key not in args or args[key] in (None, "", [], {})
        ]
        if missing:
            return (
                f"(tool {tool_name} not called: missing or empty required "
                f"argument(s): {', '.join(missing)})"
            )
        try:
            return fn(args, self.character)
        except Exception as e:
            return f"(tool {tool_name} failed: {e})"

    def _run_completion(self, messages: list[dict[str, Any]]) -> str:
        """Call ollama.chat with tools and resolve any tool calls in a loop."""
        working = list(messages)
        for _ in range(5):  # cap at 5 rounds
            try:
                response = ollama.chat(
                    model=self.model,
                    messages=working,
                    tools=TOOL_SCHEMAS,
                    options={
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                        "seed": self.seed,
                    },
                )
            except Exception as e:
                return f"(The DM's voice falters... LLM call failed: {e})"

            message = response.get("message") or {}
            tool_calls = message.get("tool_calls") or []

            # BUG 1 Fix: If the model wants to call tools, we MUST process them and loop.
            if tool_calls:
                working.append(message)
                for call in tool_calls:
                    fn_block = call.get("function") or {}
                    name = fn_block.get("name", "")
                    args = fn_block.get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    result = self.process_tool_call(name, args)
                    self.narrator.print_system(f"[tool:{name}] {result}")
                    working.append({"role": "tool", "content": result, "name": name})
                # After processing all tool calls in this round, loop back for the final narration.
                continue

            # No more tool calls; extract the narrative content.
            content = (message.get("content") or "").strip()

            # BUG 1 Safeguard: Never return raw JSON strings as narration.
            if content.startswith("{") and '"name"' in content and '"arguments"' in content:
                # If the model hallucinated a tool call into the text, skip it and loop one more time
                # with a hidden prompt to provide the actual narration.
                working.append(message)
                working.append({"role": "user", "content": "Please provide the narrative description of the outcome."})
                continue

            if content:
                return content

        return "(The DM hesitates — too many tool calls or invalid responses.)"

    def respond(self, player_input: str) -> str:
        """Full per-turn pipeline: plan, retrieve, complete, update history."""
        messages = self._build_prompt(player_input)
        reply = self._run_completion(messages)
        self.conversation_history.append({"role": "user", "content": player_input})
        self.conversation_history.append({"role": "assistant", "content": reply})
        if len(self.conversation_history) > HISTORY_LIMIT:
            self.conversation_history = self.conversation_history[-HISTORY_LIMIT:]
        return reply

    def explore_scene(self) -> str:
        """Generate a vivid description of the current scene for /look."""
        knowledge = self.rag.query(self.character.current_scene, n_results=3)
        prompt = (
            f"Describe the scene '{self.character.current_scene}' to the player in "
            f"3-5 sentences of vivid sensory detail. Use the knowledge below if relevant.\n\n"
            f"=== Knowledge ===\n{knowledge}"
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={"temperature": self.temperature, "num_predict": self.max_tokens},
            )
            return (response.get("message") or {}).get("content", "").strip()
        except Exception as e:
            return f"(The mists obscure the scene... {e})"
