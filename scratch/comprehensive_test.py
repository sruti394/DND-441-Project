import sys
import os
from modules.character import Character
from modules.dm_agent import DungeonMasterAgent
from modules.emotion_narrator import EmotionNarrator
from modules.rag_engine import RAGEngine

def run_test_report():
    print("Initializing test environment (RAG Warmup)...")
    try:
        character = Character.new("Riksha", "Fighter")
        narrator = EmotionNarrator()
        rag = RAGEngine()
        agent = DungeonMasterAgent(character, rag, narrator)
    except Exception as e:
        print(f"Error initializing system: {e}")
        return

    test_cases = [
        "I chat with the bartender about the weather",
        "I head into the Whispering Woods alone",
        "I attack the goblin"
    ]

    print("\n" + "="*50)
    print("D&D AI AGENT SYSTEM REPORT")
    print("="*50 + "\n")

    for i, user_input in enumerate(test_cases, 1):
        print(f"TEST CASE #{i}: '{user_input}'")
        print("-" * 30)
        
        # Reset character scene for specific tests
        if i == 1:
            character.current_scene = "The Rusty Flagon Inn"
        elif i == 2:
            character.current_scene = "Thornwall City Gates"
        elif i == 3:
            character.current_scene = "A dark alleyway"

        # Capturing narration and tool calls
        # Note: dm_agent.respond() calls narrator.print_system() for tool calls
        # and we manually call narrator.narrate() on the reply.
        
        reply = agent.respond(user_input)
        emotion = narrator.narrate(reply)
        
        print(f"\nFinal Emotion Label: {emotion}")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    run_test_report()
