def episode_metadata_schema() -> str:
    return (
        '{\n'
        '  "title": str,\n'
        '  "description": str,\n'
        '  "summary": str,\n'
        '  "season": int or null,\n'
        '  "episode_number": int or null\n'
        '}'
    )
