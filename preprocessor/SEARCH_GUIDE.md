# Ranczo Search - Przewodnik

CLI do przeszukiwania danych w Elasticsearch.

**Wymagania:** Elasticsearch na `localhost:9200`, zaindeksowane dane (`run-all`)

## Tryby wyszukiwania

| Tryb | Flaga | Indeks | Opis |
|------|-------|--------|------|
| Full-text | `--text` | segments | BM25, dokładne słowa |
| Semantic text | `--text-semantic` | text_embeddings | Kontekst/znaczenie |
| Cross-modal | `--text-to-video` | video_embeddings | Tekst → klatki wideo |
| Image search | `--image` | video_embeddings | Podobne sceny wizualnie |
| Character | `--character` | video_embeddings | Po postaci (case-sensitive!) |
| Object | `--object` | video_embeddings | Po obiektach (80 klas COCO) |
| Episode fuzzy | `--episode-name` | episode_names | BM25 po tytułach |
| Episode semantic | `--episode-name-semantic` | episode_names | Semantic po tytułach |
| Hash | `--hash` | video_embeddings | Duplikaty klatek |
| Stats | `--stats` | wszystkie | Liczba dokumentów |
| Characters list | `--list-characters` | video_embeddings | Lista postaci |

## Quick Start

```bash
# Statystyki i lista postaci
./run-preprocessor.sh search --stats
./run-preprocessor.sh search --list-characters

# Full-text (BM25)
./run-preprocessor.sh search --text "Kto tu rządzi" --limit 5
./run-preprocessor.sh search --text "Lucy" --season 10 --episode 2

# Semantic (rozumie kontekst)
./run-preprocessor.sh search --text-semantic "wesele"
./run-preprocessor.sh search --text-semantic "smutna scena" --season 10

# Cross-modal (tekst → klatki)
./run-preprocessor.sh search --text-to-video "pocałunek" --character "Lucy Wilska"

# Image search
./run-preprocessor.sh search --image /input_data/screenshot.jpg --limit 20

# Character search (CASE-SENSITIVE!)
./run-preprocessor.sh search --character "Lucy Wilska" --season 10

# Object search (80 klas COCO)
./run-preprocessor.sh search --object "dog"
./run-preprocessor.sh search --object "person:5+"      # 5+ osób
./run-preprocessor.sh search --object "chair:2-4"      # 2-4 krzesła

# Episode name
./run-preprocessor.sh search --episode-name "Spadek"
./run-preprocessor.sh search --episode-name-semantic "wesele"

# Perceptual hash
./run-preprocessor.sh search --hash /input_data/frame.jpg
./run-preprocessor.sh search --hash "191b075b6d0363cf"

# JSON output
./run-preprocessor.sh search --text "Lucy" --json-output | jq '.hits[]'
```

## Filtry

| Filtr | Dostępne dla |
|-------|--------------|
| `--season N` | text, text-semantic, text-to-video, image, character, object, episode-name |
| `--episode N` | text, text-semantic, text-to-video, image, character, object |
| `--character NAME` | text-to-video, image, object |
| `--limit N` | wszystkie (default: 20) |
| `--json-output` | wszystkie |
| `--host URL` | wszystkie (default: localhost:9200) |

## Scoring

| Typ | Zakres | Interpretacja |
|-----|--------|---------------|
| BM25 (text) | 0-∞ | Wyższy = lepsze dopasowanie |
| Semantic | 0-2 | >1.5 bardzo podobne, >1.0 umiarkowanie |

## Object search - klasy COCO (80)

**Popularne:** person, car, dog, cat, chair, couch, bed, tv, laptop, cell phone, bottle, cup, book, clock

**Filtrowanie:** `object:N` (dokładnie N), `object:N+` (N lub więcej), `object:N-M` (zakres)

## Format wyników

```
[1] Score: 12.45
Episode: S10E01 - Pilot
Time: 120.50s - 125.30s [Scene 12: 115.0s - 130.0s]
Speaker: Lucy Wilska
Text: Kto tu rządzi? No kto?
Path: /app/output_data/transcoded_videos/ranczo_S10E01.mp4
```

## Troubleshooting

```bash
# Brak połączenia z ES
curl http://localhost:9200

# Brak wyników - sprawdź indeksy
./run-preprocessor.sh search --stats

# Character not found - sprawdź dokładną nazwę (case-sensitive!)
./run-preprocessor.sh search --list-characters | grep -i lucy

# Image path error - plik musi być w input_data/
cp ~/screenshot.jpg preprocessor/input_data/
./run-preprocessor.sh search --image /input_data/screenshot.jpg
```

## Kiedy użyć którego trybu?

| Sytuacja | Tryb |
|----------|------|
| Pamiętam dokładne słowa | `--text` |
| Pamiętam temat/emocję | `--text-semantic` |
| Mam screenshot | `--image` |
| Szukam wizualnie po opisie | `--text-to-video` |
| Szukam scen z postacią | `--character` |
| Szukam obiektów (samochód, pies) | `--object` |
| Szukam duplikatów klatek | `--hash` |
| Pamiętam tytuł odcinka | `--episode-name` |
| Pamiętam temat odcinka | `--episode-name-semantic` |
