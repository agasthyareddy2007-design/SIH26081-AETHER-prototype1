import re

def extract_area_name(prompt_lower):
    # Match in/at/for ONLY as separate words, followed by location name
    # Location name stops at common sentence terminators or specific target words
    # Added boundaries \b to avoid matching "at" inside "what"
    match = re.search(r'\b(?:in|at|for)\b\s+([a-zA-Z\s]+?)(?:\s+(?:what|time|forecast|weather|temperature|tomorrow|today|next|on|at)|\!|\?|\.|$)', prompt_lower)
    if match:
        # Strip out preposition if accidentally caught
        return match.group(1).strip()
    return None

prompts = [
    "What will the temperature be in Gachibowli tomorrow at 12 PM?",
    "what's the weather in mumbai tomorrow?",
    "will it rain in delhi at 6 pm?",
    "Give me the forecast for Bengaluru on September 10 at 3 PM.",
    "what is the weather at hyderabad airport?"
]

for p in prompts:
    print(f"'{p}' -> '{extract_area_name(p.lower())}'")

