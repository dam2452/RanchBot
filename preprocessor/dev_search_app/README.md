# Ranczo Search Dev Tool

Prosty CLI do testowania wyszukiwania w Elasticsearch.

## Setup

```bash
./run.sh
```

Lub manualnie:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Użycie

### Statystyki
```bash
./venv/bin/python search.py --stats
```

### Wyszukiwanie tekstowe
```bash
./venv/bin/python search.py --text "Kto tu rządzi" --limit 5
./venv/bin/python search.py --text "Solejukowa" --season 10
./venv/bin/python search.py --text "partyzanci" --season 10 --episode 2
```

### Wyszukiwanie po perceptual hash
```bash
./venv/bin/python search.py --hash "191b075b6d0363cf"
```

### Output JSON
```bash
./venv/bin/python search.py --text "test" --json
```

## Indeksy

- `ranczo_segments` - segmenty transkrypcji z timestampami
- `ranczo_text_embeddings` - embeddingi tekstowe
- `ranczo_video_embeddings` - embeddingi video z perceptual hashes

## Opcje

- `--text TEXT` - wyszukiwanie full-text
- `--hash HASH` - wyszukiwanie po perceptual hash
- `--season N` - filtruj po sezonie
- `--episode N` - filtruj po odcinku
- `--limit N` - limit wyników (default: 20)
- `--stats` - pokaż statystyki
- `--json` - output w formacie JSON
- `--host URL` - Elasticsearch host (default: http://localhost:9200)
