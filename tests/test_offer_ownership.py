"""Contributor ownership of offer caps — cross-user PATCH denied; job overrides rejected."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gpu_swarm.portal_store import PortalStore
from gpu_swarm.scheduler import _FORBIDDEN_CAP_OVERRIDE_KEYS, _sanitize_job_payload


class OfferOwnershipTests(unittest.TestCase):
    def test_cross_user_machine_caps_update_denied(self) -> None:
        async def _run() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                store = PortalStore(Path(tmp) / "portal.db")
                await store.connect()
                try:
                    alice = await store.upsert_user("alice", "invite_code")
                    bob = await store.upsert_user("bob", "invite_code")
                    alice_machine = await store.create_machine(
                        alice["id"],
                        {
                            "worker_name": "alice-pc",
                            "scheduler_url": "http://127.0.0.1:8766",
                            "max_vram_mb": 2048,
                            "max_cpu_percent": 40,
                            "dedicated_ram_mb": 4096,
                            "dedicated_disk_mb": 10240,
                            "dedicated_cpu_cores": 2,
                        },
                    )
                    bob_machine = await store.create_machine(
                        bob["id"],
                        {
                            "worker_name": "bob-pc",
                            "scheduler_url": "http://127.0.0.1:8766",
                            "max_vram_mb": 1024,
                            "max_cpu_percent": 25,
                            "dedicated_ram_mb": 2048,
                            "dedicated_disk_mb": 5120,
                            "dedicated_cpu_cores": 1,
                        },
                    )

                    # Owner can raise/lower their own offer.
                    updated = await store.update_machine_caps(
                        alice_machine["id"],
                        alice["id"],
                        {"max_vram_mb": 3072, "max_cpu_percent": 55},
                    )
                    self.assertIsNotNone(updated)
                    assert updated is not None
                    self.assertEqual(updated["max_vram_mb"], 3072)
                    self.assertEqual(updated["max_cpu_percent"], 55.0)

                    # Bob cannot raise Alice's offer.
                    with self.assertRaises(PermissionError):
                        await store.update_machine_caps(
                            alice_machine["id"],
                            bob["id"],
                            {"max_vram_mb": 24576, "max_cpu_percent": 100},
                        )

                    # Alice's caps unchanged after Bob's attempt.
                    still = await store.get_machine(alice_machine["id"])
                    assert still is not None
                    self.assertEqual(still["max_vram_mb"], 3072)
                    self.assertEqual(still["max_cpu_percent"], 55.0)

                    # Alice cannot edit Bob's machine either.
                    with self.assertRaises(PermissionError):
                        await store.update_machine_caps(
                            bob_machine["id"],
                            alice["id"],
                            {"max_vram_mb": 99999},
                        )
                    bob_still = await store.get_machine(bob_machine["id"])
                    assert bob_still is not None
                    self.assertEqual(bob_still["max_vram_mb"], 1024)
                finally:
                    await store.close()

        asyncio.run(_run())

    def test_job_payload_cannot_force_worker_caps(self) -> None:
        from fastapi import HTTPException

        clean = _sanitize_job_payload({"matrix_size": 512})
        self.assertEqual(clean["matrix_size"], 512)

        for key in sorted(_FORBIDDEN_CAP_OVERRIDE_KEYS)[:6]:
            with self.assertRaises(HTTPException) as ctx:
                _sanitize_job_payload({key: 99999, "matrix_size": 256})
            self.assertEqual(ctx.exception.status_code, 400)

        with self.assertRaises(HTTPException) as ctx:
            _sanitize_job_payload({"force_caps": {"max_vram_mb": 99999}})
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("offer caps", str(ctx.exception.detail).lower())


if __name__ == "__main__":
    unittest.main()
