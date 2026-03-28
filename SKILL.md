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
| 城市 / City | 代码 | 机场中文名 |
|-------------|------|-----------|
| 巴黎 / Paris | CDG | 戴高乐机场 |
| 北京 / Beijing | BJS | trip.com城市组，含首都(PEK)和大兴(PKX) |
| 北京首都 | PEK | 北京首都国际机场 |
| 北京大兴 | PKX | 北京大兴国际机场 |
| 上海 / Shanghai | SHA | 虹桥国际机场 |
| 上海浦东 | PVG | 浦东国际机场 |
| 广州 / Guangzhou | CAN | 白云国际机场 |
| 成都 / Chengdu | CTU | 天府国际机场 |
| 深圳 / Shenzhen | SZX | 宝安国际机场 |
| 重庆 / Chongqing | CKG | 江北国际机场 |
| 西安 / Xi'an | XIY | 咸阳国际机场 |
| 武汉 / Wuhan | WUH | 天河国际机场 |
| 昆明 / Kunming | KMG | 长水国际机场 |
| 杭州 / Hangzhou | HGH | 萧山国际机场 |
| 南京 / Nanjing | NKG | 禄口国际机场 |
| 香港 / Hong Kong | HKG | 香港国际机场 |
| 台北 / Taipei | TPE | 桃园国际机场 |
| 首尔 / Seoul | ICN | 仁川国际机场 |
| 东京 / Tokyo | NRT | 成田国际机场 |
| 东京羽田 | HND | 羽田国际机场 |
| 新加坡 / Singapore | SIN | 樟宜机场 |
| 曼谷 / Bangkok | BKK | 素万那普机场 |
| 迪拜 / Dubai | DXB | 迪拜国际机场 |
| 阿布扎比 / Abu Dhabi | AUH | 阿布扎比国际机场 |
| 伦敦 / London | LHR | 希思罗机场 |
| 法兰克福 / Frankfurt | FRA | 法兰克福机场 |
| 阿姆斯特丹 / Amsterdam | AMS | 史基浦机场 |
| 纽约 / New York | NYC | 城市组，含JFK/EWR/LGA |
| 洛杉矶 / Los Angeles | LAX | 洛杉矶国际机场 |
| 悉尼 / Sydney | SYD | 金斯福德·史密斯机场 |

For hidden city search targeting Beijing specifically, use `PEK` as the `--target` flag
passed to parse_results.py (not BJS — the API returns PEK/PKX in individual leg codes).

---

## Step 2 — Direct flight search

1. **Check for an open page:**
   Call `list_pages`. If a page exists, use `select_page` with that page's ID.
   If no page exists, call `new_page`.

2. **Navigate to trip.com search:**
   Use the `showfarefirst` URL format (verified working as of 2026-03):
   ```
   https://www.trip.com/flights/showfarefirst?dcity=ORIGIN_LOWER&acity=DEST_LOWER&ddate=DATE&triptype=ow&class=y&quantity=1&locale=en-XX&curr=CNY
   ```
   Where `ORIGIN_LOWER` / `DEST_LOWER` are the IATA codes in **lowercase** (e.g. `cdg`, `bjs`).

   Example for CDG→BJS on 2026-05-21:
   ```
   https://www.trip.com/flights/showfarefirst?dcity=cdg&acity=bjs&ddate=2026-05-21&triptype=ow&class=y&quantity=1&locale=en-XX&curr=CNY
   ```

   **If the page shows 404 or no results after 10 seconds**, fall back to UI automation:
   navigate to `https://www.trip.com/flights/`, click the Flights tab, fill in the form,
   and click Search.

3. **Wait for results:**
   Call `wait_for` with text `["flights found", "¥", "$"]` and a 10-second timeout.

4. **Find the FlightListSearchSSE response:**
   Call `list_network_requests`. The `FlightListSearchSSE` request is almost always one of
   the **most recent** requests (highest reqid). Check the last page of results first, or
   scan for `FlightListSearchSSE` in the URL column — do NOT page through all 300+ entries.
   Call `get_network_request` with `responseFilePath` to save directly:
   ```
   responseFilePath: /tmp/flight_direct.json
   ```

5. **Parse the direct results:**
   ```bash
   python3 ~/.claude/skills/find-cheapest-flight/parse_results.py \
     --response /tmp/flight_direct.json \
     --target PEK \
     --type direct \
     --format json > /tmp/parsed_direct.json
   ```
   Read `/tmp/parsed_direct.json` and store as `direct_flights`.

---

## Step 3 — Hidden city search (parallel tabs)

Beijing is the real destination. Search onward cities and filter for itineraries
where PEK appears as an intermediate stop.

Onward destinations to search: `SHA`, `CAN`, `CTU`, `SZX`

### Phase A — Launch all 4 searches simultaneously (no waiting yet)

Open a **new tab for each** onward city and navigate immediately. Record each page ID.

```
tab_SHA = new_page → navigate_page: https://www.trip.com/flights/showfarefirst?dcity=ORIGIN_LOWER&acity=sha&ddate=DATE&triptype=ow&class=y&quantity=1&locale=en-XX&curr=CNY
tab_CAN = new_page → navigate_page: ...acity=can...
tab_CTU = new_page → navigate_page: ...acity=ctu...
tab_SZX = new_page → navigate_page: ...acity=szx...
```

Then call `wait_for` **once** with 10-second timeout — this single wait covers all 4 tabs
loading in parallel in the background.

### Phase B — Collect results from each tab

For each tab (SHA, CAN, CTU, SZX):
1. `select_page` with the tab's page ID
2. `list_network_requests` — find the `FlightListSearchSSE` request (highest reqid)
3. `get_network_request` with `responseFilePath: /tmp/flight_hidden_SHA.json` (use city code)
4. Parse:
   ```bash
   python3 ~/.claude/skills/find-cheapest-flight/parse_results.py \
     --response /tmp/flight_hidden_SHA.json \
     --target PEK \
     --type hidden \
     --format json > /tmp/parsed_hidden_SHA.json
   ```
5. Append non-empty results to `hidden_flights` list.
6. `close_page` to clean up the tab.

**If a tab's FlightListSearchSSE is not found:** call `take_screenshot` to diagnose, then skip.
**If trip.com shows a CAPTCHA on any tab:** close that tab, wait 3 seconds, re-open as a new page.

---

## Step 4 — Compile and display results

1. Merge all `direct_flights`, deduplicate by `(flight_no, departure_time)`, sort by price ascending.
2. Merge all `hidden_flights`, deduplicate by `(flight_no, departure_time)`, sort by price ascending.

Output format:
```
# ✈️  CDG → PEK   2026-05-21

## 直飞 / 普通中转
1. 🥇 MU557   CDG→PVG→PEK  ¥2,900  China Eastern  总时长15h30m
   ├ MU557  CDG(巴黎戴高乐) 10:00 → PVG(上海浦东) 05:30+1  [13h30m]
   └ MU5129 PVG(上海浦东) 07:30 → PEK(北京首都) 09:15  [1h45m，候机2h]

2.    AF129   CDG→PEK  ¥3,200  Air France  总时长10h  [直飞]
   └ AF129  CDG(巴黎戴高乐) 09:30 → PEK(北京首都) 06:00+1  [10h30m]

## 隐藏城市票（仅乘前段落地北京，放弃后续航段）
1. 🔥 CA856   CDG→PEK→PVG  ¥2,600  Air China
   ├ CA856  CDG(巴黎戴高乐) 13:45 → PEK(北京首都T3) 08:00+1  [落地即下机]
   └ ~~CA857 PEK→PVG 10:30~~  ← 放弃此段
   ⚠️ 警告：只能带随身行李；常旅客账户存在被航司处罚风险

(共找到 3 个结果)
```

**关键要求：**
- 每段航班单独一行，显示：航班号、出发机场代码+中文名、本地出发时间、到达机场代码+中文名、本地到达时间、飞行时长
- 中转等待时间标注在换乘行（"候机Xh Xm"）
- 价格统一用人民币 ¥，不显示美元
- 跨天到达标注 +1 / +2

If `hidden_flights` is empty, omit the hidden city section entirely.

---

## Notes

- **URL format:** The `showfarefirst` URL with lowercase city codes is the verified working format. The old slug-based URL (`/flights/paris-beijing-flight-CDG-BJS/`) returns 404.
- **SSE format:** The `FlightListSearchSSE` response uses Server-Sent Events format (`data:` prefix per line). `parse_results.py` handles this automatically — no manual stripping needed.
- **API structure:** The parser supports both the current API (`itineraryList / journeyList / transSectionList`) and any legacy structure. No inline parsing needed.
- **Rate limiting:** If trip.com returns empty results or shows a CAPTCHA, wait 3 seconds before retrying.
