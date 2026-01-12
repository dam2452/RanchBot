def get_admin_help_message() -> str:
    return """```🛠\u00A0Instrukcje\u00A0dla\u00A0admina\u00A0🛠

═════════════════════════════════
🔐 Zarządzanie użytkownikami: 🔐
═════════════════════════════════
➕ /addwhitelist <id> - Dodaje użytkownika do whitelisty. Przykład: /addwhitelist 123456789
➖ /removewhitelist <id> - Usuwa użytkownika z whitelisty. Przykład: /removewhitelist 123456789
📃 /listwhitelist - Wyświetla listę wszystkich użytkowników w whiteliście.
📃 /listadmins - Wyświetla listę wszystkich adminów.
📃 /listmoderators - Wyświetla listę wszystkich moderatorów.
🔑 /klucz <key_content> - Używa klucz dla użytkownika. Przykład: /klucz some_secret_key
🔑 /listkey - Wyświetla listę wszystkich kluczy.
🔑 /addkey <days> <note> - Tworzy nowy klucz subskrypcji na X dni. Przykład: /addkey 30 "tajny_klucz"
🚫 /removekey <key> - Usuwa istniejący klucz subskrypcji. Przykład: /removekey some_secret_key

═════════════════════════════════
💳 Zarządzanie subskrypcjami: 💳
═════════════════════════════════
➕ /addsubscription <id> <days> - Dodaje subskrypcję użytkownikowi na określoną liczbę dni. Przykład: /addsubscription 123456789 30
🚫 /removesubscription <id> - Usuwa subskrypcję użytkownika. Przykład: /removesubscription 123456789

══════════════════════════════════
🔍 Zarządzanie transkrypcjami: 🔍
══════════════════════════════════
🔍 /transkrypcja <cytat> - Wyszukuje cytat w transkrypcjach i zwraca kontekst. Przykład: /transkrypcja Nie szkoda panu tego pięknego gabinetu?

═════════════════════════
🔎 Dodatkowe komendy: 🔎
═════════════════════════
🛠 /admin skroty - Wyświetla skróty komend admina.
```"""


def get_message_sent_log_message(username: str) -> str:
    return f"Admin help message sent to user '{username}'."


def get_admin_shortcuts_message() -> str:
    return """```🛠\u00A0Skróty\u00A0Komend\u00A0Admina\u00A0🛠
═════════════════════
📋 Skróty admin 📋
═════════════════════
➕ /addw, /addwhitelist <id> - Dodaje użytkownika do whitelisty.\n
➖ /rmw, /removewhitelist <id> - Usuwa użytkownika z whitelisty.\n
📃 /lw, /listwhitelist - Wyświetla listę użytkowników w whiteliście.\n
📃 /la, /listadmins - Wyświetla listę adminów.\n
📃 /lm, /listmoderators - Wyświetla listę moderatorów.\n
🔑 /klucz, /key <key_content> - Zapisuje nowy klucz dla użytkownika.\n
🔑 /lk, /listkey - Wyświetla listę kluczy.\n
🔑 /addk, /addkey <days> <note> - Tworzy nowy klucz subskrypcji.\n
🚫 /rmk, /removekey <key> - Usuwa istniejący klucz subskrypcji.\n
➕ /addsub, /addsubscription <id> <days> - Dodaje subskrypcję użytkownikowi.\n
🚫 /rmsub, /removesubscription <id> - Usuwa subskrypcję użytkownika.\n
🔍 /t, /transkrypcja <cytat> - Wyszukuje cytat w transkrypcjach.\n
```"""
