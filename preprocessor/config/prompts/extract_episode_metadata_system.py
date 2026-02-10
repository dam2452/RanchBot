from preprocessor.config.prompts.common_schemas import episode_metadata_schema


def get() -> str:
    return (
        'Extract episode information from the provided web page content.\n'
        'Focus on finding:\n'
        '- Episode title (exact title, not description)\n'
        '- Episode description (1-2 sentences summarizing the plot)\n'
        '- Episode summary (detailed summary, 3-5 sentences)\n'
        '- Season number (if mentioned)\n'
        '- Episode number (if mentioned)\n\n'
        'If information is missing, use empty string for text fields and null '
        'for numbers.\n'
        'Be precise and extract only factual information from the text.\n\n'
        f'Return ONLY valid JSON matching this schema:\n{episode_metadata_schema()}'
    )
