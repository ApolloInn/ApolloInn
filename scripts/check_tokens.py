#!/usr/bin/env python3
import asyncio, subprocess
import httpx

def get_tokens():
    result = subprocess.run(
        ["sudo", "-u", "postgres", "psql", "-d", "apollo", "-t", "-A", "-c",
         "SELECT email, refresh_token FROM cursor_tokens WHERE status='active' ORDER BY email"],
        capture_output=True, text=True
    )
    tokens = []
    for line in result.stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|")
            tokens.append((parts[0], parts[1]))
    return tokens

async def check(email, token):
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post("https://api2.cursor.sh/oauth/token", json={
            "client_id": "KbZUR41cY7W6zRSdpSUJ7I7mLYBKOCmB",
            "grant_type": "refresh_token",
            "refresh_token": token,
        })
        data = r.json()
        if data.get("shouldLogout"):
            return email, "DEAD"
        if data.get("access_token"):
            return email, "OK"
        return email, f"ERR:{r.status_code}"

async def main():
    tokens = get_tokens()
    print(f"Checking {len(tokens)} accounts...")
    tasks = [check(e, t) for e, t in tokens]
    results = await asyncio.gather(*tasks)
    ok = 0
    for email, status in sorted(results):
        icon = "OK" if status == "OK" else "FAIL"
        if status == "OK":
            ok += 1
        print(f"  [{icon}] {email}: {status}")
    print(f"\nResult: {ok}/{len(tokens)} valid")

asyncio.run(main())
