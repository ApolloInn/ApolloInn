#!/usr/bin/env python3
"""
Apollo DB -> Supabase periodic backup script.
Syncs all tables incrementally. Usage_records uses max(id) for incremental sync.
Other tables do full replace (small enough).
"""
import asyncio, asyncpg, sys
from datetime import datetime

LOCAL_DSN = "postgresql://apollo:Apollo_2025@localhost:5432/apollo"
SUPA_DSN = "postgresql://postgres.aovjqzzojslkzkztgzja:Apollo_inn_2025@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

SMALL_TABLES = [
    'admin_config', 'tokens', 'users', 'promax_keys', 'agents',
    'model_mappings', 'cursor_tokens', 'user_apikeys', 'token_transactions'
]

BATCH = 5000

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

async def sync_small_tables(local, supa):
    for table in SMALL_TABLES:
        cols = await local.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name=$1 AND table_schema='public' ORDER BY ordinal_position", table)
        col_names = [c['column_name'] for c in cols]
        col_list = ', '.join(col_names)
        placeholders = ', '.join(f'${i+1}' for i in range(len(col_names)))

        rows = await local.fetch(f'SELECT {col_list} FROM {table}')

        await supa.execute(f'DELETE FROM {table}')
        if rows:
            await supa.executemany(
                f'INSERT INTO {table} ({col_list}) VALUES ({placeholders})',
                [tuple(r[c] for c in col_names) for r in rows]
            )
        log(f"  {table}: {len(rows)} rows synced")

async def sync_usage_records(local, supa):
    supa_max = await supa.fetchval('SELECT COALESCE(max(id), 0) FROM usage_records')
    local_total = await local.fetchval('SELECT count(*) FROM usage_records WHERE id > $1', supa_max)
    log(f"  usage_records: {local_total} new rows (after id={supa_max})")

    if local_total == 0:
        log("  usage_records: already up to date")
        return

    offset = 0
    inserted = 0
    while True:
        rows = await local.fetch(
            'SELECT id, user_id, model, prompt_tokens, completion_tokens, token_id, recorded_at '
            'FROM usage_records WHERE id > $1 ORDER BY id LIMIT $2 OFFSET $3',
            supa_max, BATCH, offset)
        if not rows:
            break

        await supa.executemany(
            'INSERT INTO usage_records (id, user_id, model, prompt_tokens, completion_tokens, token_id, recorded_at) '
            'VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (id) DO NOTHING',
            [(r['id'], r['user_id'], r['model'], r['prompt_tokens'], r['completion_tokens'], r['token_id'], r['recorded_at']) for r in rows]
        )
        inserted += len(rows)
        offset += BATCH

    max_id = await local.fetchval('SELECT max(id) FROM usage_records')
    if max_id:
        await supa.execute(f"SELECT setval('usage_records_id_seq', {max_id})")

    log(f"  usage_records: {inserted} rows synced")

async def main():
    log("Backup started")
    try:
        local = await asyncpg.connect(LOCAL_DSN)
        supa = await asyncpg.connect(SUPA_DSN)

        log("Syncing small tables...")
        await sync_small_tables(local, supa)

        log("Syncing usage_records (incremental)...")
        await sync_usage_records(local, supa)

        await local.close()
        await supa.close()
        log("Backup completed successfully")
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

asyncio.run(main())
