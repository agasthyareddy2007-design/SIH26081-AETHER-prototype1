import re
from datetime import datetime, timedelta

def resolve_time(prompt_lower, base_date):
    # Base date as 2026-09-04 00:00:00 for calculation
    target_date = base_date
    
    # Days offset
    if "day after tomorrow" in prompt_lower:
        target_date += timedelta(days=2)
    elif "tomorrow" in prompt_lower:
        target_date += timedelta(days=1)
    elif re.search(r"in (\d+) days", prompt_lower):
        days = int(re.search(r"in (\d+) days", prompt_lower).group(1))
        target_date += timedelta(days=days)
    
    # Time offset
    hour = 12 # default
    time_match = re.search(r"at (\d+)(?:\:00)?\s*(am|pm)?", prompt_lower)
    if time_match:
        h = int(time_match.group(1))
        meridiem = time_match.group(2)
        if meridiem == 'pm' and h < 12:
            h += 12
        elif meridiem == 'am' and h == 12:
            h = 0
        hour = h
    elif re.search(r"(\d+)(?:\:00)?\s*(am|pm)", prompt_lower):
        time_match = re.search(r"(\d+)(?:\:00)?\s*(am|pm)", prompt_lower)
        h = int(time_match.group(1))
        meridiem = time_match.group(2)
        if meridiem == 'pm' and h < 12:
            h += 12
        elif meridiem == 'am' and h == 12:
            h = 0
        hour = h

    target_time = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    lead_time = int((target_time - base_date).total_seconds() / 3600)
    
    # Ensure lead_time is valid (non-negative, default to 12 if unsure but here we compute exactly)
    if lead_time < 0:
        lead_time = 0
    return target_time.strftime("%Y-%m-%d %H:%M:%S"), lead_time

base = datetime(2026, 9, 4, 0, 0, 0) # Simulation base time
print("tomorrow at 12 pm:", resolve_time("tomorrow at 12 pm", base))
print("in 3 days at 2:00 am:", resolve_time("in 3 days at 2:00 am", base))
print("today:", resolve_time("today", base))
