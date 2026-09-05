import re
prompt_lower = "what's the weather in mumbai tomorrow?"
match = re.search(r'\b(?:in|at|for)\b\s+([a-zA-Z\s]+?)(?:\s+(?:what|time|now|forecast|weather|temperature|tomorrow|today|next|on|at|\d)|\!|\?|\.|&|$)', prompt_lower)
if match:
    print("Match:", match.group(1).strip())
else:
    print("No Match!")
