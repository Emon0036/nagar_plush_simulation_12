# NagarPulse: An AI-Powered Living City Simulation

For a complete file-by-file explanation, calculations, event flow, and viva questions, see [VIVA_GUIDE.md](VIVA_GUIDE.md).

CityPulse is a living city model that makes everyday economic life visible. Follow people as they move between home, work, markets, and learning spaces; inspect personal goals and financial buffers; then test how the neighbourhood responds to a change in prices, taxes, or support.

The app is designed to be read at a glance: the map shows movement, the city pulse shows distribution, and the people view keeps individual lives in focus.

## What it includes

- A responsive city map with homes, workplaces, markets, education, and moving residents.
- A people explorer with search, pressure filtering, income, savings, goals, and profiles.
- Live indicators for population, average income, financial pressure, inequality, and income distribution.
- Scenario controls for food-price changes, tax changes, cash support, and new work matches.
- A cyclone warning, landfall, and recovery scenario that changes weather visuals, travel speed, shelter routing, household risk, and emergency support.
- A synthetic training set of 50,000 financial-life patterns for the distress model.
- TiDB/MySQL persistence for the shared simulation, with an optional SQLite mode for isolated local testing.
- CSV downloads for the people sample and the training patterns.

## How the model works

Each resident is a synthetic profile with a job, income, expenses, savings, dependants, a personal goal, and a place in the city. On each simulated day, residents make simple adaptive decisions and move through the neighbourhood. Environmental events add a clear, explainable layer: cyclone severity increases household pressure, redirects residents to the civic shelter, slows travel, and opens a recovery path.

The model combines:

| Part | Purpose |
| --- | --- |
| A* pathfinding | Finds routes between city places while avoiding blocked tiles. |
| Constraint matching | Connects people seeking work with suitable vacancies. |
| Logistic regression | Estimates financial pressure from expenses, savings, debt, inflation, job stability, and dependants. |
| City metrics | Calculates inequality, poverty, average income, savings, debt, and income fifths. |

The current risk-model evaluation on a held-out test split is:

- Training patterns: **50,000**
- Accuracy: **94.15%**
- Precision: **85.05%**
- Recall: **80.82%**
- ROC-AUC: **0.983**

These are evaluation results on generated data, not a guarantee about real-world outcomes. All people and events in the app are fictional simulation data.

## Run locally

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the app

```bash
python app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). CityPulse uses this single local port for the latest neighbourhood view.

Do not open `0.0.0.0` in the browser, and do not start a second server instance while one is already running.

### 3. Database configuration

Copy `.env.example` to `.env` and provide TiDB credentials. A new shared city loads 50 citizens from TiDB in agent ID order, and its complete state is saved in TiDB. TiDB is required by default; `REQUIRE_MYSQL=false` permits SQLite fallback for local tests only. Vercel always requires TiDB/MySQL. The model weights, market configuration and downloadable CSV datasets remain packaged project files.

## Refresh the generated data

The checked-in training file already contains 50,000 rows. To regenerate the synthetic data and model weights:

```bash
python -m backend.data.dataset_generator
```

This refreshes:

- `backend/data/citizens.csv` — the 50-person live city sample.
- `backend/data/financial_risk_training.csv` — 50,000 generated training patterns.
- `backend/data/risk_model_weights.json` — the latest fitted model weights and evaluation metrics.

## Project layout

```text
.
├── app.py                         # Local server entry point
├── api/index.py                   # Deployment adapter
├── backend/
│   ├── app.py                     # FastAPI routes and static file server
│   ├── ai/                        # Pathfinding, matching, and risk model
│   ├── data/                      # Synthetic data and generated model files
│   ├── database/                  # SQLite/MySQL persistence
│   └── simulation/                # Residents, city, and simulation engine
└── public/
    ├── index.html                 # CityPulse interface
    ├── css/styles.css              # Visual system and responsive layout
    └── js/                        # Map, charts, controls, and API clients
```

## API highlights

- `GET /api/state` — current day, city state, metrics, and recent history.
- `POST /api/step` — advance the simulation one 15-minute tick.
- `POST /api/event` — inject a scenario event.
- `GET /api/agents` — search and filter residents.
- `GET /api/agents/{id}` — open a resident profile.
- `POST /api/csp-match` — find new work matches.
- `GET /api/dataset/download/citizens` — download the live sample.
- `GET /api/dataset/download/training` — download the 50,000-row training set.

## Data note

CityPulse uses generated, privacy-safe profiles calibrated for an urban Bangladesh context. It does not contain records about real people. The calibration references are kept in [`backend/data/bangladesh_data_sources.json`](backend/data/bangladesh_data_sources.json).

## Decision Engine

EcoSim uses a lightweight rule-based Decision Engine to choose each agent's next activity. The normal time-based routine remains the default, while urgent conditions override it in this order: cyclone safety, recovery, critical financial pressure, job search, debt support, food need, and normal routine.

The Decision Engine only answers "What should the agent do?". Logistic Regression measures financial risk, CSP selects a suitable job, and A* calculates the route. Each decision is returned in the agent API state with an activity, destination, reason code, priority, needs, and a human-readable reason.
