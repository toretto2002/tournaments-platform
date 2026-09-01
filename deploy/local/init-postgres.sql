-- =====================================================================
-- init-postgres.sql
-- Crea i ruoli per-servizio e i database applicativi, uno per ciascun
-- microservizio PostgreSQL. Ogni ruolo e' OWNER del proprio database:
-- permessi pieni sul proprio DB, nessun GRANT aggiuntivo necessario.
--
-- IMPORTANTE: questo script viene eseguito automaticamente da Postgres
-- SOLO al primissimo avvio del container, quando il volume dati e' vuoto
-- (meccanismo standard /docker-entrypoint-initdb.d/ dell'immagine ufficiale
-- postgres). Se il volume "pgdata" esiste gia', lo script NON viene rieseguito:
-- per applicarlo di nuovo occorre rimuovere il volume (docker compose down -v),
-- oppure rilanciarlo a mano con `psql -f`. Per quest'ultimo caso lo script e'
-- scritto per essere ri-eseguibile senza errori (controlli "se non esiste
-- gia'" sotto, sia per i ruoli sia per i database).
--
-- Credenziali: ruoli per-servizio con password comune 'password' — SOLO
-- sviluppo locale, mai in altri ambienti.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) RUOLI per-servizio (LOGIN + password comune 'password' in locale).
--    CREATE ROLE non supporta "IF NOT EXISTS": l'idiom standard per
--    renderlo idempotente e' un blocco DO con controllo su pg_roles.
--    "team-roster" contiene un trattino: in Postgres un identificatore
--    con caratteri non standard va SEMPRE fra virgolette doppie.
-- ---------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'identity') THEN
    CREATE ROLE identity LOGIN PASSWORD 'password';
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tournament') THEN
    CREATE ROLE tournament LOGIN PASSWORD 'password';
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'team-roster') THEN
    CREATE ROLE "team-roster" LOGIN PASSWORD 'password';
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'registration') THEN
    CREATE ROLE registration LOGIN PASSWORD 'password';
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'documents') THEN
    CREATE ROLE documents LOGIN PASSWORD 'password';
  END IF;
END
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'scoring') THEN
    CREATE ROLE scoring LOGIN PASSWORD 'password';
  END IF;
END
$$;

-- ---------------------------------------------------------------------
-- 2) DATABASE, uno per servizio, con OWNER assegnato subito al ruolo
--    corrispondente (owner = permessi pieni sul proprio DB, senza GRANT
--    aggiuntivi). CREATE DATABASE non puo' girare dentro una transazione
--    (quindi non dentro un blocco DO, ne' dentro una funzione): l'idiom
--    psql per renderlo comunque idempotente e'
--      SELECT ... WHERE NOT EXISTS (...) \gexec
--    che genera il comando CREATE DATABASE come testo e lo esegue subito
--    dopo, fuori da blocco transazionale, solo se il database non esiste
--    ancora.
-- ---------------------------------------------------------------------
SELECT 'CREATE DATABASE identity_db OWNER identity'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'identity_db')\gexec

SELECT 'CREATE DATABASE tournament_db OWNER tournament'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tournament_db')\gexec

SELECT 'CREATE DATABASE team_roster_db OWNER "team-roster"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'team_roster_db')\gexec

SELECT 'CREATE DATABASE registration_db OWNER registration'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'registration_db')\gexec

SELECT 'CREATE DATABASE documents_db OWNER documents'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'documents_db')\gexec

SELECT 'CREATE DATABASE scoring_db OWNER scoring'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'scoring_db')\gexec

-- sport_rules_db NON compare qui: sport-rules usa MongoDB, non Postgres
-- (vedi servizio "mongo" nel docker-compose.yml).
