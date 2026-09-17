# Moving from the old layout

| Old | New |
|---|---|
| `collectors/*.py` | `ingest/exchanges/*.py` (now use the template) |
| `core/symbols.py`, `core/validate.py` | `ingest/` |
| `core/db.py` | `storage/db.py` |
| `core/auth.py` | `serve/auth.py` |
| `api/main.py` | `serve/main.py` |
| `db/*.sql` | `storage/migrations/00N_*.sql` |
| `scripts/run_forever.py` | `ingest/worker.py` |
| `python3 scripts/x.py` | `python3 -m scripts.x` |

New in this version: freshness fields on `/v1/ticker`, `/v1/status`
endpoint, `exchange_status` table (migration 005), `symbol_std` in
`/v1/markets`, database check in `/v1/health`, all settings in
`shared/config.py`, offline tests, history filter + daily
clean-up (`prices_daily`, migration 006), `db_size` and `cleanup`
scripts, `setup_mac.sh`.

Note: `/v1/markets` entries now use `symbol` = standard form
(BTC-USDT) and `exchange_symbol` = the exchange's own spelling.
Anything already calling `/v1/markets` should be checked.
