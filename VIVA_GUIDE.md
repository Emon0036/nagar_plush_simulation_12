# EcoSim AI — Viva Guide

এই document-টি viva-তে project explain করার জন্য তৈরি করা হয়েছে। Project-এর fictional agents, events এবং financial records simulation data; এগুলো real people বা real financial advice নয়।

## 1. এক লাইনে project

EcoSim AI একটি explainable virtual-city simulation যেখানে synthetic residents income, expense, savings, debt, job, weather এবং cyclone-এর প্রভাবে সিদ্ধান্ত নেয়, শহরের মধ্যে A* route দিয়ে চলে, এবং dashboard-এ ব্যক্তিগত ও city-wide financial impact দেখায়।

## 2. Run করার নিয়ম

```bash
pip install -r requirements.txt
python app.py
```

Browser:

```text
http://127.0.0.1:8000/
```

Frontend source বদলানোর পরে browser bundle rebuild করতে:

```bash
node -e "const fs=require('fs'); const Babel=require('@babel/standalone'); const source=fs.readFileSync('public/js/react_app.jsx','utf8'); const compiled=Babel.transform(source,{presets:['react']}).code; fs.writeFileSync('public/js/react_app.js',compiled,'utf8')"
```

## 3. Active file map

```text
app.py                         Local Uvicorn server চালু করে
api/index.py                   Vercel deployment entry point
vercel.json                    Vercel routing/build configuration
requirements.txt               Python backend dependencies
package.json                  React এবং Babel build dependencies

backend/app.py                FastAPI API routes এবং public file server
backend/config.py             Environment variables এবং defaults

backend/ai/astar.py           A* grid pathfinding
backend/ai/csp_solver.py      Job matching CSP solver
backend/ai/decision_engine.py Explainable rule-based next-activity engine
backend/ai/risk_model.py      Logistic Regression financial-risk model

backend/simulation/agent.py   এক resident-এর state, money, risk, decision, movement
backend/simulation/city.py    Six city hubs এবং তাদের map metadata
backend/simulation/engine.py  পুরো simulation coordinator, events, metrics, feed

backend/data/dataset_generator.py  Synthetic citizens/training data তৈরি করে
backend/data/citizens.csv          Live synthetic population
backend/data/financial_risk_training.csv  Risk model training rows
backend/data/risk_model_weights.json       Saved model/scaler weights
backend/data/market_config.json            Jobs, poverty line, commodities
backend/data/bangladesh_seed.py            Optional Bangladesh-calibrated data generator
backend/data/bangladesh_data_sources.json  Calibration/source metadata

backend/database/db.py        SQLite fallback এবং optional MySQL persistence
seed_cloud.py                 Optional Aiven/MySQL seeding script

public/index.html              Single-page HTML shell
public/js/react_app.jsx       Active React source
public/js/react_app.js        Browser-executable compiled React bundle
public/css/styles.css          Theme, layout, map, emergency UI, responsive CSS
public/vendor/                Local React, ReactDOM, Babel browser bundles

tests/test_decision_engine.py Decision priority tests
tests/test_cyclone_dashboard.py Normal/emergency/recovery integration tests
```

## 4. Full runtime flow

```text
Browser
  ↓ fetch()
FastAPI routes: backend/app.py
  ↓
SimulationEngine: backend/simulation/engine.py
  ├─ CitizenAgent objects
  ├─ Logistic Regression risk_model
  ├─ Decision Engine
  ├─ A* pathfinder
  ├─ CSP job matcher
  └─ Database manager
  ↓ JSON state
React dashboard updates cards, map, agents, routes and activity feed
```

The most important endpoint is:

```text
GET /api/state
```

It returns clock, macro state, city, metrics, movement, agent summaries, job matching result এবং `cyclone_dashboard` summary.

## 5. Simulation clock এবং tick calculation

Constants in `backend/simulation/engine.py`:

```text
MINUTES_PER_TICK = 15
TICKS_PER_DAY = 96
SIMULATION_START_MINUTE = 06:00
```

Frontend `public/js/react_app.jsx`-এ:

```text
REAL_TICK_MS = 1000
```

অর্থাৎ প্রতি ১ real second-এ backend-এ একটি tick হয়। এক simulated day:

```text
96 ticks × 1 second = প্রায় 96 real seconds
```

Backend-এর financial month calculation বদলায়নি। এক মাসে ৩০ দিন ধরে:

```text
TICKS_PER_MONTH = 96 × 30 = 2,880
tick_share = 1 / 2,880
```

তাই agent প্রতি tick-এ পুরো মাসের salary বা expense নেয় না; monthly amount-এর 1/2880 অংশ নেয়।

## 6. Agent financial calculation

File: `backend/simulation/agent.py`

প্রতি tick-এ:

```text
tax_deduction = monthly_income × tax_rate × tick_share
net_income = monthly_income × tick_share − tax_deduction
```

Food-price shock essential expense বাড়ায়:

```text
effective_essential = essential_expenses
                      × (1 + food_shock_pct × 0.70)
                      × tick_share
```

Risk অনুযায়ী discretionary spending:

```text
critical/distressed risk → normal discretionary-এর 20%
moderate risk             → normal discretionary-এর 60%
low risk                  → normal discretionary-এর 100%
```

তারপর:

```text
net_savings_delta = net_income
                    − effective_essential
                    − effective_discretionary
```

যদি delta positive হয়, savings বাড়ে এবং 35% goal progress-এ যায়। Delta negative হলে আগে savings থেকে deficit মেটানো হয়। Savings শেষ হলে বাকি amount debt হিসেবে যোগ হয়।

## 7. Logistic Regression risk model

File: `backend/ai/risk_model.py`

Model-এর মূল input:

- Essential expenses / take-home income
- Savings / shocked essential expense
- Debt / take-home income
- Food-price shock
- Inflation rate
- Job stability
- Dependants

প্রথমে tax-এর পরে take-home income:

```text
take_home_income = income × (1 − tax_rate)
```

Food shock এবং cyclone severity দিয়ে essential cost adjust হয়:

```text
shocked_essential = essential_expenses
                    × (1 + food_shock × 0.65 + cyclone_severity × 0.20)
```

Saved Logistic Regression হলে standardized features ব্যবহার করে:

```text
z = intercept + Σ(weight_i × scaled_feature_i)
probability = 1 / (1 + exp(-z))
```

Cyclone exposure risk-এ অতিরিক্ত প্রভাব ফেলে। Final probability 0 থেকে 1-এর মধ্যে clip হয়। সাধারণত:

```text
risk_score >= 0.50 → distressed/at-risk
```

Model-এর output:

```text
risk_score
is_distressed
top risk drivers
```

এটি financial risk measure করে; নিজে destination নির্বাচন করে না।

## 8. Decision Engine

File: `backend/ai/decision_engine.py`

Decision Engine-এর একমাত্র প্রশ্ন:

```text
What should this agent do now?
```

এটি নতুন ML model নয়। এটি explainable priority rules। Priority order:

1. Cyclone warning/landfall → shelter
2. Cyclone recovery → home
3. Critical financial pressure → support/recovery
4. Unemployed → job search এবং CSP request
5. High debt → bank
6. Food shock + thin savings → market/food support
7. High financial risk → recovery support
8. Otherwise normal clock-based routine

Output example:

```json
{
  "activity": "evacuating",
  "destination": "city_center",
  "reason_code": "CYCLONE_OVERRIDE",
  "priority": 100,
  "urgent": true,
  "needs": ["safety", "shelter"]
}
```

Decision Engine job select করে না এবং route calculate করে না।

## 9. CSP job matching

File: `backend/ai/csp_solver.py`

CSP-এর প্রশ্ন:

```text
Which job/resource is suitable for this agent?
```

Constraints:

- Candidate education job requirement পূরণ করে কিনা
- Candidate-এর skill-এর সঙ্গে job skill overlap আছে কিনা
- Offered salary candidate-এর reservation wage-এর চেয়ে বেশি কিনা
- একটি agent একসাথে দুই job পাবে না
- Vacancy capacity

Algorithm:

1. প্রতিটি job-এর legal candidate domain তৈরি হয়।
2. MRV সবচেয়ে ছোট domain-এর job আগে নেয়।
3. Backtracking সম্ভাব্য assignment চেষ্টা করে।
4. Forward checking ব্যবহৃত candidate অন্য domain থেকে বাদ দেয়।
5. Result agent occupation, salary এবং workplace-এ apply হয়।

## 10. A* routing

File: `backend/ai/astar.py`

A* প্রশ্ন:

```text
How does the agent get there?
```

Grid size:

```text
24 columns × 16 rows
```

প্রতিটি step-এর cost 1। Default heuristic Manhattan distance:

```text
h(a,b) = |ax − bx| + |ay − by|
```

Priority:

```text
f(n) = g(n) + h(n)
```

Buildings obstacle; doors walkable। তাই agent building-এর ভিতর দিয়ে shortcut নেয় না, door দিয়ে ঢোকে। Route `agent.current_path`, `route_progress`, `target_hub`-এ থাকে।

Cyclone-এ A* algorithm বদলায় না। শুধু Decision Engine destination shelter বা home করে এবং movement speed কমে:

```text
normal: 100%
warning: 82%
landfall: 55%
```

## 11. Cyclone Emergency Dashboard

Main logic: `backend/simulation/engine.py` এবং UI: `public/js/react_app.jsx`।

Backend `environment.stage` থেকে mode:

```text
normal                 → Normal Mode
warning / landfall     → Emergency Mode
recovery               → Recovery Mode
```

`get_cyclone_dashboard()` existing agents এবং environment থেকে হিসাব করে:

- affected agents
- high-risk agents
- evacuating agents
- sheltered agents
- returning agents
- recovered agents
- shelter capacity/occupancy
- speed reduction
- cyclone financial damage
- automatic emergency support
- recovery progress
- AI activity feed

Warning flow:

```text
cyclone_warning event
  → environment.stage = warning
  → Decision Engine returns CYCLONE_OVERRIDE
  → destination = shelter_hub/city_center
  → A* route created
  → agent activity = evacuating
  → speed factor = 0.82
  → React switches to Emergency Mode
```

Landfall flow:

```text
cyclone_landfall event
  → severity/wind/rain update
  → household vulnerability অনুযায়ী emergency cost
  → savings কমে বা debt বাড়ে
  → speed factor = 0.55
  → agent remains/heads to shelter
  → risk model recalculates
```

Recovery flow:

```text
cyclone_recovery event
  → Decision Engine returns CYCLONE_RECOVERY
  → destination = home_hub
  → A* shelter-to-home route
  → activity = returning_home
  → React switches to Recovery Mode
  → home arrivals increase recovery progress
```

The frontend components are in the same existing React application:

- `CycloneCommandCenter` — banner and metrics
- `ActivityFeed` — recent AI/emergency actions
- `CityMap` — danger zone, shelter ring, evacuation routes, returning routes
- `App` — mode selection and live state refresh

## 12. City metrics

File: `backend/simulation/engine.py`

Metrics include:

- total agents
- distressed count/rate
- poverty rate
- average/median savings
- average income
- total debt
- Gini coefficient
- five income quintiles

Gini is calculated from simulated wealth:

```text
wealth = savings + income
```

The sorted wealth values are used in the standard relative mean-difference formula. It measures inequality; it does not decide any individual action.

## 13. Database and persistence

File: `backend/database/db.py`

Startup tries configured MySQL first. If unavailable, the project uses local SQLite. This is why the application can run offline.

The database stores selected citizens, tick metrics, events, and history. The active simulation itself remains in memory while the server is running.

## 14. Important API routes for viva

| Route | Answer |
| --- | --- |
| `GET /api/state` | Full current simulation state and dashboard summaries |
| `POST /api/step` | Advance one 15-minute simulation tick |
| `POST /api/event` | Apply food, tax, cash, cyclone, or reset event |
| `GET /api/agents` | Search/filter resident list |
| `GET /api/agents/{id}` | One resident plus memory log |
| `POST /api/agents/{id}/support` | Manual targeted support endpoint |
| `POST /api/pathfinding` | Demonstrate A* route for an agent |
| `POST /api/csp-match` | Run job allocation CSP manually |
| `GET /api/risk-weights` | Risk model weights and evaluation metadata |
| `GET /api/db-status` | MySQL/SQLite status |
| `GET /api/history` | Stored city metric history |

## 15. Viva questions and short answers

### Why are four different AI/algorithm parts used?

They solve four different problems: Logistic Regression measures risk, Decision Engine selects an activity, CSP selects a suitable job, and A* calculates the physical route.

### Is Decision Engine machine learning?

No. It is a lightweight rule-based and explainable engine. The only ML model is Logistic Regression for financial-risk estimation.

### Why not let Logistic Regression choose the destination?

Risk score is only a probability. It cannot safely express a complete action plan. The Decision Engine combines risk with time, needs, employment, location, and weather.

### What happens when food prices rise?

Essential expenses increase, the risk model recalculates risk, the Decision Engine can prioritize market or food support, and the agent may use savings or incur debt if the tick deficit is not covered.

### What happens when a cyclone warning starts?

The cyclone stage overrides the normal routine. The agent selects shelter, A* calculates a route, movement speed reduces, and the React UI enters Emergency Mode.

### What happens during landfall?

Agents remain sheltered or continue to shelter, speed falls to 55%, emergency household cost is applied, savings may fall, debt may rise, and risk drivers include cyclone exposure.

### What happens during recovery?

The Decision Engine sends agents from the shelter to their home hub. A* calculates the route and the Recovery dashboard counts home arrivals.

### Why is there an Apply button if support is automatic?

Urgent or explicit Decision Engine recovery options are automatically applied once per scenario. The endpoint remains available for a user-controlled demonstration or additional manual intervention.

### Is the data real?

No. Citizens, names, income, debt, and events are synthetic. The project is an educational simulation.

## 16. Safe change guide

| Change | File |
| --- | --- |
| Agent decision priority | `backend/ai/decision_engine.py` |
| Income/expense/savings behavior | `backend/simulation/agent.py` |
| Risk inputs/model behavior | `backend/ai/risk_model.py` |
| Job constraints | `backend/ai/csp_solver.py` and `backend/data/market_config.json` |
| City hubs/doors | `backend/simulation/city.py` and `public/js/react_app.jsx` map positions |
| Cyclone metrics/feed/events | `backend/simulation/engine.py` |
| Dashboard mode/UI | `public/js/react_app.jsx` |
| Colors/layout/map overlays | `public/css/styles.css` |
| API contract | `backend/app.py` |
| Data generation | `backend/data/dataset_generator.py` |

## 17. Validation commands

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py api backend tests
node --check public/js/react_app.js
```

The current test suite covers Decision Engine priorities and the cyclone Normal → Emergency → Recovery state flow.
