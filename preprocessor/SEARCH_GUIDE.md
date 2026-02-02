# Ranczo Search

CLI do przeszukiwania Elasticsearch. Wymaga ES na `localhost:9200` (lub inny `--host`) z zaindeksowanymi danymi.

**Indeksy:** `ranczo_segments` • `ranczo_text_embeddings` • `ranczo_video_frames` • `ranczo_episode_names`

---

## Tryby wyszukiwania

| Flaga | Opis |
|-------|------|
| `--text` | Full-text BM25, dokładne słowa |
| `--text-semantic` | Semantic, rozumie kontekst |
| `--text-to-video` | Tekst → klatki wideo |
| `--image` | Podobne sceny wizualnie |
| `--character` | Po postaci (**case-sensitive!**) |
| `--emotion` | Po emocjach (8 klas FER+) |
| `--object` | Po obiektach (80 klas COCO) |
| `--episode-name` | Fuzzy po tytułach |
| `--episode-name-semantic` | Semantic po tytułach |
| `--hash` | Duplikaty klatek (hash string lub ścieżka do obrazka) |
| `--stats` | Statystyki indeksów |
| `--list-characters` | Lista postaci |

---

## Przykłady

```bash
# Meta
./run-preprocessor.sh search --stats
./run-preprocessor.sh search --list-characters

# Text
./run-preprocessor.sh search --text "Kto tu rządzi" --limit 5
./run-preprocessor.sh search --text-semantic "wesele" --season 10

# Visual
./run-preprocessor.sh search --text-to-video "pocałunek"
./run-preprocessor.sh search --image /input_data/screenshot.jpg
./run-preprocessor.sh search --hash /input_data/frame.jpg  # znajdź duplikaty
./run-preprocessor.sh search --hash "a1b2c3d4e5f6"  # lub podaj hash bezpośrednio

# Filtry i kombinacje
./run-preprocessor.sh search --character "Lucy Wilska" --season 10
./run-preprocessor.sh search --emotion "happiness" --character "Lucy Wilska"
./run-preprocessor.sh search --emotion "sadness" --season 1 --episode 5
./run-preprocessor.sh search --object "person:5+"  # 5+ osób
./run-preprocessor.sh search --object "dog" --season 10
./run-preprocessor.sh search --text-to-video "pocałunek" --character "Lucy Wilska"
./run-preprocessor.sh search --image /input_data/frame.jpg --season 10 --episode 1

# Episode
./run-preprocessor.sh search --episode-name "Spadek"
./run-preprocessor.sh search --episode-name-semantic "wesele"

# Output
./run-preprocessor.sh search --text "Lucy" --json-output | jq '.hits[]'
```

---

## Filtry

| Filtr | Użycie |
|-------|--------|
| `--season N` | Sezon |
| `--episode N` | Odcinek |
| `--character NAME` | Postać (case-sensitive) |
| `--limit N` | Max wyników (domyślnie: 20) |
| `--json-output` | JSON zamiast tabeli |
| `--host URL` | Elasticsearch host (domyślnie: http://localhost:9200) |

---

## Emocje (FER+)

`neutral` `happiness` `surprise` `sadness` `anger` `disgust` `fear` `contempt`

---

## Obiekty (COCO)

**Popularne:** `person` `car` `dog` `cat` `chair` `couch` `tv` `laptop` `bottle` `cup` `book`

**Składnia:** `object` (≥1) • `object:N` (dokładnie N) • `object:N+` (≥N) • `object:N-M` (zakres)

---

## Kiedy którego użyć?

| Pamiętam... | Tryb |
|-------------|------|
| Dokładne słowa | `--text` |
| Temat/emocję w dialogach | `--text-semantic` |
| Mam screenshot | `--image` |
| Opis wizualny sceny | `--text-to-video` |
| Postać | `--character` |
| Emocję postaci | `--emotion` |
| Obiekt w kadrze | `--object` |
| Tytuł odcinka | `--episode-name` |
| Temat odcinka | `--episode-name-semantic` |

---

## Limity wyników

| Tryb | Domyślny limit | Opis |
|------|----------------|------|
| `--text` | 20 | Full-text search |
| `--text-semantic` | 10 | Semantic kNN (mniejszy limit = szybsze) |
| `--text-to-video` | 10 | Cross-modal kNN |
| `--image` | 10 | Video kNN |
| `--character` | 20 | Filter query |
| `--emotion` | 20 | Filter query |
| `--object` | 20 | Nested filter query |
| `--hash` | 10 | Exact match |
| `--episode-name` | 20 | Fuzzy match |
| `--episode-name-semantic` | 10 | Semantic kNN |

**Uwaga:** Dla kNN searches (semantic), `num_candidates = limit × 10` dla lepszej accuracy.

---

## Szczegóły techniczne

**Semantic search (kNN):**
- Model: Qwen/Qwen3-VL-Embedding-8B (4096-dim)
- `num_candidates`: limit × 10
- Similarity: cosine similarity

**Full-text search:**
- Engine: BM25
- Fuzziness: AUTO
- Fields: `text^2`, `episode_metadata.title`

**Perceptual hashing:**
- Algorithm: pHash
- Hash size: 8×8 = 64 bits
- Device: CUDA

**Character detection:**
- Model: InsightFace buffalo_l
- Face size: 112×112
- Threshold: 0.55 (frame detection)

**Object detection:**
- Model: D-FINE-X (COCO 80 classes)
- Confidence threshold: 0.30
- Nested queries dla count filters

**Emotion detection:**
- Model: EmoNet enet_b2_8
- Classes: 8 (FER+)

---

## Troubleshooting

```bash
# Test połączenia ES
curl http://localhost:9200
# Oczekiwany output: {"name": "...", "cluster_name": "...", ...}

# Test indeksów
./run-preprocessor.sh search --stats
# Powinno pokazać liczby dokumentów w każdym indeksie

# Brak wyników dla postaci (case-sensitive!)
./run-preprocessor.sh search --list-characters | grep -i "lucy"
# Użyj dokładnej nazwy: "Lucy Wilska" nie "lucy wilska"

# Błąd "Cannot connect to Elasticsearch"
docker-compose -f docker-compose.test.yml up -d
# lub ustaw --host http://twoj-es-server:9200

# CUDA errors przy --image lub --text-semantic
# Upewnij się że kontener ma dostęp do GPU i CUDA
nvidia-smi  # sprawdź dostępność GPU

# Plik obrazka nie znaleziony
# Ścieżki w kontenerze: /input_data/ nie ./input_data/
./run-preprocessor.sh search --image /input_data/screenshot.jpg  # ✓
./run-preprocessor.sh search --image ./input_data/screenshot.jpg  # ✗
```

**Wymagania:**
- Elasticsearch musi być uruchomiony i dostępny
- Dla `--image`, `--text-semantic`, `--text-to-video`, `--hash` (z obrazkiem): wymaga GPU z CUDA
- Obrazki muszą być dostępne w kontenerze (zamontuj jako volume lub użyj `/input_data/`)
