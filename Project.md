# The Chronicles of Eldenmoor: AI Dungeon Master

**Name:** Srutisri Raman Srinivasan
**Course:** CMPSC 441 / GAME 450

---

## Section 1: Scenarios List - Base System Functionality

This AI Dungeon Master is designed to handle the following core D&D scenarios:

- Tavern Social Encounters: Engaging with NPCs through natural dialogue, where the system tracks the social mood.
- Exploration & World Building: Sensory descriptions of diverse locales (Inn, City, Wilderness) based on RAG lore.
- Combat Resolution: Real-time resolution of attacks and monster encounters using dice-rolling logic.
- Inventory & Quest Management: Tracking player items and objectives across multiple sessions.
- Rules & Lore Lookup: Instant retrieval of 5e rules and status conditions during play.

---

## Section 2: Prompt Engineering & Model Parameters

### Model Configuration:

- Temperature (0.75): High enough for creative, vivid narration but low enough to maintain consistency in rules and persona.
- Max Tokens (400): Prevents the model from generating overwhelming text blocks, keeping the terminal experience readable.
- AI Libraries (LO2): Utilize the `ollama` Python library for local LLM inference and embeddings.

### System Prompt Logic:

Used a robust, role-based prompt that enforces strict narrative boundaries:

- Agency Protection: "Never narrate or describe the player character's actions... Only describe what the world, NPCs, and environment do."
- Context-Aware Safety: Explicit rules prevent "Random Encounters" from firing inside safe city/inn zones.
- Consequence Narration: "Assume the player's action has already happened... start your narration with the immediate consequence or NPC's reaction."

---

## Section 3: Tools Usage (LO1 & LO2)

The system leverages Python's ecosystem to provide mathematical and data-driven tools:

- `roll_dice`: Performs d20 checks and handles complex JSON parsing from the model.
- `manage_inventory`: Programmatically mutates the player's `Character` object state.
- `random_encounter`: Selects monsters from tiered danger tables based on the current scene.
- `condition_lookup`: Retrieves 5e mechanical rules for status effects like "Poisoned" or "Stunned."

---

## Section 4: Planning & Reasoning 

To ensure coherence, implemented a Multi-Step Reasoning Pass in `modules/dm_agent.py`:

- Before narrating, the agent runs an internal `_plan()` pass. This pass identifies the player's intent and determines if a tool is required before any story text is written.
- This "Think-Before-Speak" approach prevents the AI from hallucinating successes or failures that should be determined by the dice.

---

## Section 5: RAG Implementation 

I used a Retrieval-Augmented Generation pipeline powered by ChromaDB:

- Vector Storage: Lore entries are chunked and stored in a persistent `chroma_db` directory.
- Contextual Injection: The `RAGEngine` performs a similarity search for every player turn, injecting relevant info about monsters, spells, or locations (e.g., "Thornwall City") directly into the DM's context window.
- Lore Sources: Knowledge is indexed from JSON files in the `data/` directory.

---

## Section 6: Additional Tools / Innovation 

### **The Emotion-Aware Narrator**

For the innovation requirement, I built a dynamic narration layer in `modules/emotion_narrator.py`:

- Real-time Classification: Every DM response is analyzed by a fast classification call to detect its mood (Combat, Magic, Social, Dread, etc.).
- Rich Terminal UI: Using the `rich` library, the system automatically changes text color and prepends unique emojis based on the detected emotion.
- Impact: This creates a visceral, immersive experience where the terminal UI actually changes as the story gets darker or more heroic.

---

## Section 7: Code Quality & Modular Design 

The system is built for maintainability with a modular file structure:

- `main.py`: Entry point and UI loop.
- `modules/`: Contains separate, decoupled logic for `character`, `dice`, `dm_agent`, `narrator`, `rag`, and `tools`.
- **Version Control**: Follows professional standards with a `.gitignore` to prevent database and save file bloat in the repository.
