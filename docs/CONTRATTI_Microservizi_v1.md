# Documento dei Contratti tra Microservizi

## Piattaforma di Gestione Tornei Sportivi — Versione 1 (MVP)

> **Scopo.** Questo documento è propedeutico all'implementazione dei microservizi,
> esattamente come il documento dei requisiti lo era per la progettazione.
> Per ogni riferimento cross-context dello schema ER (freccia tratteggiata) definisce:
> il **mezzo di comunicazione** (API sincrona vs evento asincrono), il **razionale**,
> e — per gli eventi — lo **schema del payload** (chi emette, chi consuma, struttura).
>
> **Sorgenti di verità collegate:**
> - Schema dati: `schema_er_tornei_v1.dbml`
> - Eventi (macchina-leggibile): `asyncapi.yaml`
> - API sincrone (macchina-leggibile): `openapi-*.yaml` (uno per servizio che espone endpoint)
>
> **Broker eventi scelto:** Apache **Kafka** (log persistente, replay, coerente con
> ricalcoli a cascata US-11 ed evoluzione event-sourcing).

---

## 1. I microservizi (bounded context)

| # | Servizio | Owner dei dati | DB |
|---|----------|----------------|-----|
| 1 | **Identity & Access** | `users`, `user_roles` | PostgreSQL |
| 2 | **Tournament Management** | `tournaments`, `tournament_format_config` | PostgreSQL |
| 3 | **Sport & Rules** | `sports`, `sport_ruleset` | MongoDB (documentale) |
| 4 | **Team & Roster** | `teams`, `team_members` | PostgreSQL |
| 5 | **Registration** | `registrations` | PostgreSQL |
| 6 | **Documents** | `required_documents`, `uploaded_documents` (+ object storage) | PostgreSQL + S3 |
| 7 | **Scoring & Standings** | `groups`, `group_teams`, `matches`, `standings` | PostgreSQL |

---

## 2. Principio decisionale sync vs async

Applicato freccia per freccia:

- **API SINCRONA** → il chiamante ha bisogno di una **risposta adesso** per procedere,
  e sta **leggendo** un dato di cui un altro servizio è owner.
  *Test:* "il mittente deve attendere una risposta per continuare?" → **Sì**.

- **EVENTO ASINCRONO** → un servizio **ha compiuto un fatto** e altri devono reagire,
  ma il mittente **non deve attendere né conoscere i consumatori** (side effect).
  *Test:* "il mittente sta solo comunicando qualcosa di avvenuto?" → **Sì**.

- **DATO DI RIFERIMENTO REPLICATO** → un servizio ha bisogno *costante* di un dato
  altrui in lettura (es. nome squadra in Scoring). Invece di interrogare sincronamente
  a ogni lettura nel percorso critico, il servizio mantiene una **copia locale read-only**
  aggiornata **via evento**. Evita accoppiamento e chiamate nel path di lettura pubblica.

---

## 3. Mappa completa delle frecce cross-context (18 riferimenti)

Legenda mezzo: **[SYNC]** API · **[EVT]** evento Kafka · **[REPL]** dato replicato via evento

| # | Da (servizio.campo) | A (servizio.entità) | Mezzo | Razionale |
|---|---------------------|---------------------|-------|-----------|
| 1 | Tournament.`organizer_id` | Identity.`users` | **[SYNC]** | Validazione owner al momento della creazione torneo; lettura puntuale. |
| 2 | Tournament.`sport_id` | Sport.`sports` | **[SYNC]** | Validazione sport esistente alla creazione; catalogo piccolo e stabile. |
| 3 | Sport.`sport_ruleset.tournament_id` | Tournament.`tournaments` | **[EVT]** | Ruleset associato a un torneo reagendo a `TournamentCreated`/`Published`. |
| 4 | Team.`created_by` | Identity.`users` | **[SYNC]** | Validazione utente creatore alla creazione squadra. |
| 5 | Team.`team_members.user_id` | Identity.`users` | **[SYNC]** | Validazione utente all'invito/join; lettura puntuale. |
| 6 | Registration.`tournament_id` | Tournament.`tournaments` | **[SYNC]** | Verifica torneo aperto/esistente e leggi regole iscrizione all'atto dell'iscrizione. |
| 7 | Registration.`team_id` | Team.`teams` | **[SYNC]** | Verifica squadra esistente e appartenenza capitano all'iscrizione. |
| 8 | Documents.`required_documents.tournament_id` | Tournament.`tournaments` | **[SYNC]+[EVT]** | Lettura torneo alla definizione template (sync); reagisce a `TournamentPublished` per abilitare upload (evt). |
| 9 | Documents.`uploaded_documents.registration_id` | Registration.`registrations` | **[EVT]** | Upload abilitati quando esiste un'iscrizione: reagisce a `RegistrationSubmitted`. |
| 10 | Documents.`uploaded_documents.uploaded_by` | Identity.`users` | **[SYNC]** | Validazione proprietario documento all'upload. |
| 11 | Documents.`uploaded_documents.player_user_id` | Identity.`users` | **[SYNC]** | Validazione giocatore destinatario (doc livello PLAYER). |
| 12 | Scoring.`groups.tournament_id` | Tournament.`tournaments` | **[EVT]** | Generazione gironi/tabellone innescata da `RegistrationClosed` (US-10). |
| 13 | Scoring.`group_teams.team_id` | Team.`teams` | **[REPL]** | Nome squadra serve costante in lettura pubblica (US-12/13): copia locale via evento. |
| 14 | Scoring.`matches.tournament_id` | Tournament.`tournaments` | **[EVT]** | Le partite nascono dalla generazione tabellone su chiusura iscrizioni. |
| 15 | Scoring.`matches.home_team_id` | Team.`teams` | **[REPL]** | Come #13: dato replicato per lettura pubblica senza chiamate nel path critico. |
| 16 | Scoring.`matches.away_team_id` | Team.`teams` | **[REPL]** | Come #13. |
| 17 | Scoring.`standings.team_id` | Team.`teams` | **[REPL]** | Classifica pubblica lettura-pesante: nome squadra replicato. |
| 18 | Registration → Scoring (squadre accettate) | (flusso) | **[EVT]** | `RegistrationAccepted` alimenta l'elenco squadre partecipanti in Scoring. |

> **Nota su #13, #15, #16, #17.** Team & Roster è l'owner del nome squadra. Scoring ne
> mantiene una proiezione locale (`team_id` + `team_name` cache) aggiornata dagli eventi
> `TeamCreated`/`TeamUpdated`/`TeamNameChanged`. Così la pagina pubblica non fa MAI una
> chiamata sincrona a Team nel percorso di lettura.

---

## 4. Catalogo eventi Kafka (envelope + payload)

Ogni evento usa un **envelope standard** production-grade:

```json
{
  "eventId": "uuid",          // idempotenza lato consumer
  "eventType": "string",      // es. "registration.accepted"
  "version": "1.0",           // versionamento schema evento
  "occurredAt": "ISO-8601",   // timestamp del fatto
  "correlationId": "uuid",    // tracciamento end-to-end del flusso
  "producer": "string",       // servizio emittente
  "payload": { ... }          // specifico per evento (vedi sotto)
}
```

### 4.1 Topic e ownership

| Topic Kafka | Producer | Consumers principali |
|-------------|----------|----------------------|
| `identity.users` | Identity | Team, Tournament, Documents (validazione/replica) |
| `tournament.lifecycle` | Tournament | Sport, Documents, Registration, Scoring |
| `team.roster` | Team | Scoring (replica nome), Registration |
| `registration.lifecycle` | Registration | Documents, Scoring |
| `scoring.results` | Scoring | Tournament (stato torneo), futura Notifiche |

### 4.2 Eventi principali (dettaglio payload)

**`tournament.created`** — Producer: Tournament
```json
{ "tournamentId": "uuid", "organizerId": "uuid", "sportId": "uuid", "name": "string", "format": "ROUND_ROBIN|SINGLE_ELIM|GROUPS_PLUS_ELIM" }
```
Consumers: Sport (crea/associa ruleset).

**`tournament.published`** — Producer: Tournament
```json
{ "tournamentId": "uuid", "publishedAt": "ISO-8601" }
```
Consumers: Documents (abilita definizione/upload), Registration (apre iscrizioni).

**`tournament.registration_closed`** — Producer: Tournament
```json
{ "tournamentId": "uuid", "closedAt": "ISO-8601" }
```
Consumers: **Scoring** (innesca generazione gironi/tabellone — US-10).

**`team.created`** — Producer: Team
```json
{ "teamId": "uuid", "name": "string", "createdBy": "uuid" }
```
Consumers: Scoring (inizializza proiezione nome squadra).

**`team.name_changed`** — Producer: Team
```json
{ "teamId": "uuid", "name": "string" }
```
Consumers: Scoring (aggiorna proiezione locale).

**`registration.submitted`** — Producer: Registration
```json
{ "registrationId": "uuid", "tournamentId": "uuid", "teamId": "uuid", "submittedAt": "ISO-8601" }
```
Consumers: Documents (abilita upload documenti per quell'iscrizione).

**`registration.accepted`** — Producer: Registration
```json
{ "registrationId": "uuid", "tournamentId": "uuid", "teamId": "uuid", "acceptedAt": "ISO-8601" }
```
Consumers: **Scoring** (squadra confermata partecipante), futura Notifiche.

**`registration.rejected`** — Producer: Registration
```json
{ "registrationId": "uuid", "tournamentId": "uuid", "teamId": "uuid", "reason": "string" }
```
Consumers: futura Notifiche.

**`match.result_recorded`** — Producer: Scoring
```json
{ "matchId": "uuid", "tournamentId": "uuid", "homeTeamId": "uuid", "awayTeamId": "uuid", "homeScore": 0, "awayScore": 0, "stage": "GROUP|KNOCKOUT" }
```
Consumers: Tournament (aggiorna stato → IN_PROGRESS/COMPLETED), futura Notifiche.
*Nota US-11:* il ricalcolo classifiche/avanzamento bracket è **interno** a Scoring (non un evento cross-context); l'evento serve solo agli altri contesti.

---

## 5. API sincrone (contratti REST)

Ogni servizio che viene interrogato sincronamente espone endpoint di sola lettura/validazione.
Dettaglio macchina-leggibile in `openapi-*.yaml`. Sintesi:

| Servizio | Endpoint chiave | Chiamato da | Scopo |
|----------|-----------------|-------------|-------|
| Identity | `GET /users/{id}` | Team, Tournament, Documents | Validazione esistenza/dati utente |
| Identity | `POST /users/_validate` (batch) | vari | Validazione batch di più id |
| Sport | `GET /sports/{id}` | Tournament | Validazione sport (catalogo) |
| Sport | `GET /sports/{id}/ruleset` | Scoring | Legge criteri punteggio/spareggio per calcolo classifiche |
| Tournament | `GET /tournaments/{id}` | Registration, Documents | Verifica stato/apertura iscrizioni |
| Team | `GET /teams/{id}` | Registration | Verifica squadra + capitano |
| Team | `GET /teams/{id}/members` | Registration | Verifica roster all'iscrizione |

> **Sport.ruleset (riga #5 tabella).** Scoring legge il ruleset **sincronamente al momento del
> calcolo** classifiche (US-12): serve la risposta subito per ordinare con i criteri di
> spareggio. Alternativa: replicare il ruleset in Scoring alla generazione tabellone.
> Decisione aperta — vedi §7.

---

## 6. Flussi end-to-end principali (Must-have)

**Flusso A — Dalla creazione torneo alle iscrizioni**
1. Organizzatore crea torneo → `[SYNC]` Tournament valida `organizer_id` su Identity e `sport_id` su Sport.
2. Tournament emette `tournament.created` → Sport associa ruleset.
3. Organizzatore pubblica → `tournament.published` → Documents e Registration reagiscono.

**Flusso B — Iscrizione e accettazione**
1. Capitano iscrive squadra → `[SYNC]` Registration verifica torneo (Tournament) e squadra (Team).
2. Registration emette `registration.submitted` → Documents abilita upload.
3. Capitano/giocatori caricano documenti → `[SYNC]` Documents valida owner su Identity.
4. Organizzatore valida documenti + marca pagamento → Registration emette `registration.accepted`.
5. Scoring consuma `registration.accepted` → registra squadra partecipante (con nome replicato via `team.created`).

**Flusso C — Generazione tabellone e risultati (US-10, US-11)**
1. Organizzatore chiude iscrizioni → `tournament.registration_closed`.
2. Scoring consuma l'evento → genera gironi/bracket (US-10, logica interna).
3. Organizzatore inserisce risultato → Scoring ricalcola classifica/avanzamento (interno) → emette `match.result_recorded`.
4. Tournament consuma → aggiorna stato torneo.

**Flusso D — Lettura pubblica (US-12, US-13)**
- Pagina pubblica interroga `[SYNC]` Scoring (classifiche/partite) e Tournament (dettagli).
- Scoring risponde con nomi squadra dalla **proiezione locale** (nessuna chiamata a Team nel path).

---

## 7. Decisioni aperte (da confermare)

1. **Ruleset in Scoring: sync o replicato?** Leggere il ruleset via `[SYNC]` a ogni calcolo, o
   replicarlo in Scoring alla generazione tabellone (più autonomo, ma dato duplicato)?
2. **Object storage documenti.** Presigned URL generati da Documents e restituiti al client
   (upload diretto a S3) vs upload via Documents (proxy)? Impatta il contratto di `POST /documents`.
3. **Outbox pattern.** Per garantire "scrivi su DB + pubblica evento" atomico, adottiamo
   transactional outbox in ogni producer? (Consigliato per production-readiness.)
4. **Schema Registry.** Usiamo Confluent Schema Registry (Avro/JSON Schema) per validare gli
   eventi a runtime, o teniamo gli schemi solo in AsyncAPI?

---

*Documento di lavoro modificabile. Aggiornare man mano che i contratti si stabilizzano.*
