from preprocessor.config.prompts.common_schemas import episode_metadata_schema


def get() -> str:
    return (
        'You are merging episode information from multiple sources.\n'
        'Create a single, accurate metadata entry by:\n'
        '- Choosing the most complete and accurate title\n'
        '- Combining descriptions into a coherent 1-2 sentence description\n'
        '- Merging summaries into a comprehensive 3-5 sentence summary\n'
        '- Using the most reliable season/episode numbers\n\n'
        'Prefer longer, more detailed information when merging.\n\n'
        f'Return ONLY valid JSON matching this schema:\n{episode_metadata_schema()}'
    )
