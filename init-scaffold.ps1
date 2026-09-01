# =====================================================================
#  init-scaffold.ps1
#  Genera lo scaffold mancante del monorepo Tornei Sportivi.
#  Da lanciare DALLA ROOT della repo (dove ci sono le cartelle contracts/ e docs/).
#  NON tocca contracts/ e docs/ (gia' presenti).
#  Crea: README.md, .gitignore, services/<7 servizi>, deploy/, libs/
# =====================================================================

$ErrorActionPreference = "Stop"

# --- Guardia: assicurati di essere nella root giusta ---
if (-not (Test-Path ".git")) {
    Write-Host "ERRORE: non sembra la root della repo (manca .git). Spostati nella cartella della repo e riprova." -ForegroundColor Red
    exit 1
}

Write-Host "Genero lo scaffold mancante..." -ForegroundColor Cyan

# Helper: crea un file solo se non esiste, con contenuto UTF-8
function New-FileIfMissing($path, $content) {
    if (Test-Path $path) {
        Write-Host "  SKIP (esiste gia'): $path" -ForegroundColor Yellow
    } else {
        $dir = Split-Path $path -Parent
        if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        # UTF-8 senza BOM
        [System.IO.File]::WriteAllText((Join-Path (Get-Location) $path), $content, (New-Object System.Text.UTF8Encoding $false))
        Write-Host "  CREATO: $path" -ForegroundColor Green
    }
}

# ---------------------------------------------------------------------
# 1. Definizione servizi: nome, porta, tipo DB
# ---------------------------------------------------------------------
$services = @(
    @{ name="identity";      port=8001; db="postgres"; dbname="identity_db";      desc="Utenti, ruoli, autenticazione" }
    @{ name="tournament";    port=8002; db="postgres"; dbname="tournament_db";    desc="Creazione/gestione tornei, formati" }
    @{ name="sport-rules";   port=8003; db="mongo";    dbname="sport_rules_db";   desc="Catalogo sport, ruleset (criteri punteggio/spareggio)" }
    @{ name="team-roster";   port=8004; db="postgres"; dbname="team_roster_db";   desc="Squadre e roster giocatori" }
    @{ name="registration";  port=8005; db="postgres"; dbname="registration_db";  desc="Iscrizioni squadre ai tornei, pagamento manuale" }
    @{ name="documents";     port=8006; db="postgres"; dbname="documents_db";     desc="Documenti richiesti e caricati (metadati) + object storage" }
    @{ name="scoring";       port=8007; db="postgres"; dbname="scoring_db";       desc="Gironi, tabelloni, partite, classifiche (US-10/11)" }
)

# ---------------------------------------------------------------------
# 2. File radice: .gitignore
# ---------------------------------------------------------------------
$gitignore = @'
# ===== Python =====
__pycache__/
*.py[cod]
*.so
build/
dist/
*.egg-info/
*.egg
.eggs/

# Virtual environments
.venv/
venv/
env/
ENV/
.python-version

# Test / coverage
.pytest_cache/
.coverage
.coverage.*
htmlcov/
coverage.xml
.hypothesis/

# Type checking / linting
.mypy_cache/
.dmypy.json
.ruff_cache/
.pyre/

# ===== Env / secrets =====
.env
.env.*
!.env.example
*.pem
*.key
secrets/
credentials.json

# ===== Docker =====
docker-compose.override.yml
.docker/
*.tar
*.tar.gz

# ===== Terraform =====
**/.terraform/*
*.tfstate
*.tfstate.*
crash.log
crash.*.log
*.tfvars
*.tfvars.json
!example.tfvars
!terraform.tfvars.example
override.tf
override.tf.json
*_override.tf
.terraformrc
terraform.rc
# .terraform.lock.hcl: rimuovi la riga sotto se vuoi versionarlo (pin provider)
.terraform.lock.hcl

# ===== Kubernetes =====
*-secret.yaml
!*-secret.example.yaml
kubeconfig
*.kubeconfig

# ===== Dati locali (Kafka/DB volumes) =====
kafka-data/
*-data/

# ===== IDE / OS =====
.idea/
.vscode/
!.vscode/settings.json.example
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# ===== Docs generati =====
site/
_build/
'@
New-FileIfMissing ".gitignore" $gitignore

# ---------------------------------------------------------------------
# 3. File radice: README.md
# ---------------------------------------------------------------------
$readme = @'
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
└── docker-compose.yml      # infra locale (Postgres + Mongo + Kafka)
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
'@
New-FileIfMissing "README.md" $readme

# ---------------------------------------------------------------------
# 4. Per ogni servizio: README, Dockerfile, requirements, .env.example
# ---------------------------------------------------------------------
foreach ($s in $services) {
    $name = $s.name; $port = $s.port; $base = "services/$name"

    # ----- requirements.txt -----
    if ($s.db -eq "mongo") {
        $reqDb = "# Database (MongoDB async)`nmotor==3.*`npymongo==4.*"
    } else {
        $reqDb = "# Database (PostgreSQL async)`nsqlalchemy[asyncio]==2.*`nasyncpg==0.30.*`nalembic==1.*"
    }
    $reqExtra = ""
    if ($name -eq "documents") { $reqExtra = "`n# Object storage (S3)`nboto3==1.*" }
    $requirements = @"
# Web framework
fastapi==0.115.*
uvicorn[standard]==0.32.*
pydantic==2.*
pydantic-settings==2.*

$reqDb

# Kafka
aiokafka==0.12.*

# HTTP client (chiamate sincrone ad altri servizi)
httpx==0.28.*
$reqExtra

# --- Dev / test ---
pytest==8.*
pytest-asyncio==0.24.*
ruff==0.8.*
mypy==1.*
"@
    New-FileIfMissing "$base/requirements.txt" $requirements

    # ----- .env.example -----
    if ($s.db -eq "mongo") {
        $envDb = "# Database (MongoDB)`nMONGODB_URL=mongodb://localhost:27017/$($s.dbname)"
    } else {
        $envDb = "# Database (PostgreSQL dedicato al servizio)`nDATABASE_URL=postgresql+asyncpg://$($name):changeme@localhost:5432/$($s.dbname)"
    }
    $envExtra = ""
    if ($name -eq "documents") {
        $envExtra = @"

# Object storage (S3-compatibile)
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET=documents
S3_ACCESS_KEY=changeme
S3_SECRET_KEY=changeme
"@
    }
    $envContent = @"
# =====================================================================
# $name - variabili d'ambiente (ESEMPIO). Copia in .env e valorizza.
# NON committare .env.
# =====================================================================

# --- App ---
APP_NAME=$name
APP_ENV=local
LOG_LEVEL=info
PORT=$port

$envDb

# --- Kafka ---
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP=$name-service
# TODO: allineare i topic prodotti/consumati con contracts/asyncapi.yaml
$envExtra
"@
    New-FileIfMissing "$base/.env.example" $envContent

    # ----- Dockerfile -----
    $dockerfile = @"
# =====================================================================
# $name - Dockerfile (FastAPI)
# =====================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE $port

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$port"]
"@
    New-FileIfMissing "$base/Dockerfile" $dockerfile

    # ----- README.md del servizio -----
    $svcReadme = @"
# Servizio: $name

$($s.desc)

## Comunicazione (dai contratti)

Vedi \`contracts/asyncapi.yaml\` (eventi Kafka) e \`contracts/openapi-sync.yaml\`
(API sincrone) per gli eventi prodotti/consumati e gli endpoint di questo servizio.
Indice leggibile: \`docs/CONTRATTI_Microservizi_v1.md\`.

## Struttura (da creare in Fase 1+)

\`\`\`
$name/
├── app/
│   ├── main.py            # entrypoint FastAPI
│   ├── api/               # router / endpoint
│   ├── domain/            # logica di dominio
│   ├── models/            # modelli DB
│   ├── events/            # producer/consumer Kafka
│   └── config.py
├── tests/
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
\`\`\`

## Sviluppo locale

\`\`\`powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port $port
\`\`\`

Porta di default: **$port**
"@
    New-FileIfMissing "$base/README.md" $svcReadme

    # ----- .gitkeep nelle sottocartelle vuote previste -----
    New-FileIfMissing "$base/app/.gitkeep" ""
    New-FileIfMissing "$base/tests/.gitkeep" ""
}

# ---------------------------------------------------------------------
# 5. Cartelle infra + libs con .gitkeep
# ---------------------------------------------------------------------
New-FileIfMissing "deploy/terraform/.gitkeep" ""
New-FileIfMissing "deploy/k8s/.gitkeep" ""
New-FileIfMissing "deploy/local/.gitkeep" ""
New-FileIfMissing "libs/.gitkeep" ""

Write-Host ""
Write-Host "Scaffold completato." -ForegroundColor Cyan
Write-Host "Prossimi passi:" -ForegroundColor Cyan
Write-Host "  git status            # controlla cosa e' stato creato"
Write-Host "  git add ."
Write-Host "  git commit -m 'chore: completa scaffold servizi + file radice'"
Write-Host "  git push"
Write-Host ""
Write-Host "NB: il docker-compose.yml NON e' incluso qui: lo generiamo come passo dedicato." -ForegroundColor Yellow
