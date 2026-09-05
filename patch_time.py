with open('/home/agasthya/ai models/api_reference.py', 'r') as f:
    text = f.read()

import re

search = r"""time_match = re.search(r"\\b(?:at\\s+)?(\\d+)(?:\\:00)?\\s*(am|pm)?\\b", prompt_lower)"""
replace = r"""time_match = re.search(r"\b(?:at\s+)(\d+)(?:\:00)?\s*(am|pm)?\b", prompt_lower)
    if not time_match:
        time_match = re.search(r"\b(\d+)(?:\:00)?\s*(am|pm)\b", prompt_lower)"""

text = text.replace(search, replace)

search2 = """elif not meridiem and h < 12 and h >= 1 and 'pm' in prompt_lower:
            h += 12"""
replace2 = "" # In the new logic, if no meridiem, we don't blindly add 12 if "pm" is just anywhere in string, EXCEPT if "at 3" and "pm" is in the string? Wait, if they say "at 15", `h=15`. If they say "at 3" and "pm" is missing but at the end, the first regex `at \d+` captures it.
replace2 = """elif not meridiem and h < 12 and h >= 1:
            # Check if PM is just separated by some text, or just assume PM if < 12
            pass # Keep it simple: if they said 'at 3' without pm, they probably meant 3 PM if day, but let's default to standard parsing. If they said 'at 3 pm', it gets caught by meridiem."""
text = text.replace(search2, replace2)

with open('/home/agasthya/ai models/api_reference.py', 'w') as f:
    f.write(text)
