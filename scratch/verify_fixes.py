import json
from unittest.mock import MagicMock, patch
from modules.dm_agent import DungeonMasterAgent
from modules.character import Character
from modules.emotion_narrator import EmotionNarrator
from modules.rag_engine import RAGEngine

def test_fixes():
    # Setup mock components
    mock_character = Character.new("Riksha", "Fighter")
    mock_rag = MagicMock(spec=RAGEngine)
    mock_rag.query.return_value = "Some lore about Thornwall."
    mock_narrator = MagicMock(spec=EmotionNarrator)
    
    agent = DungeonMasterAgent(mock_character, mock_rag, mock_narrator)
    
    # 1. Test Tavern Conversation (No encounter, Social color)
    print("--- Test 1: Chatting with bartender ---")
    with patch('ollama.chat') as mock_chat:
        # Mocking a response that might have tried to call a tool incorrectly or just narrate
        mock_chat.return_value = {
            "message": {
                "role": "assistant",
                "content": "The bartender nods, wiping a glass. 'Typical Thornwall rain,' he grunts."
            }
        }
        reply = agent.respond("I chat with the bartender about the weather")
        print(f"Reply: {reply}")
        # Verify no tool calls were attempted if the prompt is working
        
    # 2. Test Whispering Woods (Random encounter OK)
    print("\n--- Test 2: Into the Whispering Woods ---")
    mock_character.current_scene = "Whispering Woods"
    with patch('ollama.chat') as mock_chat:
        # Mocking a tool call for random encounter
        mock_chat.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [{
                        "function": {
                            "name": "random_encounter",
                            "arguments": {"location": "Whispering Woods", "danger_level": "medium"}
                        }
                    }]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "As you step into the woods, a giant spider drops from the canopy!"
                }
            }
        ]
        reply = agent.respond("I head into the Whispering Woods alone")
        print(f"Reply: {reply}")

    # 3. Test Attack (Clean output, no raw JSON)
    print("\n--- Test 3: Attack Goblin ---")
    with patch('ollama.chat') as mock_chat:
         mock_chat.side_effect = [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [{
                        "function": {
                            "name": "roll_dice",
                            "arguments": {"skill": "Attack", "dc": 12, "player_name": "Riksha"}
                        }
                    }]
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": "Your blade connects with the goblin's shoulder, drawing dark blood!"
                }
            }
        ]
         reply = agent.respond("I attack the goblin")
         print(f"Reply: {reply}")
         assert "{" not in reply, "Raw JSON found in reply!"

if __name__ == "__main__":
    test_fixes()
