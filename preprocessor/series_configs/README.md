# Series Configs

Każda seria to `{series_name}.json` zawierający **tylko różnice** względem `defaults.json`.

## Wymagane pola

```json
{
  "series_name": "nazwa_serii",
  "display_name": "Nazwa Wyświetlana",
  "indexing": { "elasticsearch": { "index_name": "nazwa_serii_clips" } },
  "scraping": {
    "episodes":   { "urls": ["https://..."] },
    "characters": { "urls": ["https://..."] }
  }
}
```

> `series_name` musi zgadzać się z nazwą pliku i katalogu `input_data/`.
> `urls` są **zawsze wymagane** przez parser — nawet jeśli scraper jest w `skip_steps`. Jeśli dane masz ręcznie, wpisz URL źródłowy skąd pochodzą (dla dokumentacji).

## Pipeline mode

| Wartość | Opis |
|---|---|
| `"full"` (domyślny) | Uruchamia wszystkie kroki |
| `"selective"` | Pomija kroki z listy `skip_steps` |

## skip_steps

| ID | Co pomija |
|---|---|
| `episode_scraper` | Scrapowanie listy odcinków |
| `character_scraper` | Scrapowanie listy postaci |
| `character_reference` | Pobieranie zdjęć referencyjnych postaci |
| `transcription` | Transkrypcja audio |
| `index_to_elasticsearch` | Wysyłanie do Elasticsearch |
| `generate_archives` | Generowanie archiwów ZIP |

Jednorazowe pominięcie bez zmiany configa: `run-all --series X --skip index_to_elasticsearch`.

## Transkrypcja

```json
"processing": { "transcription": { "mode": "elevenlabs" } }
```

| `mode` | Opis |
|---|---|
| `"whisper"` (domyślny) | Lokalny model Whisper (CUDA) |
| `"elevenlabs"` / `"11labs"` | API ElevenLabs (`ELEVENLABS_API_KEY`) |

Import gotowych transkrypcji (format 11labs):
```json
"processing": {
  "transcription_import": { "format_type": "11labs_segmented", "source_dir": "/transcriptions/nazwa_serii" }
}
```

## Zdjęcia referencyjne postaci

```json
"scraping": { "character_references": { "images_per_character": 2, "search_engine": "google" } }
```

`images_per_character: 0` pomija pobieranie. Domyślna wyszukiwarka: `"duckduckgo"` (bez API). `"google"` wymaga SerpAPI.

## Elasticsearch

```json
"indexing": { "elasticsearch": { "index_name": "nazwa_serii_clips", "host": "localhost:9200", "append": false, "dry_run": false } }
```

`dry_run: true` — generuje dokumenty ale nie wysyła. `append: true` — dopisuje do istniejącego indeksu.
