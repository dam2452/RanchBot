# Integration Tests

Testy integracyjne dla bota Ranczo z użyciem mocków dla zależności zewnętrznych.

## Różnice vs E2E Tests

| Aspekt | E2E Tests (`bot/tests/`) | Integration Tests (`bot/tests/integration/`) |
|--------|-------------------------|------------------------------------------|
| Elasticsearch | Prawdziwy ES + dane | Mock (in-memory) |
| FFmpeg / Video | Prawdziwe pliki video | Mock (puste pliki) |
| PostgreSQL | Prawdziwa testowa baza | **Mock (in-memory)** |
| REST API | Wymaga uruchomionego serwera | Bezpośrednie wywołanie handlerów |
| Telegram API | Mock przez REST | Mock przez FakeResponder |

## Struktura

```
bot/tests/integration/
├── README.md                      # Ten plik
├── conftest.py                    # Pytest fixtures (mocki, baza)
├── base_integration_test.py       # FakeMessage, FakeResponder, BaseIntegrationTest
├── mocks/
│   ├── __init__.py
│   ├── mock_elasticsearch.py      # Mock TranscriptionFinder
│   ├── mock_ffmpeg.py             # Mock ClipsExtractor/Compiler
│   └── test_data.py               # Przykładowe dane testowe (segmenty ES)
└── handlers/
    ├── test_clip_handler.py       # Testy dla /klip
    ├── test_search_handler.py     # Testy dla /szukaj
    └── ...
```

## Flow testu

1. **Setup (conftest.py fixtures)**
   - Inicjalizacja testowej bazy PostgreSQL
   - Monkey-patch mocków (ES, FFmpeg)
   - Przygotowanie danych testowych

2. **Wywołanie handlera**
   ```python
   message = FakeMessage(text='/klip geniusz', user_id=123, chat_id=456)
   responder = FakeResponder()
   handler = ClipHandler(message, responder, logger)
   await handler.handle()
   ```

3. **Asercje**
   - Sprawdź odpowiedzi w `responder.texts`, `responder.videos`
   - Sprawdź wpisy w bazie danych
   - Sprawdź wywołania mocków

## Przykład testu

```python
@pytest.mark.usefixtures("db_pool", "mock_es", "mock_ffmpeg")
class TestClipHandlerIntegration(BaseIntegrationTest):

    @pytest.mark.asyncio
    async def test_clip_found(self, mock_es, mock_ffmpeg):
        # Setup mock data
        mock_es.add_segment(
            quote='geniusz',
            text='To jest geniusz!',
            start=10.0,
            end=12.0,
            video_path='/fake/episode.mp4'
        )
        mock_ffmpeg.add_mock_clip('/fake/episode.mp4', '/tmp/test_clip.mp4')

        # Execute
        message = FakeMessage('/klip geniusz', user_id=self.admin_id)
        responder = FakeResponder()
        await ClipHandler(message, responder, self.logger).handle()

        # Assert
        assert len(responder.videos) == 1
        assert responder.videos[0]['file_path'].name == 'test_clip.mp4'
```

## Uruchomienie testów

```bash
# Wszystkie testy integracyjne
pytest bot/tests/integration/

# Konkretny plik
pytest bot/tests/integration/handlers/test_clip_handler.py

# Konkretny test
pytest bot/tests/integration/handlers/test_clip_handler.py::TestClipHandlerIntegration::test_clip_found

# Z logami
pytest bot/tests/integration/ -v -s
```

## Wymagania

- **Nie wymaga PostgreSQL** - wszystko zmockowane
- **Nie wymaga Elasticsearch** - wszystko zmockowane
- **Nie wymaga REST API serwera** - bezpośrednie wywołanie handlerów
- **Nie wymaga prawdziwych plików video** - FFmpeg zmockowany
- Wymaga tylko podstawowego pliku `.env` z minimalnymi ustawieniami
