---
name: find-cheapest-flight
description: Search trip.com for cheapest flights between two cities, including hidden city (skiplag) opportunities. Usage: /find-cheapest-flight <origin> <destination> <date>
---

# Find Cheapest Flight

Search trip.com for the cheapest one-way flights from origin to destination on the given date.
Also finds hidden city (skiplag) tickets where the real destination is a layover stop.

---

## Step 1 — Parse input

Extract from the user's message:
- `ORIGIN_CODE`: origin IATA code
- `DEST_CODE`: destination IATA code
- `DATE`: travel date as YYYY-MM-DD

Common IATA codes:
| City | Code |
|------|------|
| 巴黎 / Paris | CDG |
| 北京 / Beijing | BJS (trip.com city group; covers PEK + PKX) |
| 上海 / Shanghai | SHA |
| 广州 / Guangzhou | CAN |
| 成都 / Chengdu | CTU |
| 深圳 / Shenzhen | SZX |
| 伦敦 / London | LHR |
| 纽约 / New York | NYC |

For hidden city search targeting Beijing specifically, use `PEK` as the `--target` flag
passed to parse_results.py (not BJS — the API returns PEK/PKX in individual leg codes).

---

## Step 2 — Direct flight search

Run these Chrome MCP steps:

1. **Check for an open page:**
   Call `list_pages`. If a page exists, use `select_page` with that page's ID.
   If no page exists, call `new_page`.

2. **Navigate to trip.com search:**
   Call `navigate_page` with this URL (substitute ORIGIN_CODE, DEST_CODE, DATE):
   ```
   https://www.trip.com/flights/ORIGIN_CODE-DEST_CODE-flight-ORIGIN_LOWER-DEST_LOWER/?dcity=ORIGIN_CODE&acity=DEST_CODE&ddate=DATE&triptype=ow&class=y&quantity=1
   ```
   Example for CDG→BJS on 2026-05-21:
   ```
   https://www.trip.com/flights/paris-beijing-flight-CDG-BJS/?dcity=CDG&acity=BJS&ddate=2026-05-21&triptype=ow&class=y&quantity=1
   ```

3. **Wait for results:**
   Call `wait_for` with a 10-second delay to allow the flight results to load.

4. **Find the batchSearch response:**
   Call `list_network_requests`. Look for a request whose URL contains `batchSearch`.
   Call `get_network_request` with that request's ID to retrieve the full response body.

5. **Save the response to a temp file:**
   Use the Bash tool to write the response body to `/tmp/flight_direct.json`.

6. **Parse the direct results:**
   ```bash
   python3 ~/.claude/skills/find-cheapest-flight/parse_results.py \
     --response /tmp/flight_direct.json \
     --target PEK \
     --type direct \
     --format json > /tmp/parsed_direct.json
   ```
   Read `/tmp/parsed_direct.json` and store as `direct_flights`.

---

## Step 3 — Hidden city search

Beijing is the real destination. Search onward cities and filter for itineraries
where PEK appears as an intermediate stop.

Onward destinations to search: `SHA`, `CAN`, `CTU`, `SZX`

For **each** onward city (repeat for all four):

1. **Navigate** to the search URL but with the onward city as `acity`:
   Example for CDG→SHA:
   ```
   https://www.trip.com/flights/paris-shanghai-flight-CDG-SHA/?dcity=CDG&acity=SHA&ddate=DATE&triptype=ow&class=y&quantity=1
   ```

2. **Wait** 8 seconds for results to load.

3. **Capture response** with `list_network_requests` + `get_network_request` (same as Step 2).

4. **Save and parse:**
   ```bash
   # Save response to /tmp/flight_hidden_SHA.json (use the onward city code)
   python3 ~/.claude/skills/find-cheapest-flight/parse_results.py \
     --response /tmp/flight_hidden_SHA.json \
     --target PEK \
     --type hidden \
     --format json > /tmp/parsed_hidden_SHA.json
   ```
   Append non-empty results to `hidden_flights` list.

Repeat for CAN, CTU, SZX.

**If any search returns an empty `data.flightItineraryList`, skip and continue.**
**If the batchSearch request is not found in network traffic after waiting, call `take_screenshot` to diagnose, then skip that leg.**

---

## Step 4 — Compile and display results

1. Merge all `direct_flights` results, deduplicate by `(flight_no, departure_time)`, sort by price ascending.
2. Merge all `hidden_flights` results, deduplicate by `(flight_no, departure_time)`, sort by price ascending.
3. Use the Bash tool to call format_results via parse_results.py, or format inline using the structure below.

Output format:
```
# ✈️  CDG → PEK   2026-05-21

## 直飞 / 普通中转
1. 🥇 MU557   CDG→PVG→PEK  10:00→09:15+1   ¥2,900  China Eastern  [经PVG中转]
2.    AF129   CDG→PEK       09:30→06:00+1   ¥3,200  Air France     [直飞]

## 隐藏城市票（仅乘前段落地北京，放弃后续航段）
1. 🔥 CA856   CDG→PEK→PVG  13:45→08:00+1   ¥2,600  Air China
   ⚠️ 警告：只能带随身行李；常旅客账户存在被航司处罚风险

(共找到 3 个结果)
```

If `hidden_flights` is empty, omit the hidden city section entirely.

---

## Notes

- **Session reuse:** Keep the same browser page across all 5 searches (1 direct + 4 hidden). This preserves session cookies so trip.com treats the requests as a single browsing session.
- **Rate limiting:** If trip.com returns empty results or shows a CAPTCHA, wait 3 seconds before the next navigation.
- **Response body size:** batchSearch responses can be large. If the response body appears truncated, try `evaluate_script` to read `window.__INITIAL_DATA__` or look for the data in a script tag via `take_snapshot`.
