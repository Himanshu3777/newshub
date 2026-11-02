# NewsHub — Backup Plan

Data is the product. Three independent layers, so no single failure loses it.

## Layer 1 — Code (automatic)
All code lives in GitHub (`Himanshu3777/newshub`), updated with every change.
A lost machine loses zero code.

## Layer 2 — Application backup (JSON, built-in)
Command: `python manage.py backup_data`
- Writes `backups/newshub-backup-<YYYYMMDD-HHMMSS>.json` (sources, articles,
  verification, moderation, feedback, AI-router usage/logs).
- Contains **no secrets** (keys are environment variables, never model data).
- **When:** before every migration/deploy, and weekly.
- **Restore:** `python manage.py loaddata backups/<file>.json`
  (verified by an automated roundtrip test: backup → wipe → restore → counts match).
- Keep the last **4 weekly** files; copy one off-machine (Drive/pen drive).

## Layer 3 — Database-native backup (PostgreSQL)
### Local PC (pgAdmin PostgreSQL, database `newshub`)
Weekly, from cmd (adjust the path/version):
```
pg_dump -U newshub_app -h localhost -d newshub -F c -f "%USERPROFILE%\Desktop\newshub-%DATE%.dump"
```
Restore: `pg_restore -U newshub_app -h localhost -d newshub_restore <file>.dump`
(First restore into a scratch database, verify counts, then swap.)

### Production (Neon, after deploy)
- Neon keeps automatic backups/history per its plan (check the console's
  Backups tab — retention depends on the free plan).
- Still take a Layer-2 JSON backup before every deploy: it is portable
  across providers, Neon exports are not.

## Schedule summary
| What | When | Who |
|---|---|---|
| Code push to GitHub | every change | automatic (with development) |
| `backup_data` JSON | weekly + before deploy/migration | one command |
| `pg_dump` (local PC) | weekly | one command (can be Task-Scheduler automated) |
| `validate_data --strict` | after every restore | one command — must print "Data integrity OK" |

## Restore drill (do once, then quarterly)
1. Take a fresh backup. 2. Restore into a scratch DB. 3. Run
`validate_data --strict` and open the home page. 4. Only then trust the backup.
An untested backup is not a backup.
