# Servizio: sport-rules

Catalogo sport e ruleset (criteri punteggio/spareggio) — usa MongoDB

## Comunicazione (dai contratti)

Vedi `contracts/asyncapi.yaml` (eventi Kafka) e `contracts/openapi-sync.yaml`
(API sincrone) per gli eventi prodotti/consumati e gli endpoint di questo servizio.
Indice leggibile: `docs/CONTRATTI_Microservizi_v1.md`.

## Struttura (da creare in Fase 1+)

```
sport-rules/
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
```

## Sviluppo locale

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8003
```

Porta di default: **8003**
