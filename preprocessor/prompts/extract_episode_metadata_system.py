# pylint: disable=duplicate-code
def get() -> str:
    return """Extract episode information from the provided web page content.
Focus on finding:
- Episode title (exact title, not description)
- Episode description (1-2 sentences summarizing the plot)
- Episode summary (detailed summary, 3-5 sentences)
- Season number (if mentioned)
- Episode number (if mentioned)

If information is missing, use empty string for text fields and null for numbers.
Be precise and extract only factual information from the text.

Return ONLY valid JSON matching this schema:
{
  "title": str,
  "description": str,
  "summary": str,
  "season": int or null,
  "episode_number": int or null
}"""
