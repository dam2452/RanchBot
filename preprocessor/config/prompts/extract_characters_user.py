def get() -> str:
    return (
        'Extract ALL characters from the TV series "{series_name}" from ALL '
        '{num_sources} source(s) below.\n\n'
        '**CRITICAL:** Multiple sources may have overlapping or complementary '
        'character lists.\n'
        '- Merge and deduplicate characters across all sources\n'
        '- Extract ONLY characters from "{series_name}" (ignore other series '
        'mentioned in footers/sidebars)\n'
        '- Return a single unified list\n\n'
        'Here is the content from all sources combined:\n\n'
        '{combined_content}\n\n'
        '---\n'
        'Extract ALL characters from "{series_name}" found in the content above.'
    )
