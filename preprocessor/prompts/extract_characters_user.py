def get() -> str:
    return """Extract ALL characters from the TV series "{series_name}" from ALL {num_sources} source(s) below.

**CRITICAL:** Multiple sources may have overlapping or complementary character lists.
- Merge and deduplicate characters across all sources
- Extract ONLY characters from "{series_name}" (ignore other series mentioned in footers/sidebars)
- Return a single unified list

Here is the content from all sources combined:

{combined_content}

---
Extract ALL characters from "{series_name}" found in the content above."""
