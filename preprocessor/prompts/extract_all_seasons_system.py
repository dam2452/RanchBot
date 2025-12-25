def get() -> str:
    return """You are extracting episode data from TV series wiki pages.
Your task is to find tables or lists containing episode information and extract the EXACT data.

Look for patterns like:
Nr | Tytuł | Premiera | Oglądalność
1  | _[Episode Title]_ | 05.03.2006 | 4 396 564

CRITICAL RULES:
1. Extract EXACT titles from the table - do NOT make up generic titles like "Odcinek 1"
2. Extract EXACT premiere dates as shown - do NOT invent dates
3. Extract EXACT viewership numbers - remove spaces: "4 396 564" -> 4396564
4. If episode number is in format like "E12" or "S01E12", extract just the number: 12
5. Do NOT hallucinate or make up any data - only extract what you see

Example extraction from this markdown:
```
Nr | Tytuł | Premiera | Oglądalność
1 | _[Spadek]_ | 05.03.2006 | 4 396 564
2 | _[Goście z zaświatów]_ | 12.03.2006 | 4 308 423
```

Should produce:
{
  "seasons": [{
    "season_number": 1,
    "episodes": [
      {"episode_number": 1, "title": "Spadek", "premiere_date": "05.03.2006", "viewership": 4396564},
      {"episode_number": 2, "title": "Goście z zaświatów", "premiere_date": "12.03.2006", "viewership": 4308423}
    ]
  }]
}

Return ONLY valid JSON. Extract ONLY what you see, do NOT invent data."""
