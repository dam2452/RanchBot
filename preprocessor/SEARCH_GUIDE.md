# Ranczo Search

CLI do przeszukiwania Elasticsearch. Wymaga ES na `localhost:9200` z zaindeksowanymi danymi.

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
| `--hash` | Duplikaty klatek |
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

# Filtry
./run-preprocessor.sh search --character "Lucy Wilska" --season 10
./run-preprocessor.sh search --emotion "happiness" --character "Lucy Wilska"
./run-preprocessor.sh search --object "person:5+"  # 5+ osób

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
| `--limit N` | Max wyników (default: 20) |
| `--json-output` | JSON zamiast tabeli |
| `--host URL` | Inny ES (default: localhost:9200) |

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

## Troubleshooting

```bash
curl http://localhost:9200                              # Brak połączenia
./run-preprocessor.sh search --stats                    # Brak wyników
./run-preprocessor.sh search --list-characters | grep -i lucy  # Case-sensitive
```

**Image path:** plik musi być w `input_data/` → `/input_data/` w kontenerze