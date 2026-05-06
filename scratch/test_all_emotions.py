from modules.emotion_narrator import EmotionNarrator

def test_emotions():
    narrator = EmotionNarrator()
    
    test_data = [
        ("The goblin slashes at you with its rusty blade", "combat"),
        ("Arcane energy crackles as the spell takes shape", "magic"),
        ("The forest path winds deeper into unknown territory", "exploration"),
        ("The bartender laughs and pours you another ale", "social"),
        ("The undead creature shambles toward you, reeking of rot", "dread"),
        ("The enemy falls and the crowd erupts in cheers", "triumph"),
        ("The innkeeper nods and hands you a key", "neutral")
    ]

    print("=== Emotion Classification Final Verification ===\n")
    all_passed = True
    for text, expected in test_data:
        actual = narrator.detect_emotion(text)
        status = "✅ PASS" if actual == expected else f"❌ FAIL (Got: {actual})"
        print(f"Input: '{text}'")
        print(f"Expected: {expected} | Actual: {actual} | {status}\n")
        if actual != expected:
            all_passed = False
    
    if all_passed:
        print("PERFECT: All 7 emotions classified correctly!")
    else:
        print("Some emotions failed. Check the rules in the prompt.")

if __name__ == "__main__":
    test_emotions()
