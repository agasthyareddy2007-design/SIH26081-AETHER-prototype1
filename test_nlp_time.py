import re
from datetime import datetime, timedelta

def resolve_time(prompt_lower, base_date: datetime):
    target_date = None
    
    # Date offset
    if "day after tomorrow" in prompt_lower:
        target_date = base_date + timedelta(days=2)
    elif "tomorrow" in prompt_lower:
        target_date = base_date + timedelta(days=1)
    elif "today" in prompt_lower:
        target_date = base_date
    elif re.search(r"\b(september|sep|october|oct|november|nov)\s+(\d+)\b", prompt_lower):
        m_match = re.search(r"\b(september|sep|october|oct|november|nov)\s+(\d+)\b", prompt_lower)
        month_str = m_match.group(1)[:3]
        day = int(m_match.group(2))
        month_map = {'sep': 9, 'oct': 10, 'nov': 11}
        target_date = datetime(2026, month_map[month_str], day)
    
    if target_date is None:
        return None, None
        
    hour = 12 # Default
    time_match = re.search(r"\bat\s+(\d+)(?:\:00)?\s*(am|pm)?\b", prompt_lower)
    if time_match:
        h = int(time_match.group(1))
        meridiem = time_match.group(2)
        if meridiem == 'pm' and h < 12:
            h += 12
        elif meridiem == 'am' and h == 12:
            h = 0
        elif not meridiem and h < 12 and h >= 1 and 'pm' in prompt_lower: # fallback
             h += 12
        hour = h

    target_time = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    lead_time = int((target_time - base_date).total_seconds() / 3600)
    
    if lead_time < 0:
        lead_time = 0
        
    return target_time.strftime("%Y-%m-%d %H:%M:%S"), lead_time

base = datetime(2026, 9, 4, 0, 0, 0) # Simulation base time
tests = [
    "tomorrow at 12 pm",
    "today at 6 am",
    "day after tomorrow at 3 pm",
    "on september 10 at 4 pm",
    "next week",
    "hello how are you"
]

for t in tests:
    print(f"'{t}' -> {resolve_time(t, base)}")
