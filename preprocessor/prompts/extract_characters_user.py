def get() -> str:
    return """I have scraped {num_sources} web page(s) about the TV series "{series_name}".

Please extract a COMPLETE list of ALL characters from "{series_name}" as JSON.

Here is the content from all sources combined:

{combined_content}

---
**FINAL INSTRUCTIONS:**
1. Analyze the content above.
2. Extract all characters.
3. **EXPAND** every single abbreviation (e.g., change "ks. prob." to "Ksiądz Proboszcz", "bp" to "Biskup", "kom." to "Komisarz").
4. **SANITIZE** the names: remove quotation marks, parentheses, actor names, and any non-letter symbols. The name field should look like a natural full name (Title + First Name + Last Name).
5. Output valid JSON."""
