import json
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import parse_results

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

def load(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


class TestParseDirectFlights(unittest.TestCase):

    def setUp(self):
        self.data = load("sample_direct.json")
        self.flights = parse_results.parse_flights(self.data, target="PEK", search_type="direct")

    def test_returns_list(self):
        self.assertIsInstance(self.flights, list)

    def test_sorted_by_price_ascending(self):
        prices = [f["price"] for f in self.flights]
        self.assertEqual(prices, sorted(prices))

    def test_cheapest_is_2900(self):
        self.assertEqual(self.flights[0]["price"], 2900)

    def test_direct_flight_has_zero_stops(self):
        af_flight = next(f for f in self.flights if f["legs"][0]["flight_no"] == "AF129")
        self.assertEqual(af_flight["stops"], 0)

    def test_connecting_flight_has_one_stop(self):
        mu_flight = next(f for f in self.flights if f["legs"][0]["flight_no"] == "MU557")
        self.assertEqual(mu_flight["stops"], 1)

    def test_flight_record_has_required_keys(self):
        f = self.flights[0]
        for key in ("price", "legs", "stops", "is_hidden_city"):
            self.assertIn(key, f)

    def test_leg_has_required_keys(self):
        leg = self.flights[0]["legs"][0]
        for key in ("flight_no", "airline", "departure", "arrival", "from_code", "to_code"):
            self.assertIn(key, leg)

    def test_direct_flights_not_marked_hidden(self):
        # CA101 in the fixture transits PEK (PEK is an intermediate stop),
        # but search_type="direct" should still return it with is_hidden_city=False
        ca101 = next((f for f in self.flights if f["legs"][0]["flight_no"] == "CA101"), None)
        self.assertIsNotNone(ca101, "CA101 itinerary should be included in direct search results")
        self.assertFalse(ca101["is_hidden_city"])


class TestParseHiddenCityFlights(unittest.TestCase):

    def setUp(self):
        self.data = load("sample_hidden.json")
        self.flights = parse_results.parse_flights(self.data, target="PEK", search_type="hidden")

    def test_only_returns_itineraries_transiting_target(self):
        # sample_hidden has one itinerary transiting PEK and one direct CDG→PVG
        # Only the PEK-transiting one should be returned
        self.assertEqual(len(self.flights), 1)

    def test_hidden_flight_marked_as_hidden_city(self):
        self.assertTrue(self.flights[0]["is_hidden_city"])

    def test_hidden_flight_price(self):
        self.assertEqual(self.flights[0]["price"], 2600)

    def test_hidden_flight_first_leg_arrives_at_target(self):
        # The layover city (PEK) should appear as arrivalCityCode of some leg that is not the last
        legs = self.flights[0]["legs"]
        intermediate_arrivals = [leg["to_code"] for leg in legs[:-1]]
        self.assertIn("PEK", intermediate_arrivals)


class TestFormatResults(unittest.TestCase):

    def setUp(self):
        direct_data = load("sample_direct.json")
        hidden_data = load("sample_hidden.json")
        self.direct = parse_results.parse_flights(direct_data, target="PEK", search_type="direct")
        self.hidden = parse_results.parse_flights(hidden_data, target="PEK", search_type="hidden")
        self.output = parse_results.format_results(
            self.direct, self.hidden,
            origin="CDG", destination="PEK", date="2026-05-21"
        )

    def test_output_is_string(self):
        self.assertIsInstance(self.output, str)

    def test_output_contains_origin_and_destination(self):
        self.assertIn("CDG", self.output)
        self.assertIn("PEK", self.output)

    def test_output_contains_direct_section(self):
        self.assertIn("直飞", self.output)

    def test_output_contains_hidden_city_section(self):
        self.assertIn("隐藏城市", self.output)

    def test_output_contains_warning(self):
        self.assertIn("⚠️", self.output)

    def test_output_contains_cheapest_price(self):
        self.assertIn("2600", self.output)


class TestSSEParsing(unittest.TestCase):
    """Verify that SSE-format responses (data: prefix) are parsed correctly."""

    def test_load_response_sse_format(self):
        path = os.path.join(FIXTURES, "sample_direct_sse.txt")
        data = parse_results.load_response(path)
        self.assertIn("itineraryList", data)
        self.assertEqual(len(data["itineraryList"]), 2)

    def test_parse_flights_from_sse(self):
        path = os.path.join(FIXTURES, "sample_direct_sse.txt")
        data = parse_results.load_response(path)
        flights = parse_results.parse_flights(data, target="PEK", search_type="direct")
        self.assertEqual(len(flights), 2)
        self.assertEqual(flights[0]["price"], 2900)  # MU557 is cheaper

    def test_load_response_plain_json(self):
        path = os.path.join(FIXTURES, "sample_direct.json")
        data = parse_results.load_response(path)
        # Legacy fixture uses flightItineraryList inside data{}
        itineraries = (data.get("data", {}).get("flightItineraryList")
                       or data.get("data", {}).get("itineraryList")
                       or data.get("itineraryList", []))
        self.assertEqual(len(itineraries), 3)


if __name__ == "__main__":
    unittest.main()
