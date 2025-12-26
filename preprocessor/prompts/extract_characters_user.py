def get() -> str:
    return """I have scraped {num_sources} web page(s) about the TV series "{series_name}".

Please extract a COMPLETE list of ALL characters from "{series_name}" - including main characters, supporting characters, recurring roles, and episodic appearances.

IMPORTANT: Expand ALL title abbreviations (ks. -> Ksiądz, dr -> Doktor, prof. -> Profesor, etc.). Do NOT use abbreviations in character names.

Here is the content from all sources combined:

{combined_content}

Please analyze the above content and extract ALL characters from "{series_name}" as JSON. Remember to expand all title abbreviations!"""
