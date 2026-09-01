# Piattaforma di Gestione Tornei Sportivi

Piattaforma per la gestione end-to-end di tornei sportivi (v1 focalizzata sul calcio,
data model predisposto per multi-sport). Architettura a **microservizi**, comunicazione
via **API sincrone** (FastAPI) ed **eventi asincroni** (Kafka).

> **Monorepo con confini di servizio netti:** ogni servizio ha DB, codice e Dockerfile
> propri, e comunica con gli altri **solo** tramite i contratti in `contracts/` e `docs/`
> (mai import di codice o accesso al DB altrui).

## Stack tecnologico

| Ambito | Tecnologia |
|--------|-----------|
| Linguaggio / framework | Python 3.12 - FastAPI |
| Database relazionali | PostgreSQL (un DB per servizio) |
| Database documentale | MongoDB (servizio Sport & Rules) |
| Object storage | S3-compatibile (documenti) |
| Messaggistica | Apache Kafka |
| Container | Docker |
| Orchestrazione | Kubernetes (differita) |
| Infrastruttura | Terraform |

## Struttura del repository

```
tournaments-platform/
├── contracts/              # Contratti macchina-leggibili
│   ├── asyncapi.yaml       #   eventi Kafka
│   └── openapi-sync.yaml   #   API sincrone cross-context
├── docs/                   # Progettazione
│   ├── CONTRATTI_Microservizi_v1.md
│   ├── schema_er_tornei_v1.dbml
│   └── schema_er_tornei_v1.svg
├── services/               # un sottoprogetto per microservizio
│   ├── identity/           #   Identity & Access        (porta 8001)
│   ├── tournament/         #   Tournament Management     (porta 8002)
│   ├── sport-rules/        #   Sport & Rules (MongoDB)   (porta 8003)
│   ├── team-roster/        #   Team & Roster             (porta 8004)
│   ├── registration/       #   Registration             (porta 8005)
│   ├── documents/          #   Documents (+ S3)          (porta 8006)
│   └── scoring/            #   Scoring & Standings       (porta 8007)
├── libs/                   # SOLO codice realmente condiviso (es. envelope eventi)
├── deploy/                 # infrastruttura
│   ├── terraform/          #   IaC
│   ├── k8s/                #   manifest Kubernetes (differiti)
│   └── local/              #   init DB per sviluppo locale
└── docker-compose.yml      # infra locale (Postgres + Mongo + Kafka) (in arrivo — Fase 0)
```

## I 7 microservizi

| Servizio | Responsabilita' | DB | Porta |
|----------|-----------------|-----|-------|
| **identity** | Utenti, ruoli, autenticazione | PostgreSQL | 8001 |
| **tournament** | Creazione/gestione tornei, formati | PostgreSQL | 8002 |
| **sport-rules** | Catalogo sport, ruleset | MongoDB | 8003 |
| **team-roster** | Squadre e roster giocatori | PostgreSQL | 8004 |
| **registration** | Iscrizioni squadre ai tornei | PostgreSQL | 8005 |
| **documents** | Documenti richiesti e caricati | PostgreSQL + S3 | 8006 |
| **scoring** | Gironi, tabelloni, partite, classifiche | PostgreSQL | 8007 |

## Regole di confine (bounded context)

1. **Nessun servizio importa il codice di un altro.** Uniche dipendenze condivise: `contracts/` e `libs/`.
2. **Nessun servizio accede al DB di un altro.** Solo API sincrone o eventi Kafka.
3. **I contratti si modificano prima del codice.** Prima `contracts/`, poi i servizi.

## Sviluppo locale

```bash
# Avvia l'infrastruttura (Postgres + Mongo + Kafka)
docker compose up -d

# Lavora su un singolo servizio
cd services/identity
python -m venv .venv
.venv\Scripts\Activate.ps1        # PowerShell (Windows)
pip install -r requirements.txt
copy .env.example .env             # poi valorizza le variabili
uvicorn app.main:app --reload --port 8001
```

## Documentazione

- **Contratti (indice):** `docs/CONTRATTI_Microservizi_v1.md`
- **Schema dati:** `docs/schema_er_tornei_v1.dbml` (visualizzabile su dbdiagram.io)
- **Eventi:** `contracts/asyncapi.yaml` (studio.asyncapi.com)
- **API sincrone:** `contracts/openapi-sync.yaml` (editor.swagger.io)