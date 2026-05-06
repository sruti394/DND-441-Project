from modules.emotion_narrator import EmotionNarrator

def test_narrative_flow():
    narrator = EmotionNarrator()
    
    samples = [
        # 1. Social Intro
        "As you push open the creaky door of the Rusty Flagon Inn, the warm glow of lanterns and the savory smell of roasting meats envelop you. Patrons eye you from their seats around the bar, awaiting your presence.",
        
        # 2. Social Interaction
        "Old Bren leaned back against the bar, cradling his massive arms across his chest. 'What's your story, traveler? What brings you to Thornwall City?'",
        
        # 3. Sudden Threat (Combat/Dread)
        "A large, hairy leg dangling in the air, attached to a massive spider. The spider's beady eyes locked onto you, and it began to lower itself, silk threads stretching out like ghostly fingers.",
        
        # 4. Active Combat
        "The spider's momentum carried it forward, and its legs snapped out in a flurry of movement. Riksha barely managed to dodge the blow as the second leg struck the wooden surface with a loud thud."
    ]

    print("=== Emotion Classification Test ===\n")
    for i, text in enumerate(samples, 1):
        print(f"Sample {i}:")
        # .narrate() prints the colored text and returns the label
        emotion = narrator.narrate(text)
        print(f"Detected Label: {emotion}\n" + "-"*30)

if __name__ == "__main__":
    test_narrative_flow()
