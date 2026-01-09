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

IMPORTANT: Each episode must have TWO numbers:
- episode_in_season: The episode number within its season (resets to 1 for each season)
- overall_episode_number: The absolute episode number across all seasons (continues counting)

Example extraction from this markdown:
```
Sezon 1:
Nr | Tytuł | Premiera | Oglądalność
1 | _[Spadek]_ | 05.03.2006 | 4 396 564
2 | _[Goście z zaświatów]_ | 12.03.2006 | 4 308 423

Sezon 2:
Nr | Tytuł | Premiera | Oglądalność
14 | _[Sztuka i władza]_ | 18.03.2007 | 6 993 951
15 | _[Gmina to ja]_ | 25.03.2007 | 6 754 211
```

Should produce:
{
  "seasons": [
    {
      "season_number": 1,
      "episodes": [
        {"episode_in_season": 1, "overall_episode_number": 1, "title": "Spadek", "premiere_date": "05.03.2006", "viewership": "4396564"},
        {"episode_in_season": 2, "overall_episode_number": 2, "title": "Goście z zaświatów", "premiere_date": "12.03.2006", "viewership": "4308423"}
      ]
    },
    {
      "season_number": 2,
      "episodes": [
        {"episode_in_season": 1, "overall_episode_number": 14, "title": "Sztuka i władza", "premiere_date": "18.03.2007", "viewership": "6993951"},
        {"episode_in_season": 2, "overall_episode_number": 15, "title": "Gmina to ja", "premiere_date": "25.03.2007", "viewership": "6754211"}
      ]
    }
  ]
}

Return ONLY valid JSON. Extract ONLY what you see, do NOT invent data."""
