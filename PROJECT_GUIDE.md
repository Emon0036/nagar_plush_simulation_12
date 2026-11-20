# EcoSim AI / CityPulse - Easy Project Guide

For the detailed viva-ready code map and formulas, see [VIVA_GUIDE.md](VIVA_GUIDE.md).

This file explains the project in simple English. It describes what the project does, what a user can do with it, and where the important code is located.

## 1. What this project does

This project is a small virtual city and economy simulation.

It creates a fictional city with people, jobs, homes, markets, a bank, an education center, and a civic center. Each person has a simple financial life. For example, a person can have:

- a name, age, education, and occupation;
- monthly income;
- essential and optional expenses;
- savings and debt;
- dependants;
- a personal goal, such as buying a laptop or saving for education;
- a financial-risk score;
- a home and a regular work or activity location.

The simulation moves the people around the city. At the same time, it updates their money situation and shows how the whole city is doing.

The people and events are generated simulation data. They are not real people and are not real personal financial records.

## 2. Main features

### A. Live city map

The main screen shows an interactive isometric map. It contains six places:

1. Residential Quarter - homes and family life.
2. Industrial & Tech Park - offices, factories, and work.
3. Central Bazaar - food, shopping, and retail.
4. City Commercial Bank - savings, credit, and banking.
5. University & Academy - education and skill development.
6. City Hall & Center - government services and job seeking.

People move between these places during the simulation. The map can show routes, labels, people, and activity bubbles.

### B. Automatic simulation ticks and the city clock

The city now uses a 24-hour clock. One simulation day lasts about 96 real seconds:

- 1 tick = 15 simulated minutes;
- 96 ticks = 24 simulated hours;
- the browser advances automatically every 1 second;
- the visible watch starts at 06:00 and shows the current simulation day and time.

The routine uses morning work or school hours, daytime work and learning, evening market or bank errands, and night-time return home. An agent keeps following its current A* route until it reaches its destination.

Because income and expenses are stored as monthly BDT values, the financial engine applies 1/2,880 of those amounts per 15-minute tick (30 simulated days per month). This prevents a citizen from receiving a full month of income every 15 minutes.

On every tick:

1. Each citizen checks their financial situation.
2. The financial-risk model calculates a new risk score.
3. The citizen changes spending or uses savings if needed.
4. The citizen chooses a destination such as work, the market, the bank, or home.
5. A path is calculated and the citizen moves along it.
6. City-wide measurements are recalculated.

You can pause the simulation, resume it, or move it forward manually with **Next tick**.

### C. People explorer

The **People** page shows the citizens in a table. It includes:

- name and age;
- occupation and education;
- monthly income;
- savings;
- personal goal;
- financial-risk status and percentage.

You can search by name or occupation and show only people under financial pressure. Selecting a person opens more details, including their current activity and route.

### D. Citizen profiles

Click a person on the map, in the people table, or in the people preview cards. The profile shows their income, expenses, savings, risk, goal, and current journey.

The profile can also request a route to another city place. The route is calculated by the A* pathfinding code and is highlighted on the map.

### E. Financial-risk prediction

The project uses Logistic Regression to estimate whether a citizen is under financial pressure.

The prediction looks at factors such as:

- essential expenses compared with income;
- savings compared with expenses;
- debt compared with income;
- food-price shock;
- general inflation;
- job stability;
- number of dependants.

The result is shown as a percentage and as a simple status such as **Stable** or **At risk**. The model is trained from generated data, so its score is useful for this simulation but should not be treated as a real financial decision.

### F. City-wide economic indicators

The dashboard calculates and displays:

- population;
- employment signal;
- number of citizens at risk;
- active economic events;
- simulation month;
- inequality using the Gini coefficient;
- poverty rate;
- average and median savings;
- average income;
- total debt;
- average income and savings for five income groups.

The charts show how inequality and income distribution change over time.

### G. What-if economic scenarios

The **Scenarios** page lets you test changes to the economy:

- **Food prices rise**: increases essential food costs and can increase financial pressure.
- **Taxes change**: changes the tax rate used when calculating take-home money.
- **Support arrives**: gives a cash stimulus to vulnerable or distressed citizens.
- **Return to baseline**: removes the main changes and returns to the normal tax and food-price settings.

The page also has sliders for the food-price shift and tax rate. The current buttons use preset values, while the sliders display values for scenario controls.

### H. New work matching

The **Find new work matches** button searches for jobs for unemployed or lower-income citizens.

The matching system checks:

- education level;
- skills;
- minimum acceptable pay based on expenses;
- one person not taking two jobs;
- job capacity.

It uses a Constraint Satisfaction Problem (CSP) solver with backtracking, Minimum Remaining Values, and forward checking. The result shows matched people, job titles, salary, and match notes.

### I. Data downloads

The People page can download two CSV files:

- the live citizen sample;
- the 50,000-row financial-risk training dataset.

These files can be opened in Excel, Google Sheets, or another data-analysis tool.

### J. Local and cloud database support

The project tries to connect to MySQL using the values in `.env`. If the cloud database is not available, it uses the local SQLite file `ecosim_local.db`.

The application displays whether it is using cloud synchronization or local storage. Citizens, simulation history, and economic events can be stored in the database.

## 3. How to run the project

### Requirements

Install Python 3. The dependencies are listed in `requirements.txt`.

### Install dependencies

From the project folder, run:

```bash
pip install -r requirements.txt
```

### Start the local server

Run:

```bash
python app.py
```

Then open this address in a browser:

```text
http://127.0.0.1:8000
```

Use `127.0.0.1`, not `0.0.0.0`, in the browser. Do not start a second copy of the server if one is already running.

### Optional database setup

The project works locally with SQLite by default. For MySQL, copy `.env.example` to `.env` and add the correct MySQL password and database settings.

Do not commit real database passwords to Git.

### Regenerate the generated data

To rebuild the citizens file, the 50,000 training records, and the saved model weights, run:

```bash
python -m backend.data.dataset_generator
```

This replaces the generated data files with a new deterministic sample based on the generator code.

## 4. How to use the website

1. Start the server and open the local URL.
2. Wait for the loading screen to disappear.
3. On **Simulation**, watch the people and city metrics change.
4. Use **Pause** when you want to inspect the map.
5. Use **Next tick** to advance the city one step manually.
6. Use the map filters to show workers, students, shoppers, job seekers, at-risk citizens, or stable citizens.
7. Turn routes and labels on or off. Change the visual speed if needed.
8. Click a person to inspect their financial details.
9. Click a city place to see how many people are inside or heading there.
10. Open **People** to search citizens and download datasets.
11. Open **Scenarios** to test a food-price change, tax change, or cash support.
12. Click **Find new work matches** to run the job-matching solver.

## 5. Project structure

```text
.
├── app.py                         Starts the local FastAPI server.
├── api/index.py                   Entry point used by Vercel deployment.
├── requirements.txt               Python packages needed by the backend.
├── .env.example                   Example database configuration.
├── ecosim_local.db                Local SQLite database file.
├── vercel.json                    Vercel deployment rules.
│
├── backend/
│   ├── app.py                     FastAPI routes and frontend file server.
│   ├── config.py                  Reads environment variables and defaults.
│   │
│   ├── simulation/
│   │   ├── agent.py               Citizen data, decisions, money, and movement.
│   │   ├── city.py                Six city places and their map information.
│   │   └── engine.py              Main simulation coordinator and city metrics.
│   │
│   ├── ai/
│   │   ├── astar.py               Server-side A* route finding.
│   │   ├── csp_solver.py          Job and citizen matching solver.
│   │   └── risk_model.py          Logistic Regression financial-risk model.
│   │
│   ├── database/
│   │   └── db.py                  SQLite/MySQL tables and database operations.
│   │
│   └── data/
│       ├── dataset_generator.py   Creates citizens and training data.
│       ├── citizens.csv           Generated live citizen sample.
│       ├── financial_risk_training.csv
│       │                           Generated model-training records.
│       ├── risk_model_weights.json
│       │                           Saved model weights and evaluation metrics.
│       ├── market_config.json      Tax, poverty, commodity, and job settings.
│       └── bangladesh_data_sources.json
│                                   Calibration references for the fictional data.
│
└── public/
    ├── index.html                 Main website layout and controls.
    ├── css/styles.css              Colors, layout, map panel, tables, and responsive design.
    └── js/
        ├── app.js                 Main browser controller and API calls.
        ├── city_canvas.js          Canvas map, buildings, people, animation, and clicks.
        ├── charts.js               Inequality and income-distribution charts.
        ├── astar_client.js         Browser-side A* helper for map movement.
        ├── risk_client.js          Browser-side risk calculation helper.
        ├── csp_client.js           Runs and displays job-matching results.
        ├── config.js               Frontend grid and city-place settings.
        └── sound_fx.js              Optional browser sound effects helper.
```

The active frontend files are `public/js/react_app.jsx`, `public/css/styles.css`, and `public/vendor/`. The older frontend entries shown in the tree diagram are historical names; those files have been removed from the active project.

## 6. What each important backend part does

### `backend/app.py`

This is the web API. It receives requests from the browser and sends back JSON data. It also serves the files inside `public/`.

Important routes include:

| Route | Purpose |
| --- | --- |
| `GET /api/state` | Gets the current tick, city, metrics, events, and citizen summary. |
| `POST /api/step` | Moves the simulation forward by one tick. |
| `POST /api/event` | Applies a food shock, tax change, stimulus, or reset. |
| `GET /api/agents` | Lists citizens with search and filtering. |
| `GET /api/agents/{id}` | Gets one citizen's detailed profile. |
| `POST /api/pathfinding` | Finds an A* route for a citizen. |
| `POST /api/csp-match` | Runs the job-matching solver. |
| `GET /api/risk-weights` | Returns saved risk-model weights and metrics. |
| `GET /api/db-status` | Checks local and cloud database status. |
| `GET /api/dataset/download/...` | Downloads generated CSV data. |

### `backend/simulation/agent.py`

This file defines `CitizenAgent`. It stores one person's information. Its decision method updates risk, spending, savings, debt, goals, memory, and the next destination.

### `backend/simulation/engine.py`

This is the main controller. It loads the citizens, runs each tick, applies events, calculates city metrics, saves periodic database records, and calls the job-matching solver.

### `backend/simulation/city.py`

This file describes the six city places, their grid positions, doors, colors, icons, and descriptions.

### `backend/ai/astar.py`

This file finds a short walkable path on the 24 x 16 city grid. Building interiors are blocked except for their doors. The algorithm uses Manhattan distance as its guide.

### `backend/ai/risk_model.py`

This file trains or loads the Logistic Regression model. It converts a person's financial information and the current economic conditions into a risk probability.

### `backend/ai/csp_solver.py`

This file matches job vacancies with candidates. It removes candidates that do not satisfy education, skill, or pay rules, then searches for a valid group of matches.

### `backend/database/db.py`

This file creates database tables and saves citizens, tick metrics, and events. MySQL is attempted first when configured; SQLite is the local fallback.

### `backend/data/dataset_generator.py`

This file creates the fictional citizens and the financial-risk training records. It uses fixed random seeds so the generated sample is repeatable.

## 7. What each important frontend part does

### `public/index.html`

This is the single-page entry point. It loads the local React and Babel browser bundles, the dark stylesheet, and the active React application.

### `public/js/react_app.jsx`

This is the active frontend application. It:

- loads data from the API;
- starts the automatic tick loop;
- controls navigation, pause, filters, and scenario buttons;
- updates the dashboard numbers;
- renders the city map as a detailed SVG scene;
- shows homes, workspaces, bazaar stalls, school/college, bank, and civic buildings;
- renders residents, routes, metrics, profiles, filters, and scenarios;
- calls the existing simulation API for live state, ticks, and economic events.

### `public/css/styles.css`

This controls the new dark visual design: colors, spacing, cards, resident lists, buttons, SVG map styling, and mobile layout.

### `public/vendor/`

This contains local browser copies of React, ReactDOM, and Babel. The page uses these local files so the React interface does not need an internet connection just to load its framework.

## 8. Simple data flow

```text
Browser page
    ↓ requests JSON
FastAPI routes in backend/app.py
    ↓ call
SimulationEngine
    ├── CitizenAgent objects
    ├── Risk Model
    ├── A* Pathfinder
    ├── CSP Job Matcher
    └── Database Manager
    ↓ returns state and metrics
Browser updates map, tables, cards, and charts
```

## 9. Important notes and current limitations

- This is a simulation and learning/research demo, not a real economic forecasting system.
- Citizen data is synthetic and privacy-safe.
- The risk model is trained on generated data. Its accuracy numbers describe that generated test data only.
- The simulation is kept in memory while the server is running. The database stores selected records, but restarting the server starts a new simulation run.
- The map is a 2D SVG city scene with a dark isometric-inspired visual style, not a full 3D game engine.
- The active interface is React, loaded from local browser bundles in `public/vendor/`.
- The visible browser labels use both **EcoSim AI** and **CityPulse** names because the project has evolved from the original CityPulse name.
- The website still loads Google Fonts from an external URL in `public/index.html`. If the browser is completely offline, it will use fallback system fonts, but the application and React runtime remain local.

## 10. Where to make common changes

| If you want to change... | Start in... |
| --- | --- |
| A city place or its position | `backend/simulation/city.py` and map positions in `public/js/react_app.jsx` |
| Citizen behavior | `backend/simulation/agent.py` |
| Number or type of generated citizens | `backend/data/dataset_generator.py` |
| Food, tax, poverty, or job settings | `backend/data/market_config.json` and `backend/simulation/engine.py` |
| Risk-model inputs or training | `backend/ai/risk_model.py` and `backend/data/dataset_generator.py` |
| Job matching rules | `backend/ai/csp_solver.py` and `backend/data/market_config.json` |
| API endpoints | `backend/app.py` |
| Dashboard behavior | `public/js/react_app.jsx` |
| City map and resident animation | `public/js/react_app.jsx` and `public/css/styles.css` |
| Resident filters and search | `public/js/react_app.jsx` |
| Page text and HTML controls | `public/index.html` |
| Colors and responsive layout | `public/css/styles.css` |

## 11. Short summary

In one sentence: **EcoSim AI / CityPulse is an interactive virtual city where fictional citizens move, work, spend, save, face economic changes, and receive AI-style analysis so users can explore how personal finances and city-wide inequality change together.**

### Decision-driven behavior

Each simulation tick asks the rule-based Decision Engine what an agent should do next. It uses the current clock, routine, income, expenses, savings, debt, financial-risk score, employment, needs, location, and cyclone stage.

The priority order is:

1. Cyclone warning or landfall: move to the civic shelter.
2. Cyclone recovery: return home.
3. Critical financial pressure: seek essential support.
4. Unemployment: go to the civic center and request CSP job matching.
5. High debt: visit the bank.
6. Food-price shock with a thin buffer: visit the market.
7. Normal routine: work, learn, run an errand, or return home.

The Decision Engine does not assign jobs or calculate paths. CSP still selects a suitable vacancy, and A* still calculates movement. The selected agent panel and the expanded agent list show the current decision, destination, priority, reason code, and explanation.
