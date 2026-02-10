"""Common JSON schemas used across prompts."""


def episode_metadata_schema() -> str:
    """Returns JSON schema for episode metadata."""
    return (
        '{\n'
        '  "title": str,\n'
        '  "description": str,\n'
        '  "summary": str,\n'
        '  "season": int or null,\n'
        '  "episode_number": int or null\n'
        '}'
    )
