
---
# 📝 Pełna Lista Komend

## 🚀 Skróty Komend

- **`/start`**: 👋 Uruchamia główne menu.
- **`/klip <cytat>`** / **`/k <cytat>`**: 🎥 Wyszukiwanie klipu.
- **`/szukaj <cytat>`** / **`/sz <cytat>`**: 🔍 Znalezienie klipów.
- **`/lista`** / **`/l`**: 📋 Lista klipów.
- **`/wybierz <numer_klipu>`** / **`/w <numer_klipu>`**: 🎯 Wybór klipu.
- **`/odcinki <sezon>`** / **`/o <sezon>`**: 🎞️ Lista odcinków.
- **`/wytnij <sezon_odcinek> <czas_start> <czas_koniec>`**: ✂️ Wycinanie klipu.
- **`/dostosuj <przedłużenie_przed> <przedłużenie_po>`** / **`/d <przedłużenie_przed> <przedłużenie_po>`**: ⏳ Dostosowanie klipu.
- **`/snap`** / **`/dopasuj`** / **`/sp`**: 🎯 Wyrównanie ostatniego klipu do cięć scen.
- **`/transkrypcja <cytat>`** / **`/t <cytat>`**: 📝 Transkrypcja z kontekstem dla cytatu.
- **`/kompiluj wszystko`** / **`/kom wszystko`**: 🎬 Kompilacja wszystkich klipów.
- **`/kompiluj <zakres>`** / **`/kom <zakres>`**: 🎬 Kompilacja z zakresu klipów.
- **`/kompiluj <numer_klipu1> <numer_klipu2> ...`** / **`/kom <numer_klipu1> <numer_klipu2> ...`**: 🎬 Kompilacja z wybranych klipów.
- **`/zapisz <nazwa>`** / **`/z <nazwa>`**: 💾 Zapisanie klipu.
- **`/mojeklipy`** / **`/mk`**: 📂 Twoje klipy.
- **`/wyslij <nazwa>`**/ **`/wys <nazwa>`**: 📤 Wysyłanie klipu.
- **`/usunklip <nazwa_klipu>`**/ **`/uk <nazwa_klipu>`**: 🗑️ Usunięcie klipu.
- **`/admin`**: 🔧 Polecenia administracyjne.
- **`/addwhitelist <id>`**/ **`/addw <id>`**: 📝 Dodanie do listy dozwolonych.
- **`/removewhitelist <id>`**/ **`/rmw <id>`**: 🚫 Usunięcie z listy dozwolonych.
- **`/listwhitelist`**/ **`/lw`**: 📄 Lista dozwolonych.
- **`/listadmins`**/ **`/la`**: 🛡️ Lista administratorów.
- **`/listmoderators`**/ **`/lm`**: 🛡️ Lista moderatorów.
- **`/note <user_id> <note>`**: 🗒️ Dodanie notatki do użytkownika.
- **`/klucz <key_content>`**/ **`/klucz <key_content>`**: 🔑 Użycie klucza subskrypcyjnego.
- **`/listkey`**/ **`/lk`**: 🔑 Lista kluczy subskrypcyjnych.
- **`/addkey <days> <note>`**/ **`/addk <days> <note>`**: 🔑 Tworzenie nowego klucza subskrypcyjnego.
- **`/removekey <key>`** / **`/rmk <key>`**: 🚫 Usuwanie klucza subskrypcyjnego.
- **`/report <issue_description>`** / **`/r <issue_description>`**: ⚠️ Zgłaszanie problemu.
- **`/serial <nazwa_serialu>`** / **`/ser <nazwa_serialu>`**: 📺 Zmiana aktywnego serialu.
- **`/reindex`** / **`/rei`**: 🔄 Reindeksowanie danych serialu.
- **`/postacie`** / **`/characters`** / **`/p`**: 👤 Przeglądanie postaci i scen.
- **`/emocje`** / **`/emotion`** / **`/e`**: 😊 Lista dostępnych emocji.
- **`/obiekt`** / **`/object`** / **`/obj`**: 🎯 Przeglądanie scen z obiektami.
- **`/objl`** / **`/obj_lista`**: 🎯 Pełna lista obiektów lub scen (jako dokument).

## 👥 Podstawowe Komendy Użytkownika

- **`/start`**/ **`/s`**: 👋 Wyświetla wiadomość powitalną z podstawowymi komendami.
- **`/klip <cytat>`**/ **`/k <cytat>`**: 🎥 Wyszukuje klip na podstawie cytatu. Przykład: `/klip geniusz`.
- **`/szukaj <cytat>`**/ **`/sz <cytat>`**: 🔍 Znajduje klipy pasujące do cytatu (pierwsze 5 wyników). Przykład: `/szukaj kozioł`.
- **`/lista`**/ **`/l`**: 📋 Wyświetla wszystkie klipy znalezione przez `/szukaj`.
- **`/wybierz <numer_klipu>`**/ **`/w <numer_klipu>`**: 🎯 Wybiera klip z listy uzyskanej przez `/szukaj`**do dalszych operacji. Przykład: `/wybierz 1`.
- **`/odcinki <sezon>`**/ **`/o <sezon>`**: 🎞️ Wyświetla listę odcinków dla podanego sezonu. Przykład: `/odcinki 2`.
- **`/wytnij <sezon_odcinek> <czas_start> <czas_koniec>`**: ✂️ Wycina fragment klipu. Przykład: `/wytnij S02E10 20:30.11 21:32.50`.
- **`/dostosuj <przedłużenie_przed> <przedłużenie_po>`**/ **`/d <przedłużenie_przed> <przedłużenie_po>`**: ⏳ Dostosowuje wybrany klip, rozszerzając czas rozpoczęcia i zakończenia. Przykład: `/dostosuj -5.5 1.2`.
- **`/snap`**/ **`/dopasuj`**/ **`/sp`**: 🎯 Wyrównuje ostatni klip do najbliższych cięć scen. Bez zmiany → informuje.
- **`/transkrypcja <cytat>`**/ **`/t <cytat>`**: 📝 Wyświetla transkrypcję z kontekstem dla znalezionego cytatu. Przykład: `/transkrypcja geniusz`.
- **`/kompiluj wszystko`**/ **`/kom wszystko`**: 🎬 Tworzy kompilację ze wszystkich klipów.
- **`/kompiluj <zakres>`**/ **`/kom <zakres>`**: 🎬 Tworzy kompilację z zakresu klipów. Przykład: `/kompiluj 1-4`.
- **`/kompiluj <numer_klipu1> <numer_klipu2> ...`**/ **`/kom <numer_klipu1> <numer_klipu2> ...`**: 🎬 Tworzy kompilację z wybranych klipów. Przykład: `/kompiluj 1 5 7`.
- **`/zapisz <nazwa>`**/ **`/z <nazwa>`**: 💾 Zapisuje wybrany klip z podaną nazwą. Przykład: `/zapisz moj_klip`.
- **`/mojeklipy`**/ **`/mk`**: 📂 Wyświetla listę zapisanych klipów.
- **`/wyslij <nazwa>`**/ **`/wys <nazwa>`**: 📤 Wysyła zapisany klip o podanej nazwie. Przykład: `/wyslij moj_klip`.
- **`/usunklip <nazwa_klipu>`**/ **`/uk <nazwa_klipu>`**: 🗑️ Usuwa zapisany klip o podanej nazwie. Przykład: `/uk moj_klip`.
- **`/postacie`** / **`/p`**: 👤 Wyświetla listę wszystkich postaci z liczbą odcinków.
- **`/postacie <nazwa_postaci>`** / **`/p <nazwa_postaci>`**: 👤 Wyświetla sceny z daną postacią. Przykład: `/postacie Wilkowyska`.
- **`/postacie <nazwa_postaci> <emocja>`** / **`/p <nazwa_postaci> <emocja>`**: 👤 Sceny z postacią i emocją. Przykład: `/postacie Wilkowyska happy` lub `/p Wilkowyska radosny`.
- **`/emocje`** / **`/e`**: 😊 Wyświetla listę dostępnych emocji (po polsku).
- **`/obiekt`** / **`/obj`**: 🎯 Wyświetla listę wszystkich wykrytych obiektów (od najpopularniejszych).
- **`/obiekt <nazwa>`** / **`/obj <nazwa>`**: 🎯 Lista scen z danym obiektem, posortowana od scen z największą ilością. Przykład: `/obiekt dog`.
- **`/obiekt <nazwa> <filtr>`** / **`/obj <nazwa> <filtr>`**: 🎯 Lista scen z filtrem ilości. Przykład: `/obj dog >3` lub `/obj dog =2`.
- **`/objl`**: 🎯 Pełna lista wszystkich obiektów (jako dokument).
- **`/objl <nazwa>`**: 🎯 Pełna lista scen z danym obiektem (jako dokument).
- **`/objl <nazwa> <filtr>`**: 🎯 Pełna lista scen z filtrem (jako dokument).

## 🔧 Komendy Administracyjne

- **`/admin`**: 🔧 Wyświetla polecenia administratora.
- **`/addwhitelist <id>`**/ **`/addw <id>`**: 📝 Dodaje użytkownika do whitelisty. Przykład: `/addwhitelist 123456789`.
- **`/removewhitelist <id>`**/ **`/rmw <id>`**: 🚫 Usuwa użytkownika z whitelisty. Przykład: `/removewhitelist 123456789`.
- **`/listwhitelist`**/ **`/lw`**: 📄 Wyświetla listę wszystkich użytkowników na whiteliście.
- **`/listadmins`**/ **`/la`**: 🛡️ Wyświetla listę wszystkich administratorów.
- **`/listmoderators`**/ **`/lm`**: 🛡️ Wyświetla listę wszystkich moderatorów.
- **`/note <user_id> <note>`**: 🗒️ Dodaje lub aktualizuje notatkę dla użytkownika. Przykład: `/note 123456789 To jest notatka`.
- **`/klucz <key_content>`**/ **`/klucz <key_content>`**: 🔑 Używa klucza subskrypcyjnego. Przykład: `/klucz some

_secret_key`.
- **`/listkey`**/ **`/lk`**: 🔑 Wyświetla listę wszystkich kluczy subskrypcyjnych.
- **`/addkey <days> <note>`**/ **`/addk <days> <note>`**: 🔑 Tworzy nowy klucz subskrypcji na określoną liczbę dni. Przykład: `/addkey 30 "tajny_klucz"`.
- **`/removekey <key>`**/ **`/rmk <key>`**: 🚫 Usuwa istniejący klucz subskrypcji. Przykład: `/removekey some_secret_key`.
- **`/report <issue_description>`**/ **`/r <issue_description>`**: ⚠️ Zgłasza problem do administratorów.
- **`/serial <nazwa_serialu>`**/ **`/ser <nazwa_serialu>`**: 📺 Zmienia aktywny serial dla użytkownika. Przykład: `/serial ranczo`.
- **`/reindex`**/ **`/rei`**: 🔄 Reindeksuje dane aktualnie wybranego serialu (wymaga uprawnień administratora).

---
