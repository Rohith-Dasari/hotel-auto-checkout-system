import unittest
from datetime import datetime, timezone
from src.common.utils.datetime_normaliser import from_iso_string

class TestDatetimeNormaliser(unittest.TestCase):
    def test_from_iso_string_with_timezone(self):
        iso = "2026-01-29T12:00:00+05:30"
        dt = from_iso_string(iso)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.hour, 6)

    def test_from_iso_string_utc(self):
        iso = "2026-01-29T06:00:00+00:00"
        dt = from_iso_string(iso)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertEqual(dt.hour, 6)

    def test_from_iso_string_naive_raises(self):
        iso = "2026-01-29T12:00:00"
        with self.assertRaises(ValueError):
            from_iso_string(iso)

if __name__ == "__main__":
    unittest.main()
