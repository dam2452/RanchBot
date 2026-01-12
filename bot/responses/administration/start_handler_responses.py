def get_basic_message() -> str:
    return """```🐐\u00A0Witaj\u00A0w\u00A0RanczoKlipy!\u00A0🐐
════════════════════════
🔍 Podstawowe komendy 🔍
════════════════════════
🔎 /klip <cytat> - Wyszukuje klip na podstawie cytatu. Przykład: /klip geniusz.
🔔 /subskrypcja - Sprawdza stan Twojej subskrypcji.
📜 /start lista - Wyświetla pełną listę komend.
```"""


def get_list_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0-\u00A0Działy\u00A0Komend\u00A0🐐
══════════════════════════
🔍 Wyszukiwanie:
   👉 /start wyszukiwanie

✂️ Edycja:
   👉 /start edycja

📁 Zarządzanie:
   👉 /start zarzadzanie

🛠️ Raporty:
   👉 /start raportowanie

🔔 Subskrypcje:
   👉 /start subskrypcje

📜 Wszystkie:
   👉 /start wszystko

📋 Skróty:
   👉 /start skroty
══════════════════════════
```"""


def get_all_message() -> str:
    return """```🐐\u00A0Witaj\u00A0w\u00A0RanczoKlipy!\u00A0🐐
═════════════════════════════════════════
🔍 Wyszukiwanie i przeglądanie klipów 🔍
═════════════════════════════════════════
🔎 /klip <cytat> - Wyszukuje klip na podstawie cytatu. Przykład: /klip geniusz.
🔍 /szukaj <cytat> - Znajduje klipy pasujące do cytatu (pierwsze 5 wyników). Przykład: /szukaj kozioł.
📋 /lista - Wyświetla wszystkie klipy znalezione przez /szukaj.
✅ /wybierz <numer_klipu> - Wybiera klip z listy uzyskanej przez /szukaj do dalszych operacji. Przykład: /wybierz 1.
📺 /odcinki <sezon> - Wyświetla listę odcinków dla podanego sezonu. Przykład: /odcinki 2.
✂️ /wytnij <sezon_odcinek> <czas_start> <czas_koniec> - Wytnij fragment klipu. Przykład: /wytnij S07E06 36:47.50 36:49.00.

════════════════════
✂️ Edycja klipów ✂️
════════════════════
📏 /dostosuj <przedłużenie_przed> <przedłużenie_po> - Dostosowuje wybrany klip. Przykład: /dostosuj -5.5 1.2.
📏 /dostosuj <numer_klipu> <przedłużenie_przed> <przedłużenie_po> - Dostosowuje klip z wybranego zakresu. Przykład: /dostosuj 1 10.0 -3.
🎞️ /kompiluj wszystko - Tworzy kompilację ze wszystkich klipów.
🎞️ /kompiluj <zakres> - Tworzy kompilację z zakresu klipów. Przykład: /kompiluj 1-4.
🎞️ /kompiluj <numer_klipu1> <numer_klipu2> ... - Tworzy kompilację z wybranych klipów. Przykład: /kompiluj 1 5 7.

═════════════════════════════════════
📁 Zarządzanie zapisanymi klipami 📁
═════════════════════════════════════
💾 /zapisz <nazwa> - Zapisuje wybrany klip z podaną nazwą. Przykład: /zapisz traktor.\n
📂 /mojeklipy - Wyświetla listę zapisanych klipów.\n
📤 /wyslij <numer_klipu> - Wysyła zapisany klip o podanej nazwie. Przykład: /wyslij 1.\n
🔗 /polaczklipy <numer_klipu1> <numer_klipu2> ... - Łączy zapisane klipy w jeden. Numery klipów można znaleźć używając komendy /mojeklipy. Przykład: /polaczklipy 4 2 3.\n
🗑️ /usunklip <numer_klipu> - Usuwa zapisany klip o podanej nazwie. Przykład: /usunklip 2.\n

════════════════════════
🛠️ Raportowanie błędów ️
════════════════════════
🐛 /report - Raportuje błąd do administratora.

══════════════════
🔔 Subskrypcje 🔔
══════════════════
📊 /subskrypcja - Sprawdza stan Twojej subskrypcji.
```"""


def get_search_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Wyszukiwanie\u00A0klipów\u00A0🐐
════════════════════
🔍 Wyszukiwanie 🔍
════════════════════

🔎 /klip <cytat> - Wyszukuje klip na podstawie cytatu. Przykład: /klip geniusz.\n
🔍 /szukaj <cytat> - Znajduje klipy pasujące do cytatu (pierwsze 5 wyników). Przykład: /szukaj kozioł.\n
📋 /lista - Wyświetla wszystkie klipy znalezione przez /szukaj.\n
✅ /wybierz <numer_klipu> - Wybiera klip z listy uzyskanej przez /szukaj do dalszych operacji. Przykład: /wybierz 1.\n
📺 /odcinki <sezon> - Wyświetla listę odcinków dla podanego sezonu. Przykład: /odcinki 2.\n
✂️ /wytnij <sezon_odcinek> <czas_start> <czas_koniec> - Wytnij fragment klipu. Przykład: /wytnij S07E06 36:47.50 36:49.00.\n
```"""


def get_edit_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Edycja\u00A0klipów\u00A0🐐
════════════════════
✂️ Edycja klipów ✂️
════════════════════
📏 /dostosuj <przedłużenie_przed> <przedłużenie_po> - Dostosowuje wybrany klip. Przykład: /dostosuj -5.5 1.2.\n
📏 /dostosuj <numer_klipu> <przedłużenie_przed> <przedłużenie_po> - Dostosowuje klip z wybranego zakresu. Przykład: /dostosuj 1 10.0 -3.\n
🎞️ /kompiluj wszystko - Tworzy kompilację ze wszystkich klipów.\n
🎞️ /kompiluj <zakres> - Tworzy kompilację z zakresu klipów. Przykład: /kompiluj 1-4.\n
🎞️ /kompiluj <numer_klipu1> <numer_klipu2> ... - Tworzy kompilację z wybranych klipów. Przykład: /kompiluj 1 5 7.\n
```"""


def get_menagement_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Zarządzanie\u00A0zapisanymi\u00A0klipami\u00A0🐐
═════════════════════════════════════
📁 Zarządzanie zapisanymi klipami 📁
═════════════════════════════════════
💾 /zapisz <nazwa> - Zapisuje wybrany klip z podaną nazwą. Przykład: /zapisz traktor.\n
📂 /mojeklipy - Wyświetla listę zapisanych klipów.\n
📤 /wyslij <numer_klipu> - Wysyła zapisany klip o podanej nazwie. Przykład: /wyslij 1.\n
🔗 /polaczklipy <numer_klipu1> <numer_klipu2> ... - Łączy zapisane klipy w jeden. Numery klipów można znaleźć używając komendy /mojeklipy. Przykład: /polaczklipy 4 2 3.\n
🗑️ /usunklip <numer_klipu> - Usuwa zapisany klip o podanej nazwie. Przykład: /usunklip 2.\n
```"""


def get_reporting_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Raportowanie\u00A0błędów\u00A0🐐
════════════════════════
🛠️ Raportowanie błędów ️
════════════════════════
🐛 /report - Raportuje błąd do administratora.\n
```"""


def get_subscriptions_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Subskrypcje\u00A0🐐
══════════════════
🔔 Subskrypcje 🔔
══════════════════
📊 /subskrypcja - Sprawdza stan Twojej subskrypcji.\n
```"""


def get_shortcuts_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Skróty\u00A0komend\u00A0🐐
═════════════════════
📋 Skróty komend 📋
═════════════════════
🐐 /s, /start - Uruchamia główne menu.\n
🔎 /k, /klip - Wyszukuje klip na podstawie cytatu.\n
🔎 /sz, /szukaj - Wyszukuje klip na podstawie cytatu.\n
📋 /l, /lista - Wyświetla wszystkie klipy znalezione przez /szukaj.\n
✅ /w, /wybierz - Wybiera klip z listy uzyskanej przez /szukaj.\n
📺 /o, /odcinki - Wyświetla listę odcinków dla podanego sezonu.\n
✂️ /d, /dostosuj - Dostosowuje wybrany klip.\n
🎞️ /kom, /kompiluj - Tworzy kompilację klipów.\n
🔗 /pk, /polaczklipy - Łączy zapisane klipy w jeden.\n
🗑️ /uk, /usunklip - Usuwa zapisany klip.\n
📂 /mk, /mojeklipy - Wyświetla listę zapisanych klipów.\n
💾 /z, /zapisz - Zapisuje wybrany klip.\n
📤 /wys, /wyślij - Wysyła zapisany klip.\n
🐛 /r, /report - Raportuje błąd do administratora.\n
🔔 /sub, /subskrypcja - Sprawdza stan Twojej subskrypcji.\n
```"""


def get_invalid_command_message() -> str:
    return "❌ Niepoprawna komenda w menu startowym. Użyj /start, aby zobaczyć dostępne opcje. ❌"


def get_log_start_message_sent(username: str) -> str:
    return f"Start message sent to user '{username}'"


def get_log_received_start_command(username: str, content: str) -> str:
    return f"Received start command from user '{username}' with content: {content}"
