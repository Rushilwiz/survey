A tiny, self-hostable web app for a one-shot, anonymous classroom surveys.

## run it

```bash
docker compose up -d --build
```

Survey at http://localhost:8000, projector counter at http://localhost:8000/counter.

The SQLite file lives on the `survey-data` volume, so it survives rebuilds.
Set `EXPORT_TOKEN` to require `?token=...` on `/export`:

```bash
EXPORT_TOKEN=somesecret docker compose up -d
```

To wipe the responses: `docker compose down -v`.

## run it without docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

flask run
```

- rushil
