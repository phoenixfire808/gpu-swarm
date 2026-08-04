"""Unit tests for Contribute offer → VM resource mapping (no VirtualBox / no GPU stress)."""

from __future__ import annotations

import unittest

from gpu_swarm.agent_vm_bridge import compute_vm_resource_plan
from gpu_swarm.joiner_settings import JoinerSettings


class AgentVmBridgeMappingTests(unittest.TestCase):
    def test_maps_cpu_percent_and_ram_offer(self) -> None:
        settings = JoinerSettings(
            max_cpu_percent=50.0,
            max_ram_mb=4096,
            max_vram_mb=8000,
            host_protect=True,
        )
        host = {
            "cpu_cores": 16,
            "ram_total_mb": 32768,
            "ram_available_mb": 20000,
        }
        plan = compute_vm_resource_plan(
            settings,
            host=host,
            total_vram_mb=16384,
            free_vram_mb=12000,
        )
        self.assertEqual(plan["cpus"], 8)  # 50% of 16 → 8, capped at MAX_VM_CPUS
        self.assertEqual(plan["memory_mb"], 4096)
        self.assertEqual(plan["display_vram_mb"], 64)
        # host_protect clamps VRAM offer; recorded but not applied to VM
        self.assertLessEqual(plan["offer"]["max_vram_mb"], 16384)
        self.assertIn("contributor worker", plan["gpu_note"].lower())

    def test_host_protect_clamps_cpu_offer(self) -> None:
        settings = JoinerSettings(
            max_cpu_percent=95.0,
            max_ram_mb=8192,
            host_protect=True,
        )
        host = {
            "cpu_cores": 8,
            "ram_total_mb": 16384,
            "ram_available_mb": 12000,
        }
        plan = compute_vm_resource_plan(settings, host=host)
        # host_protect default max_cpu_percent = 70
        self.assertLessEqual(plan["offer"]["max_cpu_percent"], 70.0)
        self.assertLessEqual(plan["cpus"], 5)  # 70% of 8 → 5, leave 1 host CPU
        self.assertEqual(plan["memory_mb"], 8192)

    def test_auto_ram_leaves_host_reserve(self) -> None:
        settings = JoinerSettings(
            max_cpu_percent=50.0,
            max_ram_mb=0,
            host_protect=False,
        )
        host = {
            "cpu_cores": 4,
            "ram_total_mb": 8192,
            "ram_available_mb": 4000,
        }
        plan = compute_vm_resource_plan(settings, host=host)
        self.assertGreaterEqual(plan["memory_mb"], 1024)
        self.assertLessEqual(plan["memory_mb"], 4000 - 2048)

    def test_never_claims_whole_machine_cpus(self) -> None:
        settings = JoinerSettings(max_cpu_percent=100.0, host_protect=False)
        host = {"cpu_cores": 4, "ram_total_mb": 16384, "ram_available_mb": 12000}
        plan = compute_vm_resource_plan(settings, host=host)
        self.assertLess(plan["cpus"], 4)


if __name__ == "__main__":
    unittest.main()
