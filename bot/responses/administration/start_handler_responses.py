from bot.responses.bot_response import BotResponse


def get_basic_message() -> str:
    return """```🐐\u00A0Witaj\u00A0w\u00A0RanczoKlipy!\u00A0🐐
════════════════════════
🔍 Podstawowe komendy 🔍
════════════════════════
🔎 /klip <cytat> - Wyszukuje klip na podstawie cytatu. Przykład: /klip geniusz.
📺 /serial - Zarządza aktywnym serialem (zmiana, lista dostępnych).
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
📺 /serial - Zarządza aktywnym serialem (zmiana, lista dostępnych).
✂️ /wytnij <sezon_odcinek> <czas_start> <czas_koniec> - Wytnij fragment klipu. Przykład: /wytnij S07E06 36:47.50 36:49.00.
📝 /transkrypcja <cytat> - Wyświetla transkrypcję z kontekstem dla znalezionego cytatu. Przykład: /transkrypcja geniusz.

════════════════════
✂️ Edycja klipów ✂️
════════════════════
📏 /dostosuj [numer_klipu] <przed> <po> - Dostosowuje klip RELATYWNIE.
   -> Działa względem *ostatniego stanu* klipu, uwzględniając poprzednie cięcia.
   Przykład 1: /dostosuj -1.5 2.0 (dla wybranego klipu)
   Przykład 2: /dostosuj 3 0.5 -0.2 (dla klipu nr 3 z listy)

📏 /adostosuj [numer_klipu] <przed> <po> - Dostosowuje klip ABSOLUTNIE.
   -> Działa *zawsze* względem *pierwotnej, oryginalnej wersji* klipu.
   Przykład 1: /adostosuj -5.5 1.2 (dla wybranego klipu)
   Przykład 2: /adostosuj 1 10.0 -3 (dla klipu nr 1 z listy)

🎯 /snap - Wyrównuje ostatni klip do najbliższych cięć scen (bez zmiany → informuje).

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
👤 /postacie [postac] [emocja] - Przegladanie postaci i ich scen.
😊 /emocje - Lista dostepnych emocji.

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
📺 /serial - Zarządza aktywnym serialem (zmiana, lista dostępnych).\n
✂️ /wytnij <sezon_odcinek> <czas_start> <czas_koniec> - Wytnij fragment klipu. Przykład: /wytnij S07E06 36:47.50 36:49.00.\n
📝 /transkrypcja <cytat> - Wyświetla transkrypcję z kontekstem dla znalezionego cytatu. Przykład: /transkrypcja geniusz.\n
👤 /postacie [postac] [emocja] - Przegladanie postaci i ich scen. Przyklad: /postacie Wilkowyska.\n
😊 /emocje - Wyswietla liste dostepnych emocji.\n
```"""


def get_edit_message() -> str:
    return """```🐐\u00A0RanczoKlipy\u00A0Edycja\u00A0klipów\u00A0🐐
════════════════════
✂️ Edycja klipów ✂️
════════════════════
📏 /dostosuj [numer_klipu] <przed> <po> - Dostosowuje klip RELATYWNIE.
   -> Działa względem *ostatniego stanu* klipu, uwzględniając poprzednie cięcia.
   Przykład 1: /dostosuj -1.5 2.0 (dla wybranego klipu)
   Przykład 2: /dostosuj 3 0.5 -0.2 (dla klipu nr 3 z listy)

📏 /adostosuj [numer_klipu] <przed> <po> - Dostosowuje klip ABSOLUTNIE.
   -> Działa *zawsze* względem *pierwotnej, oryginalnej wersji* klipu.
   Przykład 1: /adostosuj -5.5 1.2 (dla wybranego klipu)
   Przykład 2: /adostosuj 1 10.0 -3 (dla klipu nr 1 z listy)

🎯 /snap - Wyrównuje ostatni klip do najbliższych cięć scen (bez zmiany → informuje).

🎞️ /kompiluj wszystko - Tworzy kompilację ze wszystkich klipów.
🎞️ /kompiluj <zakres> - Tworzy kompilację z zakresu klipów. Przykład: /kompiluj 1-4.
🎞️ /kompiluj <numer_klipu1> <numer_klipu2> ... - Tworzy kompilację z wybranych klipów. Przykład: /kompiluj 1 5 7.
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
📝 /t, /transkrypcja - Wyświetla transkrypcję z kontekstem.\n
📋 /l, /lista - Wyświetla wszystkie klipy znalezione przez /szukaj.\n
✅ /w, /wybierz - Wybiera klip z listy uzyskanej przez /szukaj.\n
📺 /o, /odcinki - Wyświetla listę odcinków dla podanego sezonu.\n
📺 /ser, /serial - Zarządza aktywnym serialem.\n
✂️ /d, /dostosuj - Dostosowuje wybrany klip (relatywnie).\n
✂️ /ad, /adostosuj - Dostosowuje wybrany klip (absolutnie).\n
🎯 /sp, /snap - Wyrównuje klip do cięć scen.\n
🎞️ /kom, /kompiluj - Tworzy kompilację klipów.\n
🔗 /pk, /polaczklipy - Łączy zapisane klipy w jeden.\n
🗑️ /uk, /usunklip - Usuwa zapisany klip.\n
📂 /mk, /mojeklipy - Wyświetla listę zapisanych klipów.\n
💾 /z, /zapisz - Zapisuje wybrany klip.\n
📤 /wys, /wyślij - Wysyła zapisany klip.\n
👤 /p, /postacie - Przegladanie postaci i scen.\n
😊 /e, /emocje - Lista dostepnych emocji.\n
🐛 /r, /report - Raportuje błąd do administratora.\n
🔔 /sub, /subskrypcja - Sprawdza stan Twojej subskrypcji.\n
```"""


def get_invalid_command_message() -> str:
    return BotResponse.error("NIEPOPRAWNA KOMENDA", "Niepoprawna komenda w menu startowym. Użyj /start, aby zobaczyć dostępne opcje")


def get_log_start_message_sent(username: str) -> str:
    return f"Start message sent to user '{username}'"


def get_log_received_start_command(username: str, content: str) -> str:
    return f"Received start command from user '{username}' with content: {content}"
