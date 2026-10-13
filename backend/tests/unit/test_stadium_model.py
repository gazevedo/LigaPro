import unittest
from datetime import UTC, datetime, timedelta

from app.config.stadium import DEFAULT_FACILITIES, STADIUM_LEVELS, effects, sectors
from app.services.fan_base import FanBaseService
from app.services.physical_condition import PhysicalConditionService


class StadiumModelTests(unittest.TestCase):
    def test_sector_capacity_always_adds_to_stadium_capacity(self):
        for capacity in (1000, 10000, 11000, 20000, 30000, 45000, 60000, 80000, 120000):
            stadium = dict(
                capacity=capacity,
                ticket_price=2000,
                facilities={key: 5 for key in DEFAULT_FACILITIES},
            )
            rows = sectors(stadium)
            self.assertEqual(sum(row["capacity"] for row in rows), capacity)
            self.assertTrue(all(row["capacity"] >= 0 for row in rows))
        self.assertEqual(
            [level[2] for level in STADIUM_LEVELS], [10000, 20000, 30000, 45000, 60000, 80000]
        )

    def test_planned_sectors_unlock_progressively(self):
        local = sectors(dict(capacity=10000, ticket_price=2000))
        self.assertTrue(
            all(
                not row["available"]
                for row in local
                if row["id"].startswith("upper") or row["id"] == "skybox"
            )
        )
        regional = sectors(dict(capacity=30000, ticket_price=2000))
        self.assertTrue(all(row["available"] for row in regional if row["id"].startswith("upper")))
        self.assertFalse(next(row for row in regional if row["id"] == "skybox")["available"])

    def test_uniform_prices_preserve_previous_attendance_and_income(self):
        club = dict(supporters=10000, fan_satisfaction=50, reputation=10)
        stadium = dict(capacity=10000, ticket_price=2000)
        expected = FanBaseService.attendance(club, stadium)
        rows = FanBaseService.sector_ticketing(club, stadium)
        self.assertEqual(sum(row["attendance"] for row in rows), expected)
        self.assertEqual(sum(row["income"] for row in rows), expected * 2000)
        self.assertTrue(all(0 <= row["attendance"] <= row["capacity"] for row in rows))

    def test_expensive_sector_reduces_only_its_demand_and_respects_capacity(self):
        club = dict(supporters=10000, fan_satisfaction=50, reputation=10)
        stadium = dict(capacity=10000, ticket_price=2000)
        baseline = FanBaseService.sector_ticketing(club, stadium)
        changed = FanBaseService.sector_ticketing(
            club, {**stadium, "sector_prices": {"lower_north": 10000}}
        )
        a = next(r for r in baseline if r["id"] == "lower_north")
        b = next(r for r in changed if r["id"] == "lower_north")
        self.assertLess(b["attendance"], a["attendance"])
        self.assertTrue(all(row["income"] == row["attendance"] * row["price"] for row in changed))

    def test_training_fitness_and_commercial_effects_are_bounded(self):
        maximum = effects({"facilities": {key: 99 for key in DEFAULT_FACILITIES}})
        self.assertEqual(maximum["training_extra"], 3)
        self.assertEqual(maximum["energy_bonus"], 5)
        self.assertEqual(maximum["recovery_bonus"], 2.5)
        self.assertAlmostEqual(maximum["attendance_bonus"], 0.17)
        self.assertEqual(effects({})["services_income_per_attendee"], 0)
        now = datetime(2026, 10, 13, tzinfo=UTC)
        player = dict(
            age=22, physical_condition=20, energy=20, condition_updated_at=now - timedelta(days=1)
        )
        base = PhysicalConditionService().recover(player, now)
        upgraded = PhysicalConditionService().recover(
            player, now, recovery_bonus=2.5, energy_bonus=5
        )
        self.assertGreater(upgraded["energy"], base["energy"])
        self.assertGreater(upgraded["physical_condition"], base["physical_condition"])


if __name__ == "__main__":
    unittest.main()
