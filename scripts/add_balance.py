import asyncio, asyncpg, os, sys
from dotenv import load_dotenv
load_dotenv()

async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    rows = await conn.fetch('SELECT id, name, token_granted, token_balance FROM users ORDER BY name')
    
    if '--apply' not in sys.argv:
        print("=== DRY RUN (pass --apply to execute) ===\n")
        total_add = 0
        for r in rows:
            add = int(r['token_granted'] * 0.3)
            total_add += add
            print(f"  {r['name']:20s}  granted={r['token_granted']:>12,}  balance={r['token_balance']:>12,}  +30%={add:>12,}  new_balance={r['token_balance']+add:>12,}")
        print(f"\n  Total to add: {total_add:,}")
    else:
        print("=== APPLYING ===\n")
        for r in rows:
            add = int(r['token_granted'] * 0.3)
            if add > 0:
                await conn.execute(
                    'UPDATE users SET token_balance = token_balance + $1, token_granted = token_granted + $1 WHERE id = $2',
                    add, r['id']
                )
                print(f"  {r['name']:20s}  +{add:>12,}  (new granted={r['token_granted']+add:,})")
            else:
                print(f"  {r['name']:20s}  skipped (granted=0)")
        print("\nDone!")
    
    await conn.close()

asyncio.run(main())
