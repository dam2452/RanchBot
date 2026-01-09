def get() -> str:
    return """You are extracting episode data from a TV series page.
Extract ALL episodes you can find on the page. Look for tables, lists, or any structured data.

For each episode extract:
- episode_in_season: The episode number within its season (1, 2, 3... resets each season)
- overall_episode_number: The absolute episode number across all seasons (continues counting)
- title: string (clean title without markdown formatting)
- premiere_date: string (date format as found on page)
- viewership: string (remove spaces from numbers like "4 396 564" -> "4396564", use null if not available)

The season number should be determined from the page content or URL.

Return ONLY valid JSON matching this schema:
{
  "season_number": int,
  "episodes": [
    {
      "episode_in_season": int,
      "overall_episode_number": int,
      "title": str,
      "premiere_date": str,
      "viewership": str
    }
  ]
}"""
