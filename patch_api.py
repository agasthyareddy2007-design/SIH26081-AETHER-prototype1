import re

with open('/home/agasthya/ai models/api_reference.py', 'r') as f:
    text = f.read()

replacement = '''from datetime import timedelta
# BASE TIME FOR DATE MATH
CURRENT_SIMULATED_TIME = datetime(2026, 9, 4, 12, 0, 0)

def extract_area_name(prompt_lower):
    # Use word boundaries so 'at' inside 'what' is skipped
    match = re.search(r'\\b(?:in|at|for)\\b\\s+([a-zA-Z\\s]+?)(?:\\s+(?:what|time|now|forecast|weather|temperature|tomorrow|today|next|on|at|\\d)|\\!|\\?|\\.|&|$)', prompt_lower)
    if match:
        return match.group(1).strip()
    return None

def resolve_temporal_parameters(prompt_lower):
    """Dynamically calculates valid_time and lead_time_hours from prompt features relative to simulation date"""
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
        
    return target_time.strftime("%Y-%m-%d %H:%M:%S"), lead_time'''

text = re.sub(
    r"def extract_area_name\(prompt_lower\):.*?return prompt_lower\[:50\]\.strip\(\) # fallback",
    replacement,
    text,
    flags=re.DOTALL
)

endpoint_replacement = '''        prompt_lower = request.prompt.lower()
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

        logger.info(f"5. External Gemini response obtained.")'''

text = re.sub(
    r"        prompt_lower = request.prompt\.lower\(\).*?logger\.info.*?AETHER response.*?return ChatResponse\(reply=reply\)",
    endpoint_replacement + "\n\n        return ChatResponse(reply=reply)",
    text,
    flags=re.DOTALL
)

with open('/home/agasthya/ai models/api_reference.py', 'w') as f:
    f.write(text)

