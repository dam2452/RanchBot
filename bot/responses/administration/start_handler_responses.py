from bot.responses.bot_response import BotResponse


def get_basic_message() -> str:
    return """```🐐 Witaj w RanczoKlipy! 🐐
════════════════════════
🔍 Podstawowe komendy 🔍
════════════════════════
🔎 /klip <cytat> - Wyszukuje klip na podstawie cytatu. Przykład: /klip geniusz.
📺 /serial - Zarządza aktywnym serialem (zmiana, lista dostępnych).
🔔 /subskrypcja - Sprawdza stan Twojej subskrypcji.
📜 /start lista - Wyświetla pełną listę komend.
```"""


def get_list_message() -> str:
    return """```🐐 RanczoKlipy - Działy Komend 🐐
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
    return """```🐐 Witaj w RanczoKlipy! 🐐
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
🧠 /sens <zapytanie> - Wyszukiwanie semantyczne po tekście. Przykład: /sens ucieczka od problemów.
🧠 /sensklatki <zapytanie> - Wyszukiwanie semantyczne po klatkach. Przykład: /sensklatki biesiada.
🧠 /sensodcinek <zapytanie> - Wyszukiwanie semantyczne po odcinkach. Przykład: /sensodcinek ślub.
🎬 /klipsens <zapytanie> - Wyszukuje semantycznie i wysyła klip. Przykład: /klipsens ucieczka.
👤 /postacie [postac] [emocja] - Przegladanie postaci i ich scen. Przyklad: /postacie Wilkowyska.
👤 /szukajpostac <postac> [emocja] - Lista scen z daną postacią (bez wysyłania klipu). Przykład: /szp Wilkowyska.
🎭 /klippostac <postac> [emocja] - Klip z daną postacią. Przykład: /klippostac Wilkowyska.
🎯 /szukajobiekt <obiekt> [filtr] - Lista scen z danym obiektem (bez wysyłania klipu). Przykład: /szo dog >3.
🎯 /klipobiekt <obiekt> - Klip z danym obiektem. Przykład: /klipobiekt dog.
😊 /emocje - Wyświetla listę dostępnych emocji.
🎯 /obiekt [obiekt] [filtr] - Sceny z danym obiektem, np. /obiekt dog >3.
🔎 /filtr <filtry> - Ustawia filtry wyszukiwania. Przykład: /filtr sezon:2 postac:Pawlak.
🔎 /filtr reset - Usuwa wszystkie aktywne filtry.
ℹ️ /filtr info - Wyświetla aktywne filtry.
🎬 /klipfiltr [cytat] - Klip na podstawie aktywnego filtra. Przykład: /kf wina wójta.
🔎 /szukajfiltr [cytat] - Lista scen na podstawie aktywnego filtra. Przykład: /szf wina wójta.
🖼️ /klatka [numer_wyniku] [klatka] - Klatka kluczowa jako obraz JPEG. Przykład: /klatka 2 ostatnia.

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

🎞️ /sdostosuj <n_przed> <n_po> - Rozszerza klip o podaną liczbę cięć scen. Przykład: /sdostosuj 1 2.
🎯 /snap - Wyrównuje ostatni klip do najbliższych cięć scen (bez zmiany → informuje).

🎞️ /kompiluj wszystko - Tworzy kompilację ze wszystkich klipów.
🎞️ /kompiluj <zakres> - Tworzy kompilację z zakresu klipów. Przykład: /kompiluj 1-4.
🎞️ /kompiluj <numer_klipu1> <numer_klipu2> ... - Tworzy kompilację z wybranych klipów. Przykład: /kompiluj 1 5 7.

═════════════════════════════════════
📁 Zarządzanie zapisanymi klipami 📁
═════════════════════════════════════
💾 /zapisz <nazwa> - Zapisuje wybrany klip z podaną nazwą. Przykład: /zapisz traktor.
💾 /zapisznumer <numer> [odstep_l odstep_p] <nazwa> - Zapisuje klip z wyników wyszukiwania po numerze. Przykład: /zn 2 moj_klip.
📂 /mojeklipy [serial] - Wyświetla listę zapisanych klipów.
📤 /wyslij <nazwa> - Wysyła zapisany klip o podanej nazwie. Przykład: /wyslij traktor.
🔗 /polaczklipy <numer1> <numer2> ... - Łączy zapisane klipy w jeden. Przykład: /polaczklipy 4 2 3.
🗑️ /usunklip <nazwa> - Usuwa zapisany klip o podanej nazwie. Przykład: /usunklip traktor.
🖼️ /klatkaklipu <nazwa_lub_numer> [klatka] - Klatka kluczowa z zapisanego klipu. Przykład: /kk traktor.
🔗 /link <kod> - Powiązuje konto Telegram z kontem REST. Przykład: /link abc123.
🔑 /kodkonta - Generuje kod do założenia konta REST API dla istniejącego konta Telegram.

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
    return """```🐐 RanczoKlipy Wyszukiwanie klipów 🐐
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
🧠 /sens <zapytanie> - Wyszukiwanie semantyczne po tekście. Przykład: /sens ucieczka od problemów.\n
🧠 /sensklatki <zapytanie> - Wyszukiwanie semantyczne po klatkach. Przykład: /sensklatki biesiada.\n
🧠 /sensodcinek <zapytanie> - Wyszukiwanie semantyczne po odcinkach. Przykład: /sensodcinek ślub.\n
🎬 /klipsens <zapytanie> - Wyszukuje semantycznie i wysyła klip. Przykład: /klipsens ucieczka.\n
👤 /postacie [postac] [emocja] - Przegladanie postaci i ich scen. Przyklad: /postacie Wilkowyska.\n
👤 /szukajpostac <postac> [emocja] - Lista scen z daną postacią (bez wysyłania klipu). Przykład: /szp Wilkowyska.\n
🎭 /klippostac <postac> [emocja] - Klip z daną postacią. Przykład: /klippostac Wilkowyska.\n
🎯 /szukajobiekt <obiekt> [filtr] - Lista scen z danym obiektem (bez wysyłania klipu). Przykład: /szo dog >3.\n
🎯 /klipobiekt <obiekt> - Klip z danym obiektem. Przykład: /klipobiekt dog.\n
😊 /emocje - Wyswietla liste dostepnych emocji.\n
🎯 /obiekt [obiekt] [filtr] - Sceny z danym obiektem, np. /obiekt dog >3.\n
🔎 /filtr <filtry> - Ustawia filtry wyszukiwania. Przykład: /filtr sezon:2 postac:Pawlak.\n
🔎 /filtr reset - Usuwa wszystkie aktywne filtry.\n
ℹ️ /filtr info - Wyświetla aktywne filtry.\n
🎬 /klipfiltr [cytat] - Klip na podstawie aktywnego filtra. Przykład: /kf wina wójta.\n
🔎 /szukajfiltr [cytat] - Lista scen na podstawie aktywnego filtra. Przykład: /szf wina wójta.\n
🖼️ /klatka [numer_wyniku] [klatka] - Klatka kluczowa jako obraz JPEG. Przykład: /klatka 2 ostatnia.\n
```"""


def get_edit_message() -> str:
    return """```🐐 RanczoKlipy Edycja klipów 🐐
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

🎞️ /sdostosuj <n_przed> <n_po> - Rozszerza klip o podaną liczbę cięć scen w każdą stronę. Przykład: /sdostosuj 1 2.
🎯 /snap - Wyrównuje ostatni klip do najbliższych cięć scen (bez zmiany → informuje).
🖼️ /klatka [numer_wyniku] [klatka] - Klatka kluczowa jako obraz JPEG. Przykład: /klatka 2 ostatnia.

🎞️ /kompiluj wszystko - Tworzy kompilację ze wszystkich klipów.
🎞️ /kompiluj <zakres> - Tworzy kompilację z zakresu klipów. Przykład: /kompiluj 1-4.
🎞️ /kompiluj <numer_klipu1> <numer_klipu2> ... - Tworzy kompilację z wybranych klipów. Przykład: /kompiluj 1 5 7.
```"""


def get_menagement_message() -> str:
    return """```🐐 RanczoKlipy Zarządzanie zapisanymi klipami 🐐
═════════════════════════════════════
📁 Zarządzanie zapisanymi klipami 📁
═════════════════════════════════════
💾 /zapisz <nazwa> - Zapisuje wybrany klip z podaną nazwą. Przykład: /zapisz traktor.\n
💾 /zapisznumer <numer> [odstep_l odstep_p] <nazwa> - Zapisuje klip z wyników wyszukiwania po numerze. Przykład: /zn 2 moj_klip.\n
📂 /mojeklipy [serial] - Wyświetla listę zapisanych klipów.\n
📤 /wyslij <nazwa> - Wysyła zapisany klip o podanej nazwie. Przykład: /wyslij traktor.\n
🔗 /polaczklipy <numer1> <numer2> ... - Łączy zapisane klipy w jeden. Przykład: /polaczklipy 4 2 3.\n
🗑️ /usunklip <nazwa> - Usuwa zapisany klip o podanej nazwie. Przykład: /usunklip traktor.\n
🖼️ /klatkaklipu <nazwa_lub_numer> [klatka] - Klatka kluczowa z zapisanego klipu. Przykład: /kk traktor.\n
🔗 /link <kod> - Powiązuje konto Telegram z kontem REST. Przykład: /link abc123.\n
🔑 /kodkonta - Generuje kod do założenia konta REST API dla istniejącego konta Telegram.\n
```"""


def get_reporting_message() -> str:
    return """```🐐 RanczoKlipy Raportowanie błędów 🐐
════════════════════════
🛠️ Raportowanie błędów ️
════════════════════════
🐛 /report - Raportuje błąd do administratora.\n
```"""


def get_subscriptions_message() -> str:
    return """```🐐 RanczoKlipy Subskrypcje 🐐
══════════════════
🔔 Subskrypcje 🔔
══════════════════
📊 /subskrypcja - Sprawdza stan Twojej subskrypcji.\n
🔑 /klucz <key_content> - Używa klucza subskrypcyjnego. Przykład: /klucz some_key.\n
```"""


def get_shortcuts_message() -> str:
    return """```🐐 RanczoKlipy Skróty komend 🐐
═════════════════════
📋 Skróty komend 📋
═════════════════════
🐐 /s, /start - Uruchamia główne menu.\n
🔎 /k, /klip - Wyszukuje klip na podstawie cytatu.\n
🔎 /sz, /szukaj - Wyszukuje klipy pasujące do cytatu.\n
📝 /t, /transkrypcja - Wyświetla transkrypcję z kontekstem.\n
📋 /l, /lista - Wyświetla wszystkie klipy znalezione przez /szukaj.\n
✅ /w, /wybierz - Wybiera klip z listy uzyskanej przez /szukaj.\n
📺 /o, /odcinki - Wyświetla listę odcinków dla podanego sezonu.\n
📺 /ser, /serial - Zarządza aktywnym serialem.\n
✂️ /d, /dostosuj - Dostosowuje wybrany klip (relatywnie).\n
✂️ /ad, /adostosuj - Dostosowuje wybrany klip (absolutnie).\n
✂️ /sd, /sdostosuj - Dostosowuje klip do granic scen.\n
🎯 /sp, /snap - Wyrównuje klip do cięć scen.\n
🎞️ /kom, /kompiluj - Tworzy kompilację klipów.\n
🔗 /pk, /polaczklipy - Łączy zapisane klipy w jeden.\n
🗑️ /uk, /usunklip - Usuwa zapisany klip.\n
📂 /mk, /mojeklipy - Wyświetla listę zapisanych klipów.\n
💾 /z, /zapisz - Zapisuje wybrany klip.\n
💾 /zn, /zapisznumer - Zapisuje klip z wyników wyszukiwania po numerze.\n
📤 /wys, /wyślij - Wysyła zapisany klip.\n
🧠 /sen, /sens - Wyszukiwanie semantyczne (tekst).\n
🧠 /sensk, /sensklatki - Wyszukiwanie semantyczne (klatki).\n
🧠 /senso, /sensodcinek - Wyszukiwanie semantyczne (odcinek).\n
🎬 /ks, /ksen, /klipsens - Wyszukuje semantycznie i wysyła klip.\n
👤 /p, /postacie - Przegladanie postaci i scen.\n
👤 /szp, /szukajpostac - Lista scen z daną postacią.\n
🎭 /kp, /klippostac - Klip z daną postacią.\n
🎯 /szo, /szukajobiekt - Lista scen z danym obiektem.\n
🎯 /ko, /klipobiekt - Klip z danym obiektem.\n
😊 /e, /emocje - Lista dostepnych emocji.\n
🎯 /obj, /obiekt - Przegladanie scen z obiektami.\n
🎯 /objl - Pelna lista obiektow lub scen.\n
👤 /pl, /postacie_lista - Pelna lista postaci lub scen.\n
🔎 /f, /filtr - Ustawia filtry wyszukiwania.\n
🎬 /kf, /klipfiltr - Klip na podstawie aktywnego filtra.\n
🔎 /szf, /szukajfiltr - Lista scen na podstawie aktywnego filtra.\n
🖼️ /kl, /klatka - Klatka kluczowa z ostatniego klipu.\n
🖼️ /kk, /klatkaklipu - Klatka kluczowa z zapisanego klipu.\n
🔗 /link - Powiązuje konto Telegram z kontem REST.\n
🔑 /kodkonta - Generuje kod do założenia konta REST API.\n
🐛 /r, /report - Raportuje błąd do administratora.\n
🔔 /sub, /subskrypcja - Sprawdza stan Twojej subskrypcji.\n
```"""


def get_invalid_command_message() -> str:
    return BotResponse.error("NIEPOPRAWNA KOMENDA", "Niepoprawna komenda w menu startowym. Użyj /start, aby zobaczyć dostępne opcje")


def get_log_start_message_sent(username: str) -> str:
    return f"Start message sent to user '{username}'"


def get_log_received_start_command(username: str, content: str) -> str:
    return f"Received start command from user '{username}' with content: {content}"
