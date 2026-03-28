---
name: find-cheapest-flight
description: Search trip.com for cheapest flights between two cities including hidden city (skiplag) opportunities. Usage: /find-cheapest-flight <origin> <destination> <date>
---

# Find Cheapest Flight

## Step 1 — Parse input

Extract from the user's message:
- `ORIGIN`: origin city name or IATA code
- `DESTINATION`: destination city name or IATA code
- `DATE`: travel date in YYYY-MM-DD format

Common IATA mappings:
| City | Code(s) |
|------|---------|
| 巴黎 / Paris | CDG |
| 北京 / Beijing | BJS (group: covers PEK + PKX) |
| 上海 / Shanghai | SHA or PVG |
| 广州 / Guangzhou | CAN |
| 成都 / Chengdu | CTU |
| 深圳 / Shenzhen | SZX |
| 伦敦 / London | LHR |
| 纽约 / New York | NYC (group) |

Use the **city group code** (BJS, NYC, SHA) as `acity` parameter — trip.com resolves it to all airports.

## Step 2 — Direct flight search

(Implemented in Task 4)

## Step 3 — Hidden city search

(Implemented in Task 5)

## Step 4 — Present results

(Implemented in Task 6)
