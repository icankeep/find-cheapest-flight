"""
parse_results.py — Parse trip.com batchSearch JSON response into formatted flight list.

Usage:
    python3 parse_results.py --response /tmp/flight.json --target PEK --type direct
    python3 parse_results.py --response /tmp/flight.json --target PEK --type hidden

Prints JSON array of flight records to stdout.
Use --format human to print the human-readable table instead.
"""
import json
import argparse


def parse_flights(data: dict, target: str, search_type: str) -> list:
    """
    Parse batchSearch response dict into a sorted list of flight records.

    Args:
        data:        Parsed JSON from batchSearch API response.
        target:      IATA airport code of the real destination (e.g. "PEK").
        search_type: "direct" — return all itineraries (no filtering).
                     "hidden" — return only itineraries where `target` is
                                an intermediate stop (not the final destination).

    Returns:
        List of flight record dicts, sorted by price ascending.
    """
    itineraries = (
        data.get("data", {}).get("flightItineraryList", [])
    )
    flights = []

    for itinerary in itineraries:
        price_list = itinerary.get("priceList", [])
        if not price_list:
            continue
        price = price_list[0].get("adultPrice", 0)

        segments = itinerary.get("flightSegments", [])
        if not segments:
            continue

        raw_legs = segments[0].get("flightList", [])
        if not raw_legs:
            continue

        legs = [
            {
                "flight_no": leg.get("flightNo", ""),
                "airline": leg.get("marketAirlineName", ""),
                "from_code": leg.get("departureCityCode", ""),
                "to_code": leg.get("arrivalCityCode", ""),
                "departure": leg.get("departureDateTime", ""),
                "arrival": leg.get("arrivalDateTime", ""),
            }
            for leg in raw_legs
        ]

        # For hidden city: target must appear as an intermediate arrival (not the final leg)
        intermediate_arrivals = [leg["to_code"] for leg in legs[:-1]]
        is_hidden_city = search_type == "hidden" and target in intermediate_arrivals

        if search_type == "hidden" and not is_hidden_city:
            continue

        flights.append({
            "price": price,
            "legs": legs,
            "stops": len(legs) - 1,
            "is_hidden_city": is_hidden_city,
        })

    return sorted(flights, key=lambda f: f["price"])


def format_results(
    direct_flights: list,
    hidden_flights: list,
    origin: str,
    destination: str,
    date: str,
) -> str:
    lines = [f"# ✈️  {origin} → {destination}   {date}", ""]

    lines.append("## 直飞 / 普通中转")
    if not direct_flights:
        lines.append("(无结果)")
    for i, f in enumerate(direct_flights[:10], 1):
        first, last = f["legs"][0], f["legs"][-1]
        medal = "🥇 " if i == 1 else "   "
        if f["stops"] == 0:
            stop_label = "直飞"
        else:
            via = f["legs"][0]["to_code"]
            stop_label = f"经{via}中转"
        lines.append(
            f"{i}. {medal}{first['flight_no']}  "
            f"{first['from_code']}→{last['to_code']}  "
            f"{first['departure']}→{last['arrival']}  "
            f"¥{f['price']}  {first['airline']}  [{stop_label}]"
        )

    if hidden_flights:
        lines.append("")
        lines.append("## 隐藏城市票（仅乘第一程落地目的地，放弃后续航段）")
        for i, f in enumerate(hidden_flights[:5], 1):
            first = f["legs"][0]
            route_parts = [first["from_code"]] + [leg["to_code"] for leg in f["legs"]]
            route = "→".join(route_parts)
            medal = "🔥 " if i == 1 else "   "
            lines.append(
                f"{i}. {medal}{first['flight_no']}  "
                f"{route}  "
                f"{first['departure']}→{f['legs'][-1]['arrival']}  "
                f"¥{f['price']}  {first['airline']}"
            )
            lines.append("   ⚠️ 警告：只能带随身行李；常旅客账户存在被航司处罚风险")

    lines.append("")
    total = len(direct_flights) + len(hidden_flights)
    lines.append(f"(共找到 {total} 个结果)")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--response", required=True, help="Path to batchSearch JSON response file")
    parser.add_argument("--target", required=True, help="Target airport IATA code, e.g. PEK")
    parser.add_argument("--type", dest="search_type", default="direct",
                        choices=["direct", "hidden"])
    parser.add_argument("--format", default="json", choices=["json", "human"])
    parser.add_argument("--origin", default="")
    parser.add_argument("--destination", default="")
    parser.add_argument("--date", default="")
    args = parser.parse_args()

    with open(args.response) as f:
        data = json.load(f)

    flights = parse_flights(data, target=args.target, search_type=args.search_type)

    if args.format == "json":
        print(json.dumps(flights, ensure_ascii=False, indent=2))
    else:
        direct = flights if args.search_type == "direct" else []
        hidden = flights if args.search_type == "hidden" else []
        print(format_results(direct, hidden, args.origin, args.destination, args.date))
