# pylint: disable=duplicate-code
def get() -> str:
    return """You are merging episode information from multiple sources.
Create a single, accurate metadata entry by:
- Choosing the most complete and accurate title
- Combining descriptions into a coherent 1-2 sentence description
- Merging summaries into a comprehensive 3-5 sentence summary
- Using the most reliable season/episode numbers

Prefer longer, more detailed information when merging.

Return ONLY valid JSON matching this schema:
{
  "title": str,
  "description": str,
  "summary": str,
  "season": int or null,
  "episode_number": int or null
}"""
