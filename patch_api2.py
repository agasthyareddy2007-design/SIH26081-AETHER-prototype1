with open('/home/agasthya/ai models/api_reference.py', 'r') as f:
    text = f.read()

import re

search1 = """def extract_area_name(prompt_lower):
    # Try to heuristically extract location name, else fallback or use full prompt
    # A simple but practical implementation for this prototype
    # If it sees keywords like 'in', 'at', 'for'
    match = re.search(r'(?:in|at|for)\s+([a-zA-Z\s]+?)(?:\s+(?:what|time|forecast|weather|temperature)|\!|\?|$)', prompt_lower)
    if match:
        return match.group(1).strip()
    return prompt_lower[:50].strip() # fallback"""

repl1 = """from datetime import timedelta
# BASE TIME FOR DATE MATH
CURRENT_SIMULATED_TIME = datetime(2026, 9, 4, 12, 0, 0)

def extract_area_name(prompt_lower):
    # Use word boundaries so 'at' inside 'what' is skipped
    match = re.search(r'\\b(?:in|at|for)\\b\\s+([a-zA-Z\\s]+?)(?:\\s+(?:what|time|now|forecast|weather|temperature|tomorrow|today|next|on|at|\\d)|\\!|\\?|\\.|&|$)', prompt_lower)
    if match:
        return match.group(1).strip()
    return None

def resolve_temporal_parameters(prompt_lower):
    \"\"\"Dynamically calculates valid_time and lead_time_hours from prompt features relative to simulation date\"\"\"
    target_date = None
    
    if "day after tomorrow" in prompt_lower or "in 2 days" in prompt_lower:
        target_date = CURRENT_SIMULATED_TIME + timedelta(days=2)
    elif "tomorrow" in prompt_lower:
        target_date = CURRENT_SIMULATED_TIME + timedelta(days=1)
    elif "today" in prompt_lower:
        target_date = CURRENT_SIMULATED_TIME
    elif re.search(r"\\b(september|sep|october|oct|november|nov)\\s+(\\d+)\\b", prompt_lower):
        m_match = re.search(r"\\b(september|sep|october|oct|november|nov)\\s+(\\d+)\\b", prompt_lower)
        month_str = m_match.group(1)[:3]
        day = int(m_match.group(2))
        month_map = {'sep': 9, 'oct': 10, 'nov': 11}
        target_date = datetime(2026, month_map[month_str], day)
        
    hour = 12 # Default to noon if no time specified, as in original baseline
    
    time_match = re.search(r"\\b(?:at\\s+)?(\\d+)(?:\\:00)?\\s*(am|pm)?\\b", prompt_lower)
    if time_match:
        h = int(time_match.group(1))
        meridiem = time_match.group(2)
        if meridiem == 'pm' and h < 12:
            h += 12
        elif meridiem == 'am' and h == 12:
            h = 0
        elif not meridiem and h < 12 and h >= 1 and 'pm' in prompt_lower:
            h += 12
        hour = h

    if target_date is None:
        target_date = CURRENT_SIMULATED_TIME
        
    target_time = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
    
    # Lead time in hours from CURRENT_SIMULATED_TIME
    lead_time = int((target_time - CURRENT_SIMULATED_TIME).total_seconds() / 3600)
    
    # Must not be negative
    if lead_time < 0:
        lead_time = 0
        
    return target_time.strftime("%Y-%m-%d %H:%M:%S"), lead_time"""

search2 = """        prompt_lower = request.prompt.lower()

        # 1. Location Extraction & Geographic Resolution via Geopy
        extracted_area_name = extract_area_name(prompt_lower)
        mapped_lat, mapped_lon, loc_name = geocode_location(extracted_area_name)
        
        # 2. Date/Lead Time Boundary Injection
        valid_time_override = None
        if 'tomorrow' in prompt_lower:
            valid_time_override = '2026-09-05 12:00:00'
            lead_time = 24
        elif 'next monday' in prompt_lower:
            valid_time_override = '2026-09-07 12:00:00'
            lead_time = 72
        elif 'day after tomorrow' in prompt_lower:
            valid_time_override = '2026-09-06 12:00:00'
            lead_time = 48
        elif 'in 2 days' in prompt_lower:
            valid_time_override = '2026-09-06 12:00:00'
            lead_time = 48

        has_time_info = bool(re.search(r'\\b(2026|aug|august|time|hour|h|hr|-08-|26th|today)\\b', prompt_lower))

        injections = []
        if mapped_lat is not None and mapped_lon is not None:
            area_display = loc_name.split(',')[0] if loc_name else extracted_area_name.title()
            injections.append(f"[System override: The user is asking about {area_display}. Use lat {mapped_lat:.4f}, lon {mapped_lon:.4f} for your tool calls. CRITICAL: In your final response, refer to the location ONLY by its name \\"{area_display}\\". Do not mention the latitude and longitude.]")

        if valid_time_override:
            injections.append(f"[System override: The user requested a relative future date. Translating to valid_time '{valid_time_override}' with lead_time_hours {lead_time} based on the current date 2026-09-04.]")
        elif not has_time_info and 'tomorrow' not in prompt_lower and 'next' not in prompt_lower:
            injections.append("[System override: Default to valid_time '2026-09-04 12:00:00' with lead_time_hours 12]")

        enriched_prompt = request.prompt
        if injections:
            enriched_prompt += " " + " ".join(injections)

        logger.info(f"AETHER query (Enriched): {enriched_prompt}")

        # Process the query through AETHER
        reply = aether_assistant.run_interaction(enriched_prompt)

        logger.info(f"AETHER response: {reply[:100]}...")"""

repl2 = """        prompt_lower = request.prompt.lower()
        logger.info(f"1. AETHER parsed intent/location/time from: '{request.prompt}'")

        # 1. Location Extraction & Geographic Resolution via Geopy
        extracted_area_name = extract_area_name(prompt_lower)
        
        injections = []
        if extracted_area_name:
            mapped_lat, mapped_lon, loc_name = geocode_location(extracted_area_name)
            
            if mapped_lat is not None and mapped_lon is not None:
                # 2. Date/Lead Time Dynamic Resolution
                vt_str, lead_hours = resolve_temporal_parameters(prompt_lower)
                
                area_display = loc_name.split(',')[0] if loc_name else extracted_area_name.title()
                
                # Insert BOTH patterns required by AETHER's lat_lon_match and vt_match regex rules
                injections.append(f"[System override: The user is asking about {area_display}. Use lat {mapped_lat:.4f}, lon {mapped_lon:.4f} for your tool calls. CRITICAL: In your final response, refer to the location ONLY by its name \\"{area_display}\\". Do not mention the latitude and longitude.]")
                injections.append(f"[System override: The user requested a specific time. Translating to valid_time '{vt_str}' with lead_time_hours {lead_hours}]")
        
        enriched_prompt = request.prompt
        if injections:
            enriched_prompt += " " + " ".join(injections)

        logger.info(f"2. ForecastingEngine execution prepared via AETHER override.")
        
        # Process the query through AETHER (which will then natively invoke ForecastingEngine)
        reply = aether_assistant.run_interaction(enriched_prompt)

        logger.info(f"5. External Gemini response obtained.")"""

if search1 in text:
    text = text.replace(search1, repl1)
else:
    print("Could not find search1")

if search2 in text:
    text = text.replace(search2, repl2)
else:
    print("Could not find search2")

with open('/home/agasthya/ai models/api_reference.py', 'w') as f:
    f.write(text)
