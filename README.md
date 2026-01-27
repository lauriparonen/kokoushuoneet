# Kokoushuoneet

Rajapinta kokoushuoneiden varauksien hallintaan.

## Paikallinen käyttö

### Vaatimukset
- Python 3.11+
- pip

### Asennus ja käynnistys

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Rajapinta pyörii osoitteessa `http://localhost:8000`.

Rajapinnan dokumentaatio ja SwaggerUI kutsujen helppoon tekemiseen löytyy polusta: `http://localhost:8000/docs`

## Kontitettu versio (Docker)

### Edellytykset
- Docker asennettu ja käynnissä

### Rakennus ja käynnistys

```bash
docker build -t kokoushuoneet:latest .
docker run -p 8000:8000 kokoushuoneet:latest
```

Kontitettu sovellus on vastaavasti saatavilla osoitteessa `http://localhost:8000`.

### Taustalla käytettävä kontti

```bash
docker run -d -p 8000:8000 --name booking-app kokoushuoneet:latest
docker logs booking-app
docker stop booking-app
```

## Testit

```bash
pip install -r requirements.txt
pytest
pytest -v
```

## Terveystarkistus

```bash
curl http://localhost:8000/health
```

## Huomio

Sovellus käyttää Suomen aikavyöhykettä (Europe/Helsinki) kaikissa aika-arvoissa.
