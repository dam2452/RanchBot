# Ranczo Search - Przewodnik

Kompleksowe CLI do testowania wszystkich zebranych danych z Elasticsearch.

## Setup

Narzędzie search jest wbudowane w główny preprocessor CLI i używa tego samego środowiska Docker.

**Wymagania:**
1. Elasticsearch działa na `http://localhost:9200`
2. Indeksy `ranczo_*` zostały zaindeksowane (po uruchomieniu `run-all`)

## Funkcje

✅ **Full-text search** - wyszukiwanie w transkrypcjach (BM25)
✅ **Semantic text search** - wyszukiwanie po embedingach tekstowych (cosine similarity)
✅ **Semantic image search** - wyszukiwanie podobnych scen po obrazku
✅ **Character search** - wyszukiwanie po postaciach (wykrywanie twarzy)
✅ **Episode name search** - wyszukiwanie po nazwach odcinków (fuzzy + semantic)
✅ **Perceptual hash** - znajdowanie duplikatów klatek (pHash)
✅ **Scene context** - pokazuje kontekst scen (początek/koniec)
✅ **Filtry** - sezon, odcinek, postać
✅ **JSON output** - eksport wyników do JSON
✅ **Statystyki** - liczba dokumentów w każdym indeksie

---

## Quick Start

### Test podstawowy: statystyki
```bash
# Sprawdź liczbę dokumentów w każdym indeksie
./run-preprocessor.sh search --stats

# Lista wszystkich postaci z liczbą wystąpień
./run-preprocessor.sh search --list-characters
```

### Full-text search (BM25)
```bash
# Podstawowe wyszukiwanie
./run-preprocessor.sh search --text "Kto tu rządzi"

# Z limitem wyników
./run-preprocessor.sh search --text "Solejukowa" --limit 5

# Filtr po sezonie
./run-preprocessor.sh search --text "Lucy" --season 10

# Filtr po sezonie i odcinku
./run-preprocessor.sh search --text "partyzanci" --season 10 --episode 2

# Z większym limitem dla dokładniejszych wyników
./run-preprocessor.sh search --text "Wilska" --limit 50
```

### Semantic text search (embeddings)
```bash
# Wyszukiwanie semantyczne (rozumie kontekst, nie tylko słowa kluczowe)
./run-preprocessor.sh search --text-semantic "wesele"

# Wyszukiwanie emocji/atmosfery
./run-preprocessor.sh search --text-semantic "smutna scena"
./run-preprocessor.sh search --text-semantic "zabawna sytuacja"
./run-preprocessor.sh search --text-semantic "kłótnia"

# Z filtrem po sezonie
./run-preprocessor.sh search --text-semantic "romantyczna scena" --season 10

# Wyszukiwanie koncepcji (nie dosłownych słów)
./run-preprocessor.sh search --text-semantic "konflikt rodzinny"
./run-preprocessor.sh search --text-semantic "problemy finansowe"
```

### Semantic image search (video embeddings)
```bash
# Znajdź podobne sceny do obrazka
./run-preprocessor.sh search --image /input_data/screenshot.jpg

# Z większym limitem
./run-preprocessor.sh search --image /input_data/frame.png --limit 20

# Filtr po postaci (tylko sceny gdzie ta postać występuje)
./run-preprocessor.sh search --image /input_data/screenshot.jpg --character "Lucy"

# Filtr po sezonie
./run-preprocessor.sh search --image /input_data/frame.png --season 10 --limit 10

# Kombinacja: scena podobna do obrazka + postać + sezon
./run-preprocessor.sh search --image /input_data/shot.jpg --character "Solejukowa" --season 10
```

### Character search
```bash
# Wszystkie sceny z Lucy
./run-preprocessor.sh search --character "Lucy"

# Lucy tylko w sezonie 10
./run-preprocessor.sh search --character "Lucy" --season 10

# Z limitem
./run-preprocessor.sh search --character "Solejukowa" --limit 30

# Konkretny odcinek
./run-preprocessor.sh search --character "Wicek Wilski" --season 10 --episode 1
```

### Episode name search
```bash
# Fuzzy search po nazwach odcinków (toleruje błędy pisowni)
./run-preprocessor.sh search --episode-name "Spadek"
./run-preprocessor.sh search --episode-name "Wielkie wybory"

# Semantic search po nazwach odcinków (rozumie kontekst/znaczenie)
./run-preprocessor.sh search --episode-name-semantic "wesele"
./run-preprocessor.sh search --episode-name-semantic "wybory"

# Z filtrem po sezonie
./run-preprocessor.sh search --episode-name "Porwanie" --season 1

# Znajdź odcinki o podobnym tytule/temacie
./run-preprocessor.sh search --episode-name-semantic "święta" --limit 10
```

### Perceptual hash (duplikaty/podobne klatki)
```bash
# Znajdź klatki z takim samym hashem (duplikaty)
./run-preprocessor.sh search --hash "191b075b6d0363cf"

# Oblicz hash z obrazka i znajdź duplikaty
./run-preprocessor.sh search --hash /input_data/frame.jpg

# Przydatne do znajdowania:
# - duplikatów klatek
# - bardzo podobnych scen
# - tej samej klatki w różnych formatach
```

### Kombinowane zapytania
```bash
# Full-text + sezon + limit
./run-preprocessor.sh search --text "Solejukowa" --season 10 --limit 10

# Semantic search + sezon
./run-preprocessor.sh search --text-semantic "smutna scena" --season 10

# Image search + postać + sezon
./run-preprocessor.sh search --image /input_data/screenshot.jpg --character "Lucy" --season 10 --limit 15
```

### JSON output (dla integracji/skryptów)
```bash
# Statystyki w JSON
./run-preprocessor.sh search --stats --json-output

# Lista postaci w JSON
./run-preprocessor.sh search --list-characters --json-output

# Wyniki wyszukiwania w JSON
./run-preprocessor.sh search --text "test" --json-output

# Semantic search w JSON
./run-preprocessor.sh search --text-semantic "wesele" --json-output

# Do dalszego przetwarzania (np. jq)
./run-preprocessor.sh search --text "Lucy" --json-output | jq '.hits[] | {score: ._score, text: ._source.text}'
```

### Zmiana Elasticsearch host
```bash
# Dla zdalnego ES
./run-preprocessor.sh search --text "test" --host "http://192.168.1.100:9200"

# Dla ES z autentykacją
./run-preprocessor.sh search --text "test" --host "https://es.example.com:9200"
```

---

## Przykłady praktyczne

### Znalezienie konkretnej sceny
```bash
# Pamiętasz fragment dialogu
./run-preprocessor.sh search --text "Kto tu rządzi" --limit 3

# Pamiętasz temat/sytuację (semantic)
./run-preprocessor.sh search --text-semantic "awantura w kuchni" --limit 5

# Pamiętasz kto był w scenie
./run-preprocessor.sh search --character "Lucy" --season 10 --limit 20
```

### Analiza postaci
```bash
# Ile razy Lucy występuje
./run-preprocessor.sh search --list-characters | grep Lucy

# Wszystkie sceny Lucy w sezonie 10
./run-preprocessor.sh search --character "Lucy" --season 10 --limit 100

# Sceny Lucy + semantic search (emocje)
./run-preprocessor.sh search --text-semantic "smutna scena" --season 10
# (potem ręcznie sprawdź które mają Lucy)
```

### Znajdowanie duplikatów
```bash
# Oblicz hash pierwszego obrazka
./run-preprocessor.sh search --hash /input_data/frame1.jpg --limit 50

# Znajdź wszystkie identyczne klatki (duplikaty)
# Hash zostanie wyświetlony, skopiuj i użyj bezpośrednio
./run-preprocessor.sh search --hash "COMPUTED_HASH" --limit 100
```

---

## Format wyników

### Full-text search (`--text`)
```
[1] Score: 12.45
Episode: S10E01 - Pilot
Segment ID: 42
Time: 120.50s - 125.30s [Scene 12: 115.0s - 130.0s]
Speaker: Lucy Wilska
Text: Kto tu rządzi? No kto?
Path: /app/output_data/transcoded_videos/ranczo_S10E01.mp4
```

### Semantic text search (`--text-semantic`)
```
[1] Score: 1.85
Episode: S10E01 - Pilot
Segments: 0-4 [Scene 12: 115.0s - 130.0s]
Embedding ID: ranczo_S10E01_emb_0
Text: Lucy przyjeżdża do wsi. Spotyka Solejukową. Rozmowa o zagrodzie.
Path: /app/output_data/transcoded_videos/ranczo_S10E01.mp4
```

### Video/Image/Character search (`--image`, `--character`, `--hash`)
```
[1] Score: 1.92
Episode: S10E01 - Pilot
Frame: 3450 @ 115.0s [Scene 12: 115.0s - 130.0s]
Type: scene_start
Scene number: 12
Hash: 191b075b6d0363cf
Characters: Lucy Wilska, Solejukowa
Path: /app/output_data/transcoded_videos/ranczo_S10E01.mp4
```

**Wszystkie wyniki zawierają pełen kontekst:**
- **Score** - BM25 relevance (text) lub cosine similarity + 1.0 (semantic, zakres: 0-2)
- **Episode** - format S{season:02d}E{episode:02d} - tytuł odcinka
- **Scene context** - [Scene N: start - end] w sekundach (ZAWSZE, dla wszystkich trybów)
- **Path** - ścieżka do pliku video

**Dodatkowe pola według typu wyszukiwania:**

**Full-text (`--text`):**
- Segment ID - identyfikator segmentu transkrypcji
- Time - timestamp początek-koniec w sekundach
- Speaker - mówca (jeśli wykryty)
- Text - transkrypcja segmentu

**Semantic text (`--text-semantic`):**
- Segments - zakres segmentów (start-end)
- Embedding ID - identyfikator embeddingu
- Text - połączone transkrypcje z 5 segmentów

**Video/Image/Character (`--image`, `--character`, `--hash`):**
- Frame - numer klatki @ timestamp
- Type - typ klatki (scene_start, scene_middle, scene_end)
- Scene number - numer sceny w odcinku
- Hash - perceptual hash (16-znakowy hex, jeśli dostępny)
- Characters - lista wykrytych postaci (jeśli są)

### JSON output (`--json-output`)
Zwraca surowy obiekt `hits` z Elasticsearch:
```json
{
  "hits": [
    {
      "_score": 12.45,
      "_source": {
        "episode_id": "S10E01",
        "text": "...",
        ...
      }
    }
  ]
}
```

---

## Opcje CLI

### Wyszukiwanie (wymagana jedna z tych opcji)
- `--text TEXT` - full-text search po transkrypcjach
- `--text-semantic TEXT` - semantic search po text embeddings
- `--image PATH` - semantic search po video embeddings (ścieżka do obrazka w /input_data/)
- `--hash HASH_OR_PATH` - perceptual hash search (podaj hash string lub ścieżkę do obrazka)
- `--character NAME` - wyszukiwanie po postaci
- `--episode-name TEXT` - fuzzy search po nazwach odcinków
- `--episode-name-semantic TEXT` - semantic search po nazwach odcinków
- `--stats` - statystyki indeksów
- `--list-characters` - lista wszystkich postaci

### Filtry (opcjonalne, można łączyć)
- `--season N` - filtruj po sezonie (dostępne dla: text, text-semantic, image, character, episode-name, episode-name-semantic)
- `--episode N` - filtruj po odcinku (dostępne dla: text, text-semantic, image, character)
- `--character NAME` - filtruj po postaci (dostępne dla: image)
- `--limit N` - limit wyników (default: 20)

### Output
- `--json-output` - output w formacie JSON
- `--host URL` - Elasticsearch host (default: http://localhost:9200)

---

## Indeksy Elasticsearch

Narzędzie przeszukuje 4 indeksy:

### `ranczo_segments`
Segmenty transkrypcji (dokładne timestampy).

**Używane przez:** `--text`

**Kluczowe pola:**
- `text` (string) - transkrypcja segmentu
- `start_time`, `end_time` (float) - timestampy w sekundach
- `speaker` (string) - mówca
- `episode_metadata` (object) - sezon, odcinek, tytuł
- `scene_info` (object) - numer sceny, start/end sceny
- `video_path` (string) - ścieżka do pliku

### `ranczo_text_embeddings`
Embeddingi tekstowe (grupy 5 segmentów).

**Używane przez:** `--text-semantic`

**Kluczowe pola:**
- `text_embedding` (dense_vector, 768-dim) - embedding Qwen2-VL
- `text` (string) - połączone transkrypcje 5 segmentów
- `segment_range` (array) - [start_segment, end_segment]
- `episode_metadata` (object) - sezon, odcinek, tytuł
- `video_path` (string) - ścieżka do pliku

### `ranczo_video_embeddings`
Embeddingi video + perceptual hashes + wykryte postacie.

**Używane przez:** `--image`, `--character`, `--hash`

**Kluczowe pola:**
- `video_embedding` (dense_vector, 768-dim) - embedding Qwen2-VL
- `frame_number` (int) - numer klatki
- `timestamp` (float) - timestamp w sekundach
- `frame_type` (string) - typ klatki (scene_start, scene_middle, scene_end)
- `perceptual_hash` (keyword) - 16-znakowy hex hash
- `character_appearances` (keyword array) - wykryte postacie
- `scene_info` (object) - numer sceny, start/end sceny
- `episode_metadata` (object) - sezon, odcinek, tytuł
- `video_path` (string) - ścieżka do pliku

### `ranczo_episode_names`
Embeddingi nazw odcinków (fuzzy + semantic search po tytułach).

**Używane przez:** `--episode-name`, `--episode-name-semantic`

**Kluczowe pola:**
- `title` (text) - tytuł odcinka
- `title_embedding` (dense_vector, 768-dim) - embedding Qwen2-VL
- `episode_id` (keyword) - identyfikator odcinka (S01E01)
- `episode_metadata` (object) - sezon, odcinek, tytuł, data premiery
- `video_path` (string) - ścieżka do pliku

**Lokalizacja embeddings:** `output_data/embeddings/S{season:02d}/E{episode:02d}/episode_name_embedding.json`

**Sprawdź statystyki:** `./run-preprocessor.sh search --stats`

---

## Tryby wyszukiwania - szczegółowy opis

### 1. Full-text search (`--text`)

**Algorytm:** Elasticsearch BM25 z fuzzy matching

**Indeks:** `ranczo_segments`

**Przeszukuje:**
- Transkrypcje segmentów (pole `text`, waga x2)
- Tytuły odcinków (pole `episode_metadata.title`)

**Cechy:**
- Automatyczne fuzzy matching (tolerancja błędów pisowni)
- Wyszukiwanie dokładnych fraz
- Filtry: `--season`, `--episode`
- Domyślny limit: 20 wyników
- Score: BM25 relevance (im wyższy tym lepsze dopasowanie)

**Kiedy używać:**
- Pamiętasz dokładne słowa/frazę z dialogu
- Szukasz konkretnej wypowiedzi
- Chcesz znaleźć wszystkie wystąpienia słowa kluczowego
- Potrzebujesz dokładnych timestampów

**Przykłady:**
```bash
./run-preprocessor.sh search --text "Kto tu rządzi"
./run-preprocessor.sh search --text "Solejukowa" --season 10
./run-preprocessor.sh search --text "Wilska Lucy" --limit 30
```

### 2. Semantic text search (`--text-semantic`)

**Algorytm:** Cosine similarity na 768-wymiarowych embeddingach Qwen2-VL

**Indeks:** `ranczo_text_embeddings`

**Przeszukuje:**
- Grupy 5 segmentów transkrypcji (segment_range)
- Embeddingi tekstowe wygenerowane z kontekstu

**Cechy:**
- Rozumie znaczenie, nie tylko słowa kluczowe
- Wyszukiwanie koncepcji, emocji, sytuacji
- Działa nawet bez dokładnych słów z dialogu
- Filtry: `--season`, `--episode`
- Domyślny limit: 20 wyników
- Score: 0-2 (cosine similarity + 1.0, >1.5 = bardzo podobne)

**Kiedy używać:**
- Pamiętasz temat/sytuację, ale nie dokładne słowa
- Szukasz emocji/atmosfery sceny
- Chcesz znaleźć podobne konteksty
- Wyszukujesz koncepcje abstrakcyjne (np. "konflikt", "radość")

**Przykłady:**
```bash
./run-preprocessor.sh search --text-semantic "wesele"
./run-preprocessor.sh search --text-semantic "smutna scena"
./run-preprocessor.sh search --text-semantic "kłótnia rodzinna"
./run-preprocessor.sh search --text-semantic "problemy finansowe"
./run-preprocessor.sh search --text-semantic "przygotowania do święta"
```

### 3. Semantic image search (`--image`)

**Algorytm:** Cosine similarity na 768-wymiarowych embeddingach Qwen2-VL

**Indeks:** `ranczo_video_embeddings`

**Przeszukuje:**
- Embeddingi wygenerowane z klatek wideo
- Klatki wyeksportowane (scene_start, scene_middle, scene_end)

**Cechy:**
- Znajdź podobne sceny wizualnie
- Rozumie zawartość obrazu (obiekty, sceneria, kompozycja)
- Filtry: `--season`, `--episode`, `--character`
- Domyślny limit: 20 wyników
- Score: 0-2 (cosine similarity + 1.0)
- Wymaga pliku obrazka (JPG, PNG) w `/input_data/`

**Kiedy używać:**
- Masz screenshot i chcesz znaleźć podobne sceny
- Szukasz scen z podobnym wnętrzem/krajobrazem
- Chcesz znaleźć sceny z podobnym ujęciem kamery
- Wyszukujesz wizualnie podobne momenty

**Przykłady:**
```bash
./run-preprocessor.sh search --image /input_data/screenshot.jpg
./run-preprocessor.sh search --image /input_data/frame.png --character "Lucy"
./run-preprocessor.sh search --image /input_data/shot.jpg --season 10 --limit 15
```

**Uwaga:** Obrazek musi być w `preprocessor/input_data/` (volume kontener)

### 4. Character search (`--character`)

**Algorytm:** Exact match na wykrytych postaciach (InsightFace buffalo_l)

**Indeks:** `ranczo_video_embeddings`

**Przeszukuje:**
- Pole `character_appearances` (keyword array)
- Klatki z wykrytymi twarzami

**Cechy:**
- Wyszukiwanie po dokładnej nazwie postaci
- Case-sensitive (dokładna nazwa z characters.json)
- Filtry: `--season`, `--episode`
- Domyślny limit: 20 wyników
- Zwraca klatki gdzie postać została wykryta przez face recognition

**Kiedy używać:**
- Chcesz znaleźć wszystkie sceny z konkretną postacią
- Analizujesz występy postaci w serialu
- Szukasz scen gdzie postacie się spotykają
- Sprawdzasz w których odcinkach występuje postać

**Przykłady:**
```bash
./run-preprocessor.sh search --character "Lucy Wilska"
./run-preprocessor.sh search --character "Solejukowa" --season 10
./run-preprocessor.sh search --character "Wicek Wilski" --limit 50
```

**Uwaga:** Sprawdź dokładną nazwę: `./run-preprocessor.sh search --list-characters | grep -i lucy`

### 5. Perceptual hash (`--hash`)

**Algorytm:** Exact match na 16-znakowym perceptual hash (pHash, hash_size=8)

**Indeks:** `ranczo_video_embeddings`

**Przeszukuje:**
- Pole `perceptual_hash` (keyword)
- Hash obliczony z klatek wideo przez PerceptualHasher

**Cechy:**
- Znajdź dokładnie identyczne klatki (wizualnie)
- Może obliczyć hash z obrazka automatycznie
- Bardzo szybkie (exact match, nie similarity)
- Domyślny limit: 20 wyników
- Hash: 16-znakowy hex string (np. "191b075b6d0363cf")

**Kiedy używać:**
- Szukasz duplikatów klatek
- Sprawdzasz czy klatka już istnieje w bazie
- Znajdowanie tej samej sceny w różnych plikach
- Weryfikacja unikalności klatek

**Przykłady:**
```bash
# Podaj hash bezpośrednio
./run-preprocessor.sh search --hash "191b075b6d0363cf"

# Oblicz hash z obrazka
./run-preprocessor.sh search --hash /input_data/frame.jpg

# Znajdź wszystkie duplikaty
./run-preprocessor.sh search --hash "191b075b6d0363cf" --limit 100
```

### 6. Episode name search (`--episode-name`)

**Algorytm:** Elasticsearch BM25 z fuzzy matching

**Indeks:** `ranczo_episode_names`

**Przeszukuje:**
- Tytuły odcinków (pole `title`, waga x2)
- Tytuły odcinków w metadanych (pole `episode_metadata.title`)

**Cechy:**
- Automatyczne fuzzy matching (tolerancja błędów pisowni)
- Wyszukiwanie dokładnych nazw odcinków
- Filtry: `--season`
- Domyślny limit: 20 wyników
- Score: BM25 relevance

**Kiedy używać:**
- Pamiętasz nazwę odcinka (dokładną lub przybliżoną)
- Szukasz odcinka po tytule
- Chcesz znaleźć odcinek mimo błędu w pisowni
- Potrzebujesz znaleźć konkretny odcinek po nazwie

**Przykłady:**
```bash
./run-preprocessor.sh search --episode-name "Spadek"
./run-preprocessor.sh search --episode-name "Wielkie wybory"
./run-preprocessor.sh search --episode-name "Porwanie" --season 1
```

### 7. Episode name semantic search (`--episode-name-semantic`)

**Algorytm:** Cosine similarity na 768-wymiarowych embeddingach Qwen2-VL

**Indeks:** `ranczo_episode_names`

**Przeszukuje:**
- Embeddingi wygenerowane z tytułów odcinków
- Pole `title_embedding` (dense_vector 768-dim)

**Cechy:**
- Rozumie znaczenie i kontekst tytułów
- Znajduje odcinki o podobnej tematyce
- Działa nawet bez dokładnej nazwy
- Filtry: `--season`
- Domyślny limit: 20 wyników
- Score: 0-2 (cosine similarity + 1.0, >1.5 = bardzo podobne)

**Kiedy używać:**
- Pamiętasz temat odcinka, ale nie dokładny tytuł
- Szukasz odcinków o podobnej tematyce
- Chcesz znaleźć odcinki związane z konkretnym wydarzeniem
- Wyszukujesz odcinki po abstrakcyjnym opisie

**Przykłady:**
```bash
./run-preprocessor.sh search --episode-name-semantic "wesele"
./run-preprocessor.sh search --episode-name-semantic "wybory"
./run-preprocessor.sh search --episode-name-semantic "święta" --limit 10
./run-preprocessor.sh search --episode-name-semantic "konflikt" --season 10
```

### 8. Statystyki (`--stats`)

Wyświetla liczbę dokumentów w każdym indeksie.

**Indeksy:**
- `ranczo_segments` - segmenty transkrypcji
- `ranczo_text_embeddings` - embeddingi tekstowe
- `ranczo_video_embeddings` - embeddingi video + hashes + postacie
- `ranczo_episode_names` - embeddingi nazw odcinków

**Przykład:**
```bash
./run-preprocessor.sh search --stats
./run-preprocessor.sh search --stats --json-output
```

### 9. Lista postaci (`--list-characters`)

Wyświetla wszystkie wykryte postacie z liczbą wystąpień.

**Agregacja:** Elasticsearch terms aggregation na `character_appearances`

**Sortowanie:** Po liczbie wystąpień (malejąco)

**Przykład:**
```bash
./run-preprocessor.sh search --list-characters
./run-preprocessor.sh search --list-characters --json-output
```

---

## Dodatkowe przykłady praktyczne

### Eksploracja danych

#### Poznaj strukturę danych
```bash
# Statystyki
./run-preprocessor.sh search --stats

# Lista postaci
./run-preprocessor.sh search --list-characters

# Przykładowy wynik (sprawdź format)
./run-preprocessor.sh search --text "test" --limit 1
```

#### Eksport do analizy
```bash
# Wszystkie wystąpienia postaci do JSON
./run-preprocessor.sh search --character "Lucy Wilska" --limit 1000 --json-output > lucy_scenes.json

# Semantic search wyników do analizy
./run-preprocessor.sh search --text-semantic "wesele" --limit 50 --json-output > wedding_scenes.json

# Statystyki do CSV (przez jq)
./run-preprocessor.sh search --list-characters --json-output | \
  jq -r '.[] | "\(.[0]),\(.[1])"' > characters.csv
```

### Integracja z innymi narzędziami

#### jq (przetwarzanie JSON)
```bash
# Wyciągnij tylko teksty
./run-preprocessor.sh search --text "Lucy" --json-output | \
  jq '.hits[] | ._source.text'

# Wyciągnij score i tekst
./run-preprocessor.sh search --text-semantic "wesele" --json-output | \
  jq '.hits[] | {score: ._score, text: ._source.text}'

# Filtruj po score > 1.5
./run-preprocessor.sh search --text-semantic "romantyczna scena" --json-output | \
  jq '.hits[] | select(._score > 1.5)'
```

#### grep/awk (filtrowanie)
```bash
# Tylko sceny z konkretnym speakerem
./run-preprocessor.sh search --text "test" --limit 100 | grep "Speaker: Lucy"

# Policz ile razy postać występuje
./run-preprocessor.sh search --list-characters | grep "Lucy" | awk '{print $2}'
```

### Workflow: od screenshotu do analizy

```bash
# 1. Masz screenshot, chcesz znaleźć podobne sceny
cp ~/screenshot.jpg preprocessor/input_data/
./run-preprocessor.sh search --image /input_data/screenshot.jpg --limit 20

# 2. Znalazłeś ciekawą scenę, sprawdź co się działo
# Skopiuj timestamp z outputu (np. 115.0s) i znajdź transkrypcję
./run-preprocessor.sh search --text "test" --season 10 --episode 1 | grep "115"

# 3. Chcesz znaleźć podobne sceny emocjonalnie
./run-preprocessor.sh search --text-semantic "smutna scena" --season 10 --limit 10

# 4. Sprawdź które postacie były w tych scenach
./run-preprocessor.sh search --character "Lucy Wilska" --season 10 --limit 100
```

---

## Troubleshooting

### Brak połączenia z Elasticsearch

**Problem:** `Blad polaczenia z Elasticsearch: Connection refused`

```bash
# Sprawdź czy ES działa
curl http://localhost:9200

# Sprawdź logi ES
docker logs elasticsearch

# Użyj innego hosta
./run-preprocessor.sh search --text "test" --host "http://192.168.1.100:9200"
```

### Brak wyników

**Problem:** `Znaleziono: 0 wynikow`

```bash
# Sprawdź czy indeksy istnieją
./run-preprocessor.sh search --stats

# Jeśli 0 dokumentów - zaindeksuj dane
./run-preprocessor.sh index --name ranczo --elastic-documents-dir /app/output_data/elastic_documents
```

### Wolne embeddings/hashing

**Problem:** Długi czas ładowania modelu lub generowania embeddings

```bash
# Sprawdź czy używa GPU
docker logs ranchbot-preprocessing-app 2>&1 | grep "Model loaded"
# Powinno być: "Model loaded on cuda"

# Jeśli "Model loaded on cpu" - sprawdź NVIDIA Container Toolkit
nvidia-smi

# Model loading to jednorazowa operacja (pierwsze użycie)
# Kolejne zapytania będą szybsze (model w pamięci)
```

### Błąd "Podaj przynajmniej jedna opcje"

**Problem:** `Podaj przynajmniej jedna opcje wyszukiwania. Uzyj --help`

Musisz podać jedną z opcji wyszukiwania:

```bash
# ZLE
./run-preprocessor.sh search

# DOBRZE
./run-preprocessor.sh search --stats
./run-preprocessor.sh search --text "test"
./run-preprocessor.sh search --list-characters
```

### Image search - błąd ścieżki

**Problem:** `Blad: Obrazek nie istnieje: /home/user/screenshot.jpg`

Sprawdź ścieżkę (musi być dostępna w kontenerze):

```bash
# ZLE (ścieżka host)
./run-preprocessor.sh search --image /home/user/screenshot.jpg

# DOBRZE (ścieżka w kontenerze)
./run-preprocessor.sh search --image /input_data/screenshot.jpg
```

Upewnij się że plik jest w `preprocessor/input_data/`:

```bash
# Skopiuj plik do input_data
cp ~/screenshot.jpg preprocessor/input_data/

# Uruchom search
./run-preprocessor.sh search --image /input_data/screenshot.jpg
```

### Character not found

**Problem:** Character search nie znajduje postaci mimo że widzisz ją na liście

```bash
# Sprawdź dokładną nazwę (case-sensitive!)
./run-preprocessor.sh search --list-characters | grep -i lucy

# Użyj DOKŁADNEJ nazwy z listy
./run-preprocessor.sh search --character "Lucy Wilska"

# NIE:
./run-preprocessor.sh search --character "lucy wilska"  # ZLE
./run-preprocessor.sh search --character "Lucy"         # ZLE
```

---

## FAQ

### Jaka jest różnica między --text a --text-semantic?

- **`--text`** - BM25 full-text search
  - Szuka dokładnych słów (z fuzzy matching)
  - Przeszukuje pojedyncze segmenty
  - Zwraca dokładne timestampy (start/end)
  - Najlepsze gdy pamiętasz dokładne słowa

- **`--text-semantic`** - Semantic search
  - Rozumie znaczenie i kontekst
  - Przeszukuje grupy 5 segmentów
  - Zwraca zakres segmentów
  - Najlepsze gdy pamiętasz temat/sytuację

**Przykład:**
```bash
# Dokładne słowa
./run-preprocessor.sh search --text "Kto tu rządzi"

# Koncept/emocja
./run-preprocessor.sh search --text-semantic "konflikt o władzę"
```

### Czy mogę łączyć filtry?

Tak, większość filtrów można łączyć:

```bash
# Text + sezon + odcinek + limit
./run-preprocessor.sh search --text "Lucy" --season 10 --episode 5 --limit 10

# Image + postać + sezon
./run-preprocessor.sh search --image /input_data/shot.jpg --character "Lucy" --season 10

# Semantic + sezon
./run-preprocessor.sh search --text-semantic "wesele" --season 10 --limit 30
```

**Dostępne kombinacje:**
- `--text`: season, episode, limit
- `--text-semantic`: season, episode, limit
- `--image`: season, episode, character, limit
- `--character`: season, episode, limit
- `--hash`: limit

### Jak działa scoring w semantic search?

**Score = cosine similarity + 1.0**

- **Zakres:** 0-2
- **Im wyższy score, tym większe podobieństwo**
- **Score > 1.5** = bardzo podobne
- **Score > 1.0** = umiarkowanie podobne
- **Score < 1.0** = mało podobne

**Przykład:**
```
[1] Score: 1.92  ← bardzo podobne
[2] Score: 1.65  ← bardzo podobne
[3] Score: 1.45  ← umiarkowanie podobne
[4] Score: 0.85  ← mało podobne (prawdopodobnie false positive)
```

### Czy character search jest case-sensitive?

**TAK.** Nazwa musi dokładnie odpowiadać nazwie z `characters.json`:

```bash
# DOBRZE
./run-preprocessor.sh search --character "Lucy Wilska"

# ZLE (nie znajdzie)
./run-preprocessor.sh search --character "lucy wilska"
./run-preprocessor.sh search --character "Lucy"
./run-preprocessor.sh search --character "Wilska"
```

**Sprawdź dokładną nazwę:**
```bash
./run-preprocessor.sh search --list-characters | grep -i lucy
# Output: Lucy Wilska: 1,234 wystapien
# Użyj: "Lucy Wilska"
```

### Jak znaleźć scenę po numerze klatki?

Numer klatki nie jest bezpośrednio wyszukiwalny, ale możesz:

**Opcja 1:** Użyj semantic image search z klatką
```bash
# Jeśli masz klatkę
./run-preprocessor.sh search --image /input_data/frame_3450.jpg
```

**Opcja 2:** Oblicz timestamp i użyj full-text
```bash
# frame_number / fps = timestamp
# Np. klatka 3450 @ 30fps = 115s

# Znajdź wszystkie segmenty w okolicy
./run-preprocessor.sh search --text "test" --season 10 --episode 1 | grep "115"
```

**Opcja 3:** Użyj JSON output i jq
```bash
./run-preprocessor.sh search --character "Lucy" --season 10 --json-output | \
  jq '.hits[] | select(._source.frame_number == 3450)'
```

### Czy mogę przeszukiwać wiele indeksów naraz?

**Nie bezpośrednio.** Każda opcja przeszukuje tylko swój indeks:

- `--text` → `ranczo_segments`
- `--text-semantic` → `ranczo_text_embeddings`
- `--image`, `--character`, `--hash` → `ranczo_video_embeddings`

**Workaround:** Uruchom kilka komend lub użyj bezpośrednio Elasticsearch API.

```bash
# Full-text + semantic w osobnych zapytaniach
./run-preprocessor.sh search --text "wesele" --limit 10
./run-preprocessor.sh search --text-semantic "wesele" --limit 10

# Lub użyj JSON i złącz wyniki
./run-preprocessor.sh search --text "wesele" --json-output > text.json
./run-preprocessor.sh search --text-semantic "wesele" --json-output > semantic.json
```

### Jaka jest dokładność perceptual hash?

**Perceptual hash (pHash):**
- Hash size: 8 (16-znakowy hex string)
- Algorytm: DCT-based perceptual hash
- **Exact match:** Ten sam hash = wizualnie identyczne klatki
- **Nie wykrywa:** Podobne klatki (tylko identyczne)

**Użyj semantic image search dla podobnych (nie identycznych) scen:**
```bash
# Identyczne klatki
./run-preprocessor.sh search --hash /input_data/frame.jpg

# Podobne sceny
./run-preprocessor.sh search --image /input_data/frame.jpg
```

### Ile czasu zajmuje pierwsze wyszukiwanie?

**Pierwsze uruchomienie (cold start):**
- Ładowanie modelu Qwen2-VL: ~10-30s (GPU) lub ~1-2min (CPU)
- Kolejne zapytania: <1s (model w pamięci)

**Typy zapytań:**
- `--stats`, `--list-characters`: <1s (zawsze)
- `--text`, `--character`, `--hash`: <1s (zawsze)
- `--text-semantic`: 10-30s (pierwszy raz), <1s (kolejne)
- `--image`: 10-30s (pierwszy raz), <1s (kolejne)

**Optymalizacja:**
```bash
# Załaduj model przed właściwym użyciem
./run-preprocessor.sh search --text-semantic "test" --limit 1
# Teraz model jest w pamięci, kolejne zapytania będą szybkie
```

---

## Technologie i algorytmy

### Użyte technologie

- **Elasticsearch 8.17.0** - wyszukiwarka i baza wektorowa
- **Qwen2-VL** (`Alibaba-NLP/gme-Qwen2-VL-2B-Instruct`) - embeddingi text/video (768-dim)
- **InsightFace** (`buffalo_l`) - wykrywanie twarzy (ArcFace embeddings)
- **pHash** - perceptual hashing (DCT-based, hash_size=8)
- **BM25** - ranking algorithm dla full-text search
- **Cosine similarity** - metric dla semantic search
- **CUDA** - GPU acceleration (opcjonalne, fallback: CPU)

### Parametry embeddingów

**Model:** `Alibaba-NLP/gme-Qwen2-VL-2B-Instruct`
- **Wymiar:** 768 (dense_vector)
- **Normalizacja:** L2 normalized
- **Dtype:** bfloat16 (GPU) / float32 (CPU)
- **Device:** Auto (CUDA jeśli dostępne)

**Similarity:**
- Cosine similarity + 1.0 (zakres: 0-2)
- Script: `cosineSimilarity(params.query_vector, 'text_embedding') + 1.0`

### Parametry face detection

**Model:** InsightFace `buffalo_l`
- **Embedding dim:** 512 (ArcFace)
- **Threshold:** Konfigurowalny (default w settings)
- **GPU:** Opcjonalne (fallback: CPU)

### Parametry perceptual hash

**Algorytm:** pHash (DCT-based)
- **Hash size:** 8 (→ 64-bit → 16-char hex)
- **Output:** Lowercase hex string (np. "191b075b6d0363cf")
- **Matching:** Exact match (keyword field w ES)

---

## Powiązane dokumenty

- **[Główne README](README.md)** - pełna dokumentacja preprocessor pipeline
- **[Dev Search App](dev_search_app/README.md)** - standalone search tool (alternatywne UI)
- **Elasticsearch Docs** - https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **Qwen2-VL Docs** - https://huggingface.co/Alibaba-NLP/gme-Qwen2-VL-2B-Instruct
