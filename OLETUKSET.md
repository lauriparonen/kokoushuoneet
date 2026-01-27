# Oletukset

Tämä dokumentti listaa liiketoimintalogiikan oletukset, jotka eivät käyneet ilmi tehtävänannosta. Todellisessa projektissa ne vahvistettaisiin asiakkaan kanssa.

---

## 1. Aikavyöhyke

### Oletus
Järjestelmä käyttää Suomen aikavyöhykettä (Europe/Helsinki).

### Perustelu
Tehtävänanto ei määritellyt aikavyöhykettä. Valitsin Suomen aikavyöhykkeen koska järjestelmä on oletettavasti suomalaista käyttöä varten.

### Vaikutukset
- Naive datetime-arvot tulkitaan Suomen ajaksi
- UTC-ajat konvertoidaan automaattisesti
- Kesä-/talviaika käsitellään automaattisesti

**Toteutus:** `app/schemas.py:7`  
**Testit:** `TestTimezoneHandling` (`tests/test_edge_cases.py:72`)

---

## 2. Varausten kesto

| Rajoitus | Arvo | Perustelu |
|----------|------|-----------|
| Minimi | 15 min | Lyhyitä palavereita varten |
| Maksimi | 4 h | Estää koko päivän varaamisen kerralla |

Peräkkäiset varaukset sallitaan.

**Toteutus:** `app/schemas.py:49-56`  
**Testit:** `test_very_short_booking_rejected`, `test_fifteen_minute_booking_accepted`, `test_extremely_long_booking_rejected`

---

## 3. Varaukset tulevaisuudessa

### Oletus
Varauksia voi tehdä max 90 päivää eteenpäin.

### Perustelu
Estää kohtuuttoman pitkälle ulottuvia varauksia. 90 päivää on sopiva alustava suunnitteluhorisontti.

**Toteutus:** `app/schemas.py:58-61`  
**Testit:** `test_booking_too_far_in_future_rejected`

---

## 4. Kenttien pituudet

| Kenttä | Min | Max | Perustelu |
|--------|-----|-----|-----------|
| room_id | 1 | 50 | Huonetunnisteet (esim. "A1", "Kokoustila-3") |
| user_name | 1 | 100 | Henkilönimet |

Whitespace trimmataan automaattisesti. Pelkkä whitespace hylätään.

**Toteutus:** `app/schemas.py:10-14`, `app/schemas.py:35-41`  
**Testit:** `test_whitespace_only_room_id_rejected`, `test_room_id_exceeds_max_length`, `test_user_name_exceeds_max_length`

---

## 5. Päällekkäisyydet

| Tilanne | Tulos |
|---------|-------|
| Varaukset päällekkäin | Hylätään (409) |
| Reunat koskettavat (end₁ = start₂) | Sallitaan |
| Eri huoneet, sama aika | Sallitaan |

### Konfliktin määritelmä
```python
A.start_time < B.end_time AND A.end_time > B.start_time
```

**Toteutus:** `app/services.py:143-173`  
**Testit:** `test_overlapping_booking_rejected`, `test_edge_touching_bookings_allowed`, `test_different_rooms_no_conflict`

---

## 6. Huoneiden hallinta

### Oletus
Ei ennalta määriteltyä huonelistaa. Mikä tahansa room_id on sallittu.

### Perustelu
Tehtävänanto ei määritellyt huonerekisteriä. Todellisessa toteutuksessa tämä integroitaisiin asiakkaan tietokantaan.

---

## 7. Peruutukset

### Oletus
Varauksia voi peruuttaa milloin tahansa ilman rajoituksia.

### Perustelu
Tehtävänanto ei määritellyt peruutussääntöjä. Todellisessa toteutuksessa käytettäisiin asiakkaan sääntöjä (esim. "ei peruutuksia 24h sisällä").

**Toteutus:** `app/routes.py:25-31`  
**Testit:** `test_complete_booking_lifecycle`

---

## 8. Kilpailutilanteet

### Ratkaisu
Rivi-tason lukitus (SQLAlchemy `with_for_update()` → SQL `FOR UPDATE`).

### Perustelu
Estää samanaikaisten pyyntöjen luoman kaksoisvarauksen. Toinen pyyntö odottaa ja saa joko 201 tai 409.

**Toteutus:** `app/services.py:143-173`  
**Testit:** `test_concurrent_booking_attempts_sequential`, `test_service_layer_with_locking`

---

## 9. Tekniset valinnat

### 9.1 Tietokanta
**SQLite in-memory** tehtävänannon mukaisesti.

- **Huom:** Data häviää palvelun uudelleenkäynnistyksessä
- **Tuotanto:** Migraatio PostgreSQL/MySQL:ään tarvitaan

**Toteutus:** `app/database.py`

### 9.2 Varaus-ID:t
**UUID v4** automaattisesti generoituna.

- Hajautetumpi kuin autoincrement
- Ei keskitettyä laskuria

**Toteutus:** `app/models.py:13`

---

## 10. HTTP-statuskoodit

| Tilanne | Koodi |
|---------|-------|
| Varaus luotu | 201 |
| Validointivirhe | 422 |
| Päällekkäisyys | 409 |
| Ei löydy | 404 |
| Peruttu | 204 |

Virheviestit sisältävät selkeän kuvauksen (esim. "Booking duration must be at least 15 minutes").

**Toteutus:** `app/exceptions.py`

---

## 11. API-päätepisteet

| Metodi | Polku | Toiminto |
|--------|-------|----------|
| POST | `/bookings/` | Luo varaus |
| GET | `/bookings/{booking_id}` | Hae varaus |
| DELETE | `/bookings/{booking_id}` | Peru varaus |
| GET | `/bookings/room/{room_id}` | Listaa huoneen varaukset |
| GET | `/health` | Terveystarkistus |

**Toteutus:** `app/routes.py`

---

## Yhteenveto

Nämä oletukset täyttävät tehtävänannon aukot. Todellisessa projektissa ne tarkennettaisiin asiakkaan kanssa.

Validoitu 35 testillä: `tests/test_edge_cases.py`