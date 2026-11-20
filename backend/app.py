import os
import re
import secrets
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.simulation.persistence import city_key, simulation_session
from backend.simulation.city import city_env
from backend.ai.risk_model import risk_model
from backend.ai.astar import pathfinder
from backend.database.db import db_manager
from backend.config import config

app = FastAPI(
    title="CityPulse API",
    description="Living city simulation API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def identify_city(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.url.path in ("/api/health", "/api/db-status"):
        return await call_next(request)
    cookie = request.cookies.get("nagarpulse_city", "")
    is_new = not re.fullmatch(r"[0-9a-f]{64}", cookie)
    key = secrets.token_hex(32) if is_new else cookie
    token = city_key.set(key)
    try:
        response = await call_next(request)
        response.headers["Cache-Control"] = "private, no-store"
        if is_new:
            response.set_cookie("nagarpulse_city", key, max_age=31536000, httponly=True,
                                secure=bool(os.getenv("VERCEL")) or request.url.scheme == "https",
                                samesite="strict", path="/api")
        return response
    finally:
        city_key.reset(token)


@app.post("/api/reset")
def reset_simulation():
    with simulation_session(write=True, reset=True) as engine:
        return engine.get_state()


# Request schemas
class ShockEventRequest(BaseModel):
    event_type: str
    magnitude: Optional[float] = 0.0
    description: Optional[str] = ""

class TaxChangeRequest(BaseModel):
    tax_rate: float

class PathfindingRequest(BaseModel):
    agent_id: Optional[str] = None
    destination: str
    start: Optional[List[int]] = None

class AgentSupportRequest(BaseModel):
    support_type: Optional[str] = "auto"

@app.get("/api/state")
def get_simulation_state():
    """Returns the current macro state, city layout, metrics, and agent summary"""
    with simulation_session() as engine:
        return engine.get_state()

@app.post("/api/step")
def step_simulation(automatic: bool = False):
    """Advances simulation cycle by one tick"""
    with simulation_session(write=True) as engine:
        now = engine._database_now
        if automatic and now - getattr(engine, "last_shared_tick_time", 0) < 0.5:
            return engine.get_state()
        engine.last_shared_tick_time = now
        engine.step()
        return engine.get_state()

@app.post("/api/event")
def inject_shock_event(req: ShockEventRequest):
    """Injects an economic shock (e.g. food_price_shock 0.30, cash_stimulus, tax_change)"""
    with simulation_session(write=True) as engine:
        event = engine.inject_event(req.event_type, req.magnitude or 0.0, req.description or "")
        return {
            "status": "success",
            "event": event,
            "state": engine.get_state(),
            "new_metrics": engine.metrics_history[-1] if engine.metrics_history else {}
        }

@app.api_route("/api/csp-match", methods=["GET", "POST"])
def trigger_csp_allocation():
    """Executes CSP job matching algorithm"""
    with simulation_session(write=True) as engine:
        return {"status": "success", "result": engine.run_labor_csp()}

@app.get("/api/agents")
def list_agents(
    search: Optional[str] = Query(None, description="Search by name or occupation"),
    distressed_only: Optional[bool] = Query(False, description="Filter distressed citizens only"),
    limit: int = Query(50, ge=1, le=500)
):
    """Lists citizens with search and status filters"""
    with simulation_session() as engine:
        agents = [a.to_dict() for a in engine.agents]
    if distressed_only:
        agents = [a for a in agents if a["is_distressed"] == 1]
    if search:
        s = search.lower()
        agents = [a for a in agents if s in a["name"].lower() or s in a["occupation"].lower()]
    return {
        "count": len(agents),
        "agents": agents[:limit]
    }

@app.get("/api/agents/{agent_id}")
def get_agent_detail(agent_id: str):
    """Returns deep-dive inspector details for a specific citizen agent"""
    with simulation_session() as engine:
        for a in engine.agents:
            if a.id == agent_id:
                data = a.to_dict()
                data["full_memory"] = a.memory_log
                data["current_hub_info"] = city_env.hubs.get(a.current_hub, {})
                return data
    raise HTTPException(status_code=404, detail="Agent not found")

@app.post("/api/agents/{agent_id}/support")
def support_agent(agent_id: str, req: AgentSupportRequest):
    """Apply a small targeted intervention to one vulnerable resident."""
    try:
        with simulation_session(write=True) as engine:
            result = engine.apply_agent_support(agent_id, req.support_type or "auto")
            return {**result, "state": engine.get_state()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/api/pathfinding")
def calculate_agent_route(req: PathfindingRequest):
    """Runs the existing A* pathfinder for an agent route demonstration."""
    if req.destination not in pathfinder.building_zones:
        raise HTTPException(status_code=400, detail="Unknown destination hub")

    start = tuple(req.start or [])
    if req.agent_id:
        with simulation_session() as engine:
            agent = next((item for item in engine.agents if item.id == req.agent_id), None)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            start = (int(agent.x), int(agent.y))

    if len(start) != 2:
        raise HTTPException(status_code=400, detail="A start coordinate or agent_id is required")

    goal = pathfinder.get_hub_door(req.destination)
    route = pathfinder.find_path((int(start[0]), int(start[1])), goal)
    return {
        "algorithm": "A* Search",
        "heuristic": "Manhattan Distance",
        "start": [int(start[0]), int(start[1])],
        "destination": req.destination,
        "route": [[int(x), int(y)] for x, y in route],
        "path_length": max(len(route) - 1, 0),
        "cost": max(len(route) - 1, 0)
    }

@app.get("/api/db-status")
@app.get("/api/health")
def get_database_status():
    """Report active database readiness without revealing connection details."""
    status = db_manager.get_status()
    return JSONResponse(status_code=200 if status["status"] == "ok" else 503, content=status)

@app.get("/api/risk-weights")
def get_risk_weights():
    """Returns trained Logistic Regression coefficients and evaluation metrics"""
    return {
        "metrics": risk_model.metrics,
        "weights": risk_model.feature_weights,
        "intercept": risk_model.intercept,
        "feature_names": [
            "essential_to_income_ratio",
            "savings_to_expense_ratio",
            "debt_to_income_ratio",
            "food_shock_pct",
            "inflation_rate",
            "job_stability",
            "dependents"
        ]
    }

@app.get("/api/history")
def get_history(limit: int = 50):
    """Returns time-series macroeconomic indicator history"""
    with simulation_session() as engine:
        run_id = engine.run_id
    return db_manager.get_history(limit, run_id)

@app.get("/api/dataset/download/{dataset_name}")
def download_dataset(dataset_name: str):
    """Allows researchers/students to export the simulated demographic or training dataset"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if dataset_name == "citizens":
        file_path = os.path.join(base_dir, "backend/data/citizens.csv")
        filename = "citypulse_people_dataset.csv"
    elif dataset_name == "training":
        file_path = os.path.join(base_dir, "backend/data/financial_risk_training.csv")
        filename = "citypulse_training_patterns.csv"
    else:
        raise HTTPException(status_code=400, detail="Invalid dataset name")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file not generated")

    return FileResponse(file_path, media_type="text/csv", filename=filename)

# Mount frontend static files (after all API routes)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
