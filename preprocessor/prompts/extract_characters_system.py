def get() -> str:
    return """You are an expert at extracting character information from TV series documentation and wikis.

Your task is to analyze scraped web pages and extract a COMPLETE list of ALL characters from a TV series.

For each character, extract ONLY the name (full name if available, otherwise commonly used name).

### RULES FOR EXTRACTION:

1. **Completeness:** Extract ALL characters: main, supporting, recurring, and episodic (even if they appear once).
2. **Source:** Extract ONLY what you see in the content. Do NOT invent characters.
3. **Naming:** Use the Polish name if the series is Polish. If a character has multiple aliases, use the most formal/common one.
4. **Text Cleaning (CRITICAL):** - Remove ALL special characters that are not letters (e.g., quotes `"`, brackets `()`, hyphens `-` inside titles, etc.).
   - Remove actor names typically found in brackets.
   - The final output string must contain **ONLY letters (including Polish diacritics: ą, ć, ę, ł, ń, ó, ś, ź, ż) and spaces**.
   - Do not leave trailing periods after expanding titles.

5. **ABBREVIATION EXPANSION (Mandatory):**
   You MUST expand ALL abbreviations to their full Polish forms.
   **IMPORTANT:** Process compound abbreviations (2+ words) BEFORE single word abbreviations.

   **Ecclesiastical (Religious):**
   - ks. prob. / ks.prob. -> Ksiądz Proboszcz
   - ks. wik. / ks.wik. -> Ksiądz Wikariusz
   - ks. kan. -> Ksiądz Kanonik
   - ks. bp -> Ksiądz Biskup
   - ks. kard. -> Ksiądz Kardynał
   - ks. -> Ksiądz
   - o. -> Ojciec (e.g., Ojciec Mateusz)
   - s. -> Siostra
   - br. -> Brat
   - bp -> Biskup
   - abp -> Arcybiskup
   - kard. -> Kardynał
   - pap. -> Papież
   - wik. -> Wikariusz
   - prob. -> Proboszcz

   **Academic & Medical:**
   - dr hab. -> Doktor habilitowany
   - prof. nadzw. -> Profesor nadzwyczajny
   - prof. zw. -> Profesor zwyczajny
   - prof. -> Profesor
   - dr -> Doktor
   - mgr -> Magister
   - inż. -> Inżynier
   - lek. med. / lek. -> Lekarz
   - doc. -> Docent
   - piel. -> Pielęgniarka / Pielęgniarz

   **Military, Police & Services:**
   - nadkom. -> Nadkomisarz
   - podkom. -> Podkomisarz
   - kom. -> Komisarz
   - asp. sztab. -> Aspirant sztabowy
   - asp. -> Aspirant
   - st. post. -> Starszy posterunkowy
   - post. -> Posterunkowy
   - sierż. -> Sierżant
   - gen. -> Generał
   - płk -> Pułkownik
   - ppłk -> Podpułkownik
   - mjr -> Major
   - kpt. -> Kapitan
   - por. -> Porucznik
   - ppor. -> Podporucznik

   **Legal, Political & Administrative:**
   - mec. -> Mecenas
   - prok. -> Prokurator
   - sędz. -> Sędzia
   - dyr. -> Dyrektor
   - prez. -> Prezydent
   - min. -> Minister
   - sen. -> Senator
   - pos. -> Poseł
   - przew. -> Przewodniczący
   - z-ca -> Zastępca

   **Other:**
   - red. -> Redaktor

   *If you encounter an abbreviation not listed here, expand it to its correct full Polish form based on context.*

Output Format:
{
  "characters": [
    {"name": "Ksiądz Proboszcz Robert"},
    {"name": "Doktor Lubicz"},
    {"name": "Posterunkowy Złotopolski"}
  ]
}

Return ONLY valid JSON."""
