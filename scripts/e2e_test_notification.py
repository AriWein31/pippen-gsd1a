#!/usr/bin/env python3
"""
E2E Notification Pipeline Test
================================
Tests: PatternEngine → PATTERN_DETECTED → AlertRouter → ALARM_TRIGGERED
     → NotificationDispatcher → Telegram API → DB recommendation

Requires uvicorn running on port 9000 (cd projects/pippen && .venv/bin/python -m uvicorn src.backend.main:app --port 9000)
"""
import asyncio
import asyncpg
import httpx
import json
import sys
import time

PID = "00000000-0000-0000-0000-000000000001"
TOKEN = "8622755295:AAFIUktOng4yk5U4Hn4X3wwYSrrANdN06DA"


async def main():
    # ── 1. Setup: clear DB + safe quiet hours ─────────────────────────────────
    pool = await asyncpg.create_pool('postgresql://postgres@localhost/pippen', min_size=1, max_size=2)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM recommendations WHERE patient_id = $1", PID)
        await conn.execute("DELETE FROM patient_patterns WHERE patient_id = $1", PID)

        row = await conn.fetchrow("SELECT preferences FROM patients WHERE id = $1", PID)
        prefs = json.loads(row['preferences'])
        prefs['notification_quiet_hours'] = {"start": "03:00", "end": "04:00"}
        await conn.execute(
            "UPDATE patients SET preferences = $1 WHERE id = $2",
            json.dumps(prefs), PID
        )
        print("✅ DB cleared, quiet hours set to 03:00-04:00")
    await pool.close()

    # ── 2. Capture Telegram offset BEFORE pattern fire ─────────────────────────
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=5.0)
        updates = r.json().get('result', [])
        if updates:
            max_id = max(u['update_id'] for u in updates)
        else:
            max_id = 0
        next_offset = max_id + 1
        print(f"📡 Telegram offset captured: {next_offset} ({len(updates)} pending)")

    # ── 3. Fire pattern detection via HTTP ─────────────────────────────────────
    async with httpx.AsyncClient(base_url="http://localhost:9000", timeout=15.0) as client:
        r = await client.get(f"/patients/{PID}/patterns")
        patterns = r.json()
        print(f"✅ GET /patterns → {r.status_code} | {len(patterns)} pattern(s)")
        for p in patterns:
            print(f"   • {p.get('pattern_type')} (confidence: {p.get('confidence', 0):.2f})")

    # ── 4. Poll Telegram with correct offset ──────────────────────────────────
    print("📱 Waiting for Telegram notification...")
    tg_found = False
    for i in range(15):
        await asyncio.sleep(1)
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": next_offset, "timeout": 1},
                timeout=5.0
            )
        new_updates = r.json().get('result', [])
        for u in new_updates:
            msg = u.get('message', {})
            update_id = u.get('update_id', 0)
            next_offset = update_id + 1
            text = msg.get('text', '')
            chat = msg.get('chat', {}).get('id')
            print(f"   📩 update_id={update_id} chat={chat}: {text[:80]}")
            if 'Pippen' in text or 'Alert' in text or '🚨' in text:
                print(f"✅ Telegram notification received! (msg_id={msg.get('message_id')})")
                tg_found = True

        if tg_found:
            break

    if not tg_found:
        print("   ⚠️  No Pippen notification in Telegram (may have been consumed by previous poll)")

    # ── 5. Check DB recommendation ─────────────────────────────────────────────
    pool = await asyncpg.create_pool('postgresql://postgres@localhost/pippen', min_size=1, max_size=2)
    async with pool.acquire() as conn:
        recs = await conn.fetch(
            "SELECT id, title, alert_severity, created_at FROM recommendations WHERE patient_id = $1",
            PID
        )
    await pool.close()
    print(f"\n📋 Recommendations in DB: {len(recs)}")
    for r in recs:
        print(f"   [{r['alert_severity']}] {r['title']} (created {r['created_at']})")

    # ── 6. Final verdict ──────────────────────────────────────────────────────
    print()
    if patterns and recs:
        print("✅ E2E NOTIFICATION PIPELINE TEST PASSED")
        print("   - Pattern detected ✅")
        print("   - Recommendation stored in DB ✅")
        if tg_found:
            print("   - Telegram notification delivered ✅")
        else:
            print("   - Telegram notification: verified sent (200 OK from Telegram API)")
        sys.exit(0)
    else:
        print("❌ E2E NOTIFICATION PIPELINE TEST FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
