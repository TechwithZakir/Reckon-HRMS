"""Unit tests for the geofence rule."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from reckon_hrms.geo import distance_m, within_geofence  # noqa: E402

DHAKA = (23.8103, 90.4125)


class GeoTests(unittest.TestCase):
    def test_same_point_is_zero(self):
        self.assertAlmostEqual(distance_m(*DHAKA, *DHAKA), 0.0, places=6)

    def test_known_distance_dhaka_to_chattogram(self):
        d = distance_m(23.8103, 90.4125, 22.3569, 91.7832)
        self.assertTrue(205_000 < d < 220_000, d)

    def test_inside_radius(self):
        inside, d = within_geofence(23.8105, 90.4127, *DHAKA, 150)
        self.assertTrue(inside)
        self.assertLess(d, 150)

    def test_outside_radius(self):
        inside, _ = within_geofence(23.8200, 90.4125, *DHAKA, 150)
        self.assertFalse(inside)

    def test_missing_position_is_not_inside(self):
        self.assertFalse(within_geofence(None, None, *DHAKA, 150)[0])

    def test_invalid_coordinates_rejected(self):
        self.assertFalse(within_geofence(120.0, 90.4, *DHAKA, 150)[0])

    def test_default_radius_applies(self):
        self.assertTrue(within_geofence(23.8103, 90.4126, *DHAKA, None)[0])


if __name__ == "__main__":
    unittest.main()
