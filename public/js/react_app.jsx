const { useEffect, useMemo, useRef, useState } = React;

const PLACE_META = {
  housing: { short: "Homes", type: "Residential", accent: "#62c28d", detail: "Courtyards, apartment lanes, and family homes" },
  workplace: { short: "Workshops", type: "Work", accent: "#7ca8f8", detail: "Office towers, workshops, and daily shifts" },
  market: { short: "Bazaar", type: "Commerce", accent: "#e8b86b", detail: "Food stalls, small shops, and neighborhood trade" },
  bank: { short: "Bank", type: "Finance", accent: "#ae94ed", detail: "Savings, credit, and small-business planning" },
  education: { short: "Campus", type: "Learning", accent: "#65c8d9", detail: "School rooms, college halls, and new skills" },
  city_center: { short: "Civic", type: "Civic", accent: "#e38c9d", detail: "City services, transit, and job seeking" },
};

const HUB_POSITIONS = {
  housing: { x: 38, y: 42, w: 190, h: 128 },
  workplace: { x: 328, y: 42, w: 210, h: 128 },
  market: { x: 642, y: 42, w: 196, h: 128 },
  bank: { x: 38, y: 338, w: 190, h: 132 },
  education: { x: 328, y: 338, w: 210, h: 132 },
  city_center: { x: 642, y: 338, w: 196, h: 132 },
};

const TRACK_LABELS = {
  housing: "Home",
  workplace: "Workplace",
  market: "Bazaar",
  bank: "Bank",
  education: "School / college",
  city_center: "Urban center",
};

// Faster demonstration clock: 96 fifteen-minute ticks complete one simulated
// day in about 96 real seconds while the backend time model stays unchanged.
const REAL_TICK_MS = 1000;

const DEMO_AGENTS = [
  { id: "demo-1", name: "Rohan Rahman", occupation: "Programmer", education: "Bachelor", income: 30000, savings: 5000, risk_score: 0.42, is_distressed: 0, goal: "Buy a laptop", current_hub: "housing", target_hub: "workplace", x: 5, y: 6 },
  { id: "demo-2", name: "Sadika Noor", occupation: "University Lecturer", education: "Master", income: 55000, savings: 45000, risk_score: 0.08, is_distressed: 0, goal: "Education fund", current_hub: "education", target_hub: "housing", x: 12, y: 11 },
  { id: "demo-3", name: "Emon Rahman", occupation: "Bank Officer", education: "Bachelor", income: 48000, savings: 38000, risk_score: 0.12, is_distressed: 0, goal: "Emergency fund", current_hub: "bank", target_hub: "workplace", x: 4, y: 11 },
  { id: "demo-4", name: "Farhana Akter", occupation: "Store Retailer", education: "Higher Secondary", income: 18000, savings: 9200, risk_score: 0.66, is_distressed: 1, goal: "Start a small shop", current_hub: "market", target_hub: "market", x: 18, y: 6 },
  { id: "demo-5", name: "Tanvir Hossain", occupation: "City Driver", education: "Secondary", income: 16000, savings: 6400, risk_score: 0.58, is_distressed: 1, goal: "Buy a motorbike", current_hub: "city_center", target_hub: "market", x: 18, y: 10 },
];

function money(value) { return `${Math.round(Number(value) || 0).toLocaleString()} BDT`; }
function riskOf(agent) { return Math.round((Number(agent?.risk_score) || 0) * 100); }
function clockForTick(tick) {
  const minutes = (360 + ((Number(tick) || 0) * 15)) % 1440;
  const hour = Math.floor(minutes / 60);
  const minute = minutes % 60;
  return { day: Math.floor((Number(tick) || 0) / 96) + 1, hour, minute, time: `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}` };
}
function statusOf(agent) {
  const occupation = String(agent?.occupation || "").toLowerCase();
  if (occupation.includes("unemployed") || occupation.includes("seeking")) return "unemployed";
  if (agent?.is_distressed || riskOf(agent) >= 55) return "risk";
  if (occupation.includes("student")) return "student";
  return "stable";
}
function conditionOf(agent) {
  if (riskOf(agent) >= 75) return "Critical";
  const status = statusOf(agent);
  return status === "critical" ? "Critical" : status === "risk" ? "At risk" : status === "unemployed" ? "Job seeking" : status === "student" ? "Learning" : "Stable";
}
function arrivalTime(clock, remainingSteps) {
  if (!Number.isFinite(Number(remainingSteps)) || Number(remainingSteps) <= 0) return "Reached";
  const total = (Number(clock?.minutes) || 0) + (Number(remainingSteps) * 15);
  const minutes = total % 1440;
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}
function activityOf(agent) {
  const state = agent?.activity_state;
  if (state === "traveling") return agent?.target_hub ? `Traveling to ${PLACE_META[agent.target_hub]?.short || agent.target_hub}` : "Traveling through the city";
  if (state === "working") return agent?.current_hub === "education" ? "Teaching and learning on campus" : "Working at the daily shift";
  if (state === "shopping") return "Shopping at the bazaar";
  if (state === "banking") return "Banking and planning";
  if (state === "at_home") return "At home in the neighborhood";
  const hub = agent?.target_hub || agent?.current_hub || "housing";
  if (hub === "market") return "Shopping at the bazaar";
  if (hub === "bank") return "Banking and planning";
  if (hub === "education") return "Learning on campus";
  if (hub === "city_center") return "Moving through the civic district";
  if (hub === "workplace") return "On the way to work";
  return "At home in the neighborhood";
}
function journeyTargetOf(agent) {
  if (agent?.target_hub) return PLACE_META[agent.target_hub]?.short || agent.target_hub;
  if (agent?.activity_state === "at_home") return "Resting at home";
  if (agent?.activity_state === "working") return "Working here";
  if (agent?.activity_state === "shopping") return "Shopping here";
  if (agent?.activity_state === "banking") return "Banking here";
  return "Inside the place";
}

function agentText(value, fallback = "—") { return value === undefined || value === null || value === "" ? fallback : String(value); }
function agentMoney(value) { return money(Number(value || 0)); }
function agentHub(value) { return PLACE_META[value]?.short || agentText(value, "Not assigned"); }
function supportLabel(agent) {
  const labels = {
    emergency_support: "Emergency cyclone support",
    food_support: "Targeted food support",
    tax_relief: "Temporary tax relief",
    debt_support: "Debt repayment support",
    job_search_support: "Temporary job-search support",
    buffer_support: "Savings-buffer support",
  };
  const type = agent?.next_action?.support_type || agent?.decision?.support_type || "";
  return labels[type] || type || "Monitor and protect essentials";
}
function decisionLabel(agent) {
  const labels = {
    at_home: "Stay at home", traveling: "Travel", working: "Work",
    learning: "Learn", shopping: "Shop for essentials", banking: "Visit the bank",
    job_search: "Search for work", seeking_support: "Seek support",
    evacuating: "Evacuate", sheltered: "Stay in shelter", returning_home: "Return home",
  };
  return labels[agent?.decision?.activity] || agent?.decision?.activity || activityOf(agent);
}
function agentDetail(agent) {
  return [
    ["Agent ID", agent.id], ["Age", agent.age ? `${agent.age} years` : "—"], ["Gender", agent.gender],
    ["Education", agent.education], ["Skills", agent.skills], ["Monthly income", agentMoney(agent.income || agent.monthly_income)],
    ["Essential expenses", agentMoney(agent.essential_expenses)], ["Optional expenses", agentMoney(agent.discretionary_expenses)],
    ["Savings", agentMoney(agent.savings)], ["Debt", agentMoney(agent.debt)], ["Dependants", agent.dependents],
    ["Goal", agent.goal], ["Goal progress", `${agentMoney(agent.goal_progress_bdt)} / ${agentMoney(agent.goal_target_bdt)}`],
    ["Home", agentHub(agent.home_hub)], ["Workplace", agentHub(agent.workplace_hub)],
    ["Current place", agentHub(agent.current_hub)], ["Destination", agentHub(agent.target_hub)], ["Decision", decisionLabel(agent)], ["Decision reason", agent.decision?.reason || "Following the normal routine."], ["Decision priority", agent.decision?.priority ?? "—"], ["Selected response", agent.next_action?.title || "Monitor and protect essentials"], ["Support option", supportLabel(agent)], ["Automatic support", agent.automatic_support?.applied ? `${supportLabel(agent)} · ${agent.automatic_support.description}` : "Not yet applied"],
    ["Activity", activityOf(agent)], ["Weather status", agentText(agent.weather_status, "Normal")],
    ["Risk score", `${riskOf(agent)}%`], ["Risk drivers", agent.top_drivers?.length ? agent.top_drivers.join(" · ") : "None"],
    ["Next action", agent.next_action?.title || "None"], ["Route remaining", agent.route_remaining_steps === undefined ? "—" : `${agent.route_remaining_steps} steps`],
    ["Route progress", agent.route_progress === undefined ? "—" : `${agent.route_progress} / ${agent.route_length || 0}`],
    ["Travel speed", agent.travel_speed === undefined ? "—" : `${agent.travel_speed} cells/tick`],
    ["Journeys completed", agent.completed_journeys], ["Coordinates", agent.x === undefined ? "—" : `${agent.x}, ${agent.y}`],
  ];
}
function Icon({ name, size = 18 }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  const paths = {
    pulse: <><path d="M3 12h4l2.2-6 4.1 12 2.2-6H21" /></>,
    play: <><path d="m8 5 11 7-11 7V5Z" fill="currentColor" stroke="none" /></>,
    pause: <><path d="M8 5v14M16 5v14" /></>,
    step: <><path d="m5 5 8 7-8 7V5ZM18 5v14" /></>,
    arrow: <><path d="M5 12h13M13 6l6 6-6 6" /></>,
    search: <><circle cx="10.8" cy="10.8" r="6.2" /><path d="m16 16 4.2 4.2" /></>,
    home: <><path d="m3 11 9-7 9 7" /><path d="M5.5 10v9h13v-9M9 19v-5h6v5" /></>,
    work: <><rect x="4" y="7" width="16" height="12" rx="1.5" /><path d="M9 7V4.5h6V7M4 12h16M10 12v2h4v-2" /></>,
    market: <><path d="M4 10h16l-1 9H5l-1-9Z" /><path d="M3 10 5 5h14l2 5M8 10v2M12 10v2M16 10v2" /></>,
    school: <><path d="m3 10 9-5 9 5-9 5-9-5Z" /><path d="M6 12.5V17c3.5 2.5 8.5 2.5 12 0v-4.5M21 10v6" /></>,
    bank: <><path d="m3 9 9-5 9 5M5 10v7M9 10v7M15 10v7M19 10v7M3 19h18" /></>,
    civic: <><path d="M4 20h16M6 17V9M10 17V9M14 17V9M18 17V9M3 8l9-4 9 4" /></>,
    route: <><circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 17c5 0 3-8 8-8" /></>,
    clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3 2" /></>,
    refresh: <><path d="M20 11a8 8 0 0 0-14.7-3L3 11M4 5v6h6M4 13a8 8 0 0 0 14.7 3L21 13m0 6v-6h-6" /></>,
    leaf: <><path d="M20 4C10 4 4 8 4 15c0 3 2 5 5 5 7 0 11-6 11-16Z" /><path d="M4 20c2-5 5-8 11-11" /></>,
    storm: <><path d="M6 18h11a4 4 0 0 0 .5-8A5.5 5.5 0 0 0 7 8.5 4.5 4.5 0 0 0 6 18Z" /><path d="m13 13-2 4h3l-2 4" /></>,
  };
  return <svg {...common}>{paths[name] || paths.pulse}</svg>;
}

function WatchFace({ clock }) {
  const minutes = Number(clock?.minute) || 0;
  const hour = Number(clock?.hour) || 0;
  const minuteAngle = minutes * 6;
  const hourAngle = ((hour % 12) * 30) + (minutes * 0.5);
  return <span className="watch-face" aria-label={`Simulation time ${clock.time}`}><i className="watch-hand watch-hour" style={{ transform: `rotate(${hourAngle}deg)` }} /><i className="watch-hand watch-minute" style={{ transform: `rotate(${minuteAngle}deg)` }} /><i className="watch-center" /></span>;
}

function BuildingArt({ id, x, y, w, h, accent, selected, onClick }) {
  const meta = PLACE_META[id] || PLACE_META.housing;
  const iconName = id === "housing" ? "home" : id === "workplace" ? "work" : id === "market" ? "market" : id === "education" ? "school" : id === "bank" ? "bank" : "civic";
  const houses = [[18, 23], [63, 23], [108, 23], [40, 72], [88, 72], [135, 72]];
  const offices = [[22, 22, 34, 50], [66, 31, 43, 41], [119, 18, 53, 54]];
  const stalls = [[17, 25], [62, 25], [107, 25], [39, 73], [84, 73], [129, 73]];
  return <g className={`map-place place-${id} ${selected ? "is-selected" : ""}`} onClick={() => onClick(id)} role="button" tabIndex="0">
    <rect className="place-shadow" x={x + 3} y={y + 5} width={w} height={h} rx="14" />
    <rect className="place-base" x={x} y={y} width={w} height={h} rx="14" style={{ "--place-accent": accent }} />
    <rect className="place-roof" x={x + 8} y={y + 8} width={w - 16} height={h - 16} rx="10" />
    {id === "housing" && houses.map(([hx, hy], index) => <g key={index} className="house" transform={`translate(${x + hx} ${y + hy})`}><path d="M0 12 15 0l15 12v20H0Z" /><path d="M10 32V20h10v12M4 13h22" /><rect x="4" y="16" width="6" height="6" rx="1" /><rect x="20" y="16" width="6" height="6" rx="1" /></g>)}
    {id === "workplace" && offices.map(([ox, oy, ow, oh], index) => <g key={index} className="office-block" transform={`translate(${x + ox} ${y + oy})`}><rect width={ow} height={oh} rx="3" /><path d={`M7 11h${ow - 14}M7 20h${ow - 14}M7 29h${ow - 14}`} /><path d={`M${ow / 2} 4v${oh - 8}`} /></g>)}
    {id === "market" && stalls.map(([sx, sy], index) => <g key={index} className="market-stall" transform={`translate(${x + sx} ${y + sy})`}><path d="M0 9h32l-4-9H4L0 9Z" /><rect x="3" y="10" width="26" height="19" rx="2" /><path d="M10 15v7M18 15v7" /></g>)}
    {id === "education" && <g className="campus-art" transform={`translate(${x + 28} ${y + 17})`}><path d="m0 18 76-18 76 18-76 18L0 18Z" /><path d="M25 25v32h102V25M42 24v29M62 19v34M82 14v39M102 10v43" /><path d="M14 62h124M27 68h100" /></g>}
    {id === "bank" && <g className="bank-art" transform={`translate(${x + 31} ${y + 22})`}><path d="m0 18 64-18 64 18H0Z" /><path d="M14 22v45M38 22v45M62 22v45M86 22v45M110 22v45M0 72h128" /></g>}
    {id === "city_center" && <g className="civic-art" transform={`translate(${x + 30} ${y + 17})`}><path d="M0 17 68 0l68 17H0Z" /><path d="M15 22v48M40 22v48M68 22v48M96 22v48M121 22v48M0 75h136" /></g>}
    <g className="place-label" transform={`translate(${x + 14} ${y + h - 23})`}><circle cx="9" cy="9" r="9" style={{ fill: accent }} /><foreignObject x="3" y="3" width="12" height="12"><Icon name={iconName} size={12} /></foreignObject><text x="25" y="7">{meta.short}</text><text x="25" y="20" className="place-type">{meta.type}</text></g>
  </g>;
}

function cycloneModeOf(cyclone, environment) {
  const stage = cyclone?.stage || environment?.stage || "normal";
  return cyclone?.mode || (stage === "recovery" ? "recovery" : ["warning", "landfall"].includes(stage) ? "emergency" : "normal");
}

function CycloneCommandCenter({ cyclone }) {
  if (!cyclone || cyclone.mode === "normal") return null;
  const emergency = cyclone.mode === "emergency";
  const stageLabel = cyclone.stage === "landfall" ? "LANDFALL" : cyclone.stage === "warning" ? "WARNING" : "RECOVERY";
  const progress = Math.round((Number(cyclone.recovery_progress) || 0) * 100);
  return <section className={`cyclone-command cyclone-command-${cyclone.mode}`}>
    <div className="cyclone-banner">
      <div className="cyclone-banner-mark">🌪️</div>
      <div><span className="eyebrow">AI EMERGENCY OPERATIONS</span><h2>{emergency ? `CYCLONE EMERGENCY — ${stageLabel}` : "CYCLONE PASSED — RECOVERY IN PROGRESS"}</h2><p>{cyclone.description}</p></div>
      <div className="cyclone-severity"><small>SEVERITY</small><strong>{Math.round((Number(cyclone.severity) || 0) * 100)}%</strong><span>{cyclone.wind_kph} kph wind</span></div>
    </div>
    <div className="cyclone-metrics">
      {emergency ? <>
        <Metric label="Affected agents" value={cyclone.affected_agents} detail={`${cyclone.total_agents} total residents`} tone="amber" />
        <Metric label="High risk" value={cyclone.high_risk_agents} detail="financially vulnerable" tone="pink" />
        <Metric label="Evacuating" value={cyclone.evacuating_agents} detail="A* shelter routes" tone="blue" />
        <Metric label="Sheltered" value={`${cyclone.sheltered_agents} / ${cyclone.available_shelters?.[0]?.capacity || 0}`} detail="safe inside shelter" tone="green" />
        <Metric label="Speed reduction" value={`${cyclone.movement_speed_reduction_pct}%`} detail={`${Math.round(cyclone.movement_speed_factor * 100)}% movement speed`} tone="blue" />
      </> : <>
        <Metric label="Returned home" value={cyclone.recovered_agents} detail={`${progress}% recovery progress`} tone="green" />
        <Metric label="Returning" value={cyclone.returning_agents} detail="A* routes to home" tone="blue" />
        <Metric label="Still sheltered" value={cyclone.sheltered_agents} detail="awaiting safe return" tone="amber" />
        <Metric label="Emergency support" value={money(cyclone.emergency_support_bdt)} detail="automatic assistance" tone="green" />
        <Metric label="Financial damage" value={money(cyclone.financial_damage_bdt)} detail="household emergency cost" tone="pink" />
      </>}
    </div>
    <div className="cyclone-command-bottom">
      <div className="cyclone-shelter-card"><span className="eyebrow">AVAILABLE SHELTERS</span>{(cyclone.available_shelters || []).map((shelter) => <div className="cyclone-shelter" key={shelter.id}><strong>🏛 {shelter.name}</strong><span>{shelter.occupied} / {shelter.capacity} occupied · {shelter.available} available</span></div>)}</div>
      <ActivityFeed feed={cyclone.feed} />
    </div>
  </section>;
}

function ActivityFeed({ feed = [] }) {
  return <div className="cyclone-feed"><div className="feed-heading"><span className="eyebrow">AI ACTIVITY FEED</span><span className="live-dot" /></div>{feed.length ? feed.slice(-8).reverse().map((item, index) => <div className="feed-item" key={`${item.tick}-${index}`}><time>{item.time || "--:--"}</time><span>{item.icon}</span><p>{item.message}</p></div>) : <p className="feed-empty">Waiting for the first emergency update.</p>}</div>;
}

function CityMap({ agents, selectedAgentId, selectedPlace, onAgent: selectAgent, onPlace, showRoutes, clock, environment, cycloneDashboard }) {
  const [trackingId, setTrackingId] = useState(null);
  const [liveEnvironment, setLiveEnvironment] = useState(environment || null);
  useEffect(() => { fetch("/api/state").then((response) => response.json()).then((data) => setLiveEnvironment(data.macro_state?.environment || null)).catch(() => {}); }, [agents]);
  const onAgent = (agent) => {
    setTrackingId((current) => current === agent.id ? null : agent.id);
    selectAgent(agent);
  };
  const trackedAgent = trackingId ? agents.find((agent) => agent.id === trackingId) : null;
  // The city map is intentionally a full-population view: all 50 residents
  // stay present while their individual schedules determine who is traveling.
  const visibleAgents = agents;
  const motionRef = useRef(new Map());
  const [, forceMotion] = useState(0);
  const pointFor = (agent, index) => {
    const hub = HUB_POSITIONS[agent.current_hub] || HUB_POSITIONS.housing;
    const seed = String(agent.id || index).split("").reduce((sum, letter) => sum + letter.charCodeAt(0), 0);
    const hasGridPosition = Number.isFinite(Number(agent.x)) && Number.isFinite(Number(agent.y));
    const traveling = agent?.activity_state === "traveling" || agent?.target_hub;
    const inBuilding = !traveling && Boolean(HUB_POSITIONS[agent.current_hub]);
    const base = inBuilding
      ? { x: hub.x + 32 + (seed * 13 + index * 23) % Math.max(30, hub.w - 72), y: hub.y + 38 + (seed * 7 + index * 17) % Math.max(24, hub.h - 70) }
      : hasGridPosition
        ? { x: 35 + (Number(agent.x) / 23) * 806, y: 30 + (Number(agent.y) / 15) * 450 }
        : { x: hub.x + 18 + (seed * 13 + index * 23) % Math.max(30, hub.w - 38), y: hub.y + 20 + (seed * 7 + index * 17) % Math.max(28, hub.h - 48) };
    const spreadX = traveling ? 0 : ((seed * 17) % 15) - 7;
    const spreadY = traveling ? 0 : ((seed * 11) % 11) - 5;
    return { x: base.x + spreadX, y: base.y + spreadY };
  };
  useEffect(() => {
    const targets = new Map(visibleAgents.map((agent, index) => [agent.id || `agent-${index}`, pointFor(agent, index)]));
    const starts = new Map();
    targets.forEach((target, id) => starts.set(id, motionRef.current.get(id) || target));
    const startedAt = performance.now();
    let frame;
    const animate = (now) => {
      const progress = Math.min((now - startedAt) / Math.max(REAL_TICK_MS - 120, 700), 1);
      targets.forEach((target, id) => {
        const start = starts.get(id) || target;
        const eased = 1 - Math.pow(1 - progress, 3);
        motionRef.current.set(id, { x: start.x + (target.x - start.x) * eased, y: start.y + (target.y - start.y) * eased });
      });
      forceMotion((value) => value + 1);
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [agents]);
  const positionFor = (agent, index) => motionRef.current.get(agent.id || `agent-${index}`) || pointFor(agent, index);
  const tracked = trackingId ? visibleAgents.find((agent) => agent.id === trackingId) : null;
  const trackedIndex = tracked ? visibleAgents.findIndex((agent) => agent.id === trackingId) : -1;
  const trackedPoint = tracked ? positionFor(tracked, trackedIndex) : null;
  const trackedTarget = tracked?.target_hub ? (TRACK_LABELS[tracked.target_hub] || tracked.target_hub) : `At ${TRACK_LABELS[tracked?.current_hub] || "home"}`;
  const remainingSteps = tracked && Number.isFinite(Number(tracked.route_remaining_steps)) ? Number(tracked.route_remaining_steps) : null;
  const calloutX = trackedPoint ? Math.min(Math.max(trackedPoint.x - 18, 16), 652) : 0;
  const calloutY = trackedPoint ? Math.max(trackedPoint.y - 102, 14) : 0;
  const travelingCount = visibleAgents.filter((agent) => agent.activity_state === "traveling" || agent.target_hub).length;
  const homeCount = visibleAgents.filter((agent) => agent.activity_state === "at_home").length;
  const routeCandidates = visibleAgents.filter((agent) => (agent.activity_state === "traveling" || agent.route_remaining_steps > 0) && agent.target_hub && HUB_POSITIONS[agent.target_hub]);
  const priorityRoutes = routeCandidates.filter((agent) => agent.id === selectedAgentId || agent.id === trackingId);
  const priorityIds = new Set(priorityRoutes.map((agent) => agent.id));
  const routeAgents = [...priorityRoutes, ...routeCandidates.filter((agent) => !priorityIds.has(agent.id))].slice(0, 14);
  const weatherStage = (environment || liveEnvironment)?.stage || "normal";
  const cycloneMode = cycloneModeOf(cycloneDashboard, environment || liveEnvironment);
  const shelterHub = cycloneDashboard?.available_shelters?.[0]?.id || (environment || liveEnvironment)?.shelter_hub || "city_center";
  const shelterPosition = HUB_POSITIONS[shelterHub];
  return <div className={`city-map-wrap weather-wrap-${weatherStage}`}><svg className="city-map" viewBox="0 0 876 518" aria-label="Interactive dark city map" role="img">
    <defs><pattern id="city-grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#1b332c" strokeWidth="1" /></pattern><filter id="soft-glow"><feGaussianBlur stdDeviation="3" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
    <rect width="876" height="518" rx="22" className="map-ground" /><rect x="22" y="23" width="832" height="472" rx="18" fill="url(#city-grid)" opacity=".55" />
    {cycloneMode === "emergency" && <g className="cyclone-danger-zone"><ellipse cx="690" cy="265" rx="205" ry="215" /><text x="604" y="83">DANGER WEATHER ZONE</text><text x="625" y="98">EVACUATE TO SHELTER</text></g>}
    {cycloneMode !== "normal" && shelterPosition && <g className="shelter-overlay"><circle cx={shelterPosition.x + shelterPosition.w / 2} cy={shelterPosition.y + shelterPosition.h / 2} r="78" /><circle cx={shelterPosition.x + shelterPosition.w / 2} cy={shelterPosition.y + shelterPosition.h / 2} r="62" /><text x={shelterPosition.x + shelterPosition.w / 2 - 42} y={shelterPosition.y - 9}>SHELTER</text></g>}
    {weatherStage !== "normal" && <g className={`weather-layer weather-${weatherStage}`} aria-hidden="true"><rect className="weather-tint" width="876" height="518" />{weatherStage !== "recovery" && Array.from({ length: 20 }, (_, index) => { const x = (index * 47) % 876; const y = 70 + ((index * 31) % 380); return <path key={`rain-${index}`} className="rain-streak" d={`M${x} ${y}l-16 34`} />; })}</g>}
    <path className="river" d="M270-20c28 95-36 138 16 221 45 73 42 164 4 337h89c38-165 38-262-11-347C320 111 387 66 355-20Z" />
    <path className="road road-main" d="M26 208H850M26 295H850M273 25V493M581 25V493" /><path className="road road-side" d="M26 246H850M26 384H850M286 25V493M568 25V493" /><path className="lane" d="M26 208H850M26 295H850M273 25V493M581 25V493" />
    <g className="park"><rect x="250" y="207" width="304" height="86" rx="18" /><circle cx="290" cy="242" r="12" /><circle cx="336" cy="265" r="9" /><circle cx="505" cy="241" r="14" /><circle cx="461" cy="269" r="8" /><path d="M275 282c46-29 95-29 141 0s95 29 141 0" /></g>
    <g className="district-labels"><text x="56" y="30">NORTH RESIDENTIAL BELT</text><text x="354" y="30">EMPLOYMENT CORRIDOR</text><text x="666" y="30">TRADING QUARTER</text><text x="58" y="329">SOUTH BANKING ROW</text><text x="351" y="329">LEARNING DISTRICT</text><text x="665" y="329">CIVIC DISTRICT</text></g>
    {Object.entries(HUB_POSITIONS).map(([id, p]) => <BuildingArt key={id} id={id} {...p} accent={PLACE_META[id].accent} selected={selectedPlace === id} onClick={onPlace} />)}
    {showRoutes && routeAgents.map((agent, index) => { const start = positionFor(agent, index); const targetHub = HUB_POSITIONS[agent.target_hub]; const end = { x: targetHub.x + targetHub.w / 2, y: targetHub.y + targetHub.h / 2 }; const evacuation = agent.decision?.activity === "evacuating" || agent.target_hub === shelterHub; const returning = agent.decision?.activity === "returning_home"; return <path key={`route-${agent.id}`} className={`agent-route ${evacuation ? "evacuation-route" : ""} ${returning ? "return-route" : ""} ${agent.id === selectedAgentId || agent.id === trackingId ? "is-priority" : ""}`} d={`M${start.x} ${start.y} C${(start.x + end.x) / 2} ${start.y}, ${(start.x + end.x) / 2} ${end.y}, ${end.x} ${end.y}`} />; })}
    <g className="agents-layer">{visibleAgents.map((agent, index) => { const p = positionFor(agent, index); const status = statusOf(agent); const selected = agent.id === selectedAgentId; const emergencyActivity = agent.decision?.activity; const emergencyClass = emergencyActivity === "evacuating" ? "is-evacuating" : emergencyActivity === "sheltered" ? "is-sheltered" : emergencyActivity === "returning_home" ? "is-returning" : ""; return <g key={agent.id || index} className={`map-agent agent-${status} ${emergencyClass} ${selected ? "is-selected" : ""}`} transform={`translate(${p.x} ${p.y})`} onClick={(event) => { event.stopPropagation(); onAgent(agent); }} role="button" tabIndex="0">{status === "risk" && <circle className="danger-pulse" r="12" />}{emergencyActivity === "evacuating" && <circle className="evacuation-pulse" r="13" />}<circle className="agent-shadow" cx="0" cy="8" r="8" /><circle className="agent-head" cy="-5" r="4" /><path className="agent-body" d="M-6 9c.5-8 2.5-11 6-11s5.5 3 6 11Z" />{selected && <><circle className="agent-focus" r="15" /><text className="agent-tag" x="10" y="3">{String(agent.name || "Citizen").split(" ")[0]}</text></>}</g>; })}</g>
    {tracked && trackedPoint && <g className={`condition-meter condition-${conditionOf(tracked) === "Critical" ? "critical" : statusOf(tracked)}`} transform={`translate(${trackedPoint.x - 18} ${trackedPoint.y - 25})`}><rect className="condition-meter-track" width="36" height="5" rx="2.5" /><rect className="condition-meter-fill" width={Math.max(3, Math.round(riskOf(tracked) * 0.36))} height="5" rx="2.5" /></g>}
    {tracked && trackedPoint && <g className={`tracking-callout tracking-${conditionOf(tracked) === "Critical" ? "critical" : statusOf(tracked)}`}>
      <path className="tracking-line" d={`M${trackedPoint.x} ${trackedPoint.y - 8} L${calloutX + 20} ${calloutY + 68}`} />
      <rect className="tracking-box" x={calloutX} y={calloutY} width="208" height="74" rx="10" />
      <text className="tracking-title" x={calloutX + 12} y={calloutY + 16}>TRACKING · {String(tracked.name || "CITIZEN").split(" ")[0].toUpperCase()}</text>
      <text className="tracking-copy" x={calloutX + 12} y={calloutY + 35}>Target: {trackedTarget}</text>
      <text className="tracking-copy" x={calloutX + 12} y={calloutY + 51}>Reach: {remainingSteps === null ? "Live route" : arrivalTime(clock, remainingSteps)}</text>
      <text className="tracking-status" x={calloutX + 12} y={calloutY + 67}>Condition: {conditionOf(tracked)}</text>
  </g>}
    <g className="map-scale"><circle cx="48" cy="468" r="4" /><path d="M48 468h54" /><text x="48" y="487">250m city block</text></g>
  </svg><div className="map-hud"><span><i className="live-dot" /> {cycloneMode === "normal" ? "Live city model" : cycloneMode === "emergency" ? "Emergency operations" : "Recovery operations"}</span><span>{visibleAgents.length} residents · {cycloneMode === "emergency" ? `${cycloneDashboard?.sheltered_agents || 0} sheltered` : `${travelingCount} traveling · ${homeCount} home`}</span><span>Dhaka · {clock.time} · day {clock.day}</span></div><div className="map-legend"><span><i className="legend-dot stable" /> Stable</span><span><i className="legend-dot risk" /> Danger</span><span><i className="legend-dot student" /> Learning</span><span><i className="legend-dot moving" /> Moving</span>{cycloneMode !== "normal" && <><span><i className="legend-dot shelter" /> Shelter</span><span><i className="legend-dot evacuation" /> Evacuating</span></>}</div></div>;
}

function Metric({ label, value, detail, tone = "green" }) { return <div className={`metric metric-${tone}`}><span className="metric-label">{label}</span><strong>{value}</strong><small>{detail}</small></div>; }

function App() {
  const [state, setState] = useState(null); const [agents, setAgents] = useState([]); const [selectedAgent, setSelectedAgent] = useState(null); const [selectedPlace, setSelectedPlace] = useState("housing"); const [playing, setPlaying] = useState(true); const [showRoutes, setShowRoutes] = useState(true); const [layer, setLayer] = useState("all"); const [query, setQuery] = useState(""); const [busy, setBusy] = useState(false); const [notice, setNotice] = useState("Baseline conditions"); const [impact, setImpact] = useState({ title: "Baseline conditions", detail: "No economic shift is active", support: "0 BDT" }); const [error, setError] = useState("");
  const metrics = state?.metrics || {}; const macro = state?.macro_state || {}; const clock = state?.simulation_clock || clockForTick(state?.tick || 0); const environment = macro.environment || { stage: "normal", title: "Clear weather", description: "Normal city movement and routines.", severity: 0 }; const cyclone = state?.cyclone_dashboard || {}; const dashboardMode = cycloneModeOf(cyclone, environment); const foodShift = Math.round((Number(macro.food_shock_pct) || 0) * 100); const taxRate = Math.round((Number(macro.tax_rate) || .10) * 100); const allAgents = agents.length ? agents : DEMO_AGENTS;
  const filteredAgents = useMemo(() => { const q = query.toLowerCase().trim(); return allAgents.filter((agent) => { const matchesQuery = !q || `${agent.name} ${agent.occupation}`.toLowerCase().includes(q); const status = statusOf(agent); const matchesLayer = layer === "all" || (layer === "risk" && status === "risk") || (layer === "workers" && status === "stable") || (layer === "students" && status === "student"); return matchesQuery && matchesLayer; }); }, [allAgents, layer, query]);
  const movement = state?.movement || {}; const selected = selectedAgent || filteredAgents[0] || allAgents[0]; const total = metrics.total_agents || allAgents.length; const atRisk = metrics.distressed_count ?? allAgents.filter((agent) => statusOf(agent) === "risk").length; const employment = allAgents.length ? Math.round((1 - allAgents.filter((agent) => statusOf(agent) === "unemployed").length / allAgents.length) * 100) : 0; const placeInfo = PLACE_META[selectedPlace]; const selectedPlaceAgents = allAgents.filter((agent) => agent.current_hub === selectedPlace || agent.target_hub === selectedPlace);

  async function loadData() { try { const response = await fetch("/api/state"); if (!response.ok) throw new Error("The local model is not responding yet."); const next = await response.json(); setState(next); const people = await fetch("/api/agents?limit=50"); if (people.ok) { const data = await people.json(); setAgents(data.agents || []); if (!selectedAgent && data.agents?.length) setSelectedAgent(data.agents[0]); } setError(""); } catch (err) { setError("Preview mode · start python app.py to connect the live model"); } }
  async function step(automatic = false) { setBusy(true); try { const response = await fetch(automatic === true ? "/api/step?automatic=true" : "/api/step", { method: "POST" }); if (response.ok) { setState(await response.json()); const people = await fetch("/api/agents?limit=50"); if (people.ok) setAgents((await people.json()).agents || []); } } catch (err) { setError("The city is paused while the local model reconnects."); } finally { setBusy(false); } }
  async function event(eventType, magnitude, label) { setBusy(true); setNotice(label); try { const before = metrics; const response = await fetch("/api/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: eventType, magnitude }) }); if (response.ok) { const payload = await response.json(); const after = payload.new_metrics || {}; const beforeRisk = before.distressed_count ?? "—"; const afterRisk = after.distressed_count ?? "—"; const detail = eventType === "food_price_shock" ? `Essential costs rise · pressure ${beforeRisk} → ${afterRisk} residents` : eventType === "tax_change" ? `Take-home pay shifts · danger ${beforeRisk} → ${afterRisk} residents` : eventType.startsWith("cyclone") ? `Weather stage changed · danger ${beforeRisk} → ${afterRisk} residents` : eventType === "cash_stimulus" ? "Targeted transfers reach vulnerable households" : "All scenario values returned to baseline"; setImpact({ title: label, detail, support: eventType === "cash_stimulus" ? money(magnitude) : eventType === "reset_baseline" ? "0 BDT" : impact.support }); await loadData(); } } catch (err) { setError("Scenario preview only · connect the server to apply it to the model"); } finally { setBusy(false); } }
  async function applySupport() { if (!selected?.id) return; setBusy(true); try { const response = await fetch(`/api/agents/${encodeURIComponent(selected.id)}/support`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ support_type: selected.next_action?.support_type || "auto" }) }); if (!response.ok) throw new Error("Support could not be applied."); const payload = await response.json(); const before = Math.round((Number(payload.before_risk) || 0) * 100); const after = Math.round((Number(payload.after_risk) || 0) * 100); setSelectedAgent(payload.agent); setImpact({ title: "Targeted support applied", detail: `${payload.description} · risk ${before}% → ${after}% · danger ${payload.before_danger_count} → ${payload.after_danger_count} residents`, support: "Personalized" }); await loadData(); setSelectedAgent(payload.agent); } catch (err) { setError("Support could not be applied while the local model is reconnecting."); } finally { setBusy(false); } }
  useEffect(() => { loadData(); }, []); useEffect(() => { if (!playing) return undefined; const timer = window.setInterval(() => step(true), REAL_TICK_MS); return () => window.clearInterval(timer); }, [playing]);

  return <div className={`app-shell dashboard-mode-${dashboardMode}`}><header className="topbar"><div className="brand"><span className="brand-mark"><Icon name="pulse" size={20} /></span><span><strong>EcoSim</strong><small>Living city model</small></span></div><div className="topbar-center"><span className="eyebrow">NIGHT SHIFT / DHAKA</span><span className="simulation-clock"><WatchFace clock={clock} /><span><b>{clock.time}</b><small>Day {clock.day} · 15 min / tick</small></span></span><span className="tick-readout">Tick {state?.tick ?? 0}</span></div><div className="top-actions"><span className="connection"><i className="live-dot" />{error ? "Preview" : "Model live"}</span><button className="icon-btn" onClick={() => setPlaying((value) => !value)} title={playing ? "Pause simulation" : "Resume simulation"}><Icon name={playing ? "pause" : "play"} size={15} /><span>{playing ? "Pause" : "Resume"}</span></button><button className="icon-btn" onClick={step} disabled={busy} title="Advance one simulation tick"><Icon name="step" size={15} /><span>Next tick</span></button></div></header>
    <main className="dashboard">{dashboardMode !== "normal" && <CycloneCommandCenter cyclone={cyclone} />}<section className="intro-row"><div><div className="eyebrow accent-text">A CITY THAT BREATHES</div><h1>{dashboardMode === "emergency" ? <>Protect the city<br /><em>through the storm.</em></> : dashboardMode === "recovery" ? <>The city<br /><em>finds its way home.</em></> : <>See the city<br /><em>come alive.</em></>}</h1><p className="intro-copy">{dashboardMode === "emergency" ? "Cyclone safety has priority. Agents are evacuating through the existing Decision Engine and A* shelter routes." : dashboardMode === "recovery" ? "The cyclone has passed. Agents are returning home while financial recovery and safe movement continue." : "A calm, human-scale view of work, money, movement, and the small decisions that shape a neighborhood."}</p></div><div className="event-strip"><span className="event-kicker"><Icon name={dashboardMode === "normal" ? "leaf" : "storm"} size={14} /> {dashboardMode === "normal" ? "Economic signal" : "Cyclone signal"}</span><strong>{impact.title || notice}</strong><small>{impact.detail}</small><div className="impact-readout"><span><small>Food price</small><b>+{foodShift}%</b></span><span><small>Tax rate</small><b>{taxRate}%</b></span><span><small>Support</small><b>{impact.support}</b></span></div></div></section>
      <section className="metrics-row"><Metric label="Residents" value={total.toLocaleString()} detail="synthetic citizens" /><Metric label="Employment" value={`${employment}%`} detail="model estimate" tone="blue" /><Metric label="Under pressure" value={atRisk.toLocaleString()} detail="financial risk" tone="amber" /><Metric label="Inequality" value={Number(metrics.gini_coefficient || 0).toFixed(3)} detail="Gini coefficient" tone="pink" /><div className="tick-card"><span className="metric-label">Simulation day</span><strong>{clock.day}</strong><small>96 ticks · 15 min each</small></div></section>
      <section className="workspace-grid"><div className="map-panel panel-dark"><div className="panel-head"><div><span className="eyebrow">{dashboardMode === "normal" ? "THE NEIGHBORHOOD / LIVE MAP" : dashboardMode === "emergency" ? "EMERGENCY MAP / LIVE EVACUATION" : "RECOVERY MAP / RETURN ROUTES"}</span><h2>{dashboardMode === "normal" ? "People, places, and daily journeys" : dashboardMode === "emergency" ? "Shelters, danger zones, and evacuation routes" : "Agents returning safely through the city"}</h2></div><div className="map-tools"><button className={`small-toggle ${showRoutes ? "active" : ""}`} onClick={() => setShowRoutes((value) => !value)}><Icon name="route" size={14} /> Routes</button><span className="map-time">{clock.time} · {movement.traveling_count ?? 0} on the move</span></div></div><CityMap agents={allAgents} selectedAgentId={selected?.id} selectedPlace={selectedPlace} onAgent={(agent) => setSelectedAgent(agent)} onPlace={setSelectedPlace} showRoutes={showRoutes} clock={clock} environment={environment} cycloneDashboard={cyclone} /></div>
        <aside className="right-rail"><section className="detail-panel panel-dark"><div className="panel-head compact"><div><span className="eyebrow">FOCUS</span><h2>{selected?.name || "Select a resident"}</h2></div><span className={`status-pill ${statusOf(selected)}`}>{statusOf(selected) === "risk" ? "Danger" : "Stable"}</span></div>{selected && <><div className="resident-head"><div className={`avatar avatar-${statusOf(selected)}`}>{String(selected.name || "C").split(" ").map((word) => word[0]).slice(0, 2).join("")}</div><div><strong>{selected.occupation || "Resident"}</strong><small>{selected.education || "Local citizen"} · {activityOf(selected)}</small></div></div><div className="resident-stats"><div><small>Monthly income</small><strong>{money(selected.income || selected.monthly_income)}</strong></div><div><small>Savings buffer</small><strong>{money(selected.savings)}</strong></div><div><small>Personal goal</small><strong>{selected.goal || "Build a buffer"}</strong></div></div><div className="risk-line"><div><span>Financial pressure</span><strong>{riskOf(selected)}%</strong></div><div className="risk-bar"><i style={{ width: `${riskOf(selected)}%` }} /></div><small>Logistic Regression estimate · {riskOf(selected) >= 55 ? "needs attention" : "room to breathe"}</small></div>{selected.decision && <div className="decision-card"><div className="decision-kicker">CURRENT DECISION · PRIORITY {selected.decision.priority}</div><strong>{decisionLabel(selected)} → {agentHub(selected.decision.destination)}</strong><p>{selected.decision.reason}</p><small>{selected.decision.reason_code}</small></div>}{selected.next_action && <div className={`response-card ${statusOf(selected) === "risk" ? "danger" : "stable"}`}><div className="response-kicker">{selected.automatic_support?.applied ? "AUTOMATICALLY APPLIED" : statusOf(selected) === "risk" ? "SELECTED RESPONSE" : "NEXT BEST ACTION"}</div><strong>{selected.next_action.title}</strong><p>{selected.next_action.description}</p>{selected.automatic_support?.applied && <small className="response-meta">Decision Engine automatically applied: {supportLabel(selected)} · {selected.automatic_support.description}</small>}{!selected.automatic_support?.applied && statusOf(selected) === "risk" && <small className="response-meta">Selected support option: {supportLabel(selected)}</small>}{selected.top_drivers?.length > 0 && <div className="driver-list">{selected.top_drivers.slice(0, 3).map((driver) => <span key={driver}>{driver}</span>)}</div>}{statusOf(selected) === "risk" && !selected.automatic_support?.applied && <button className="support-button" onClick={applySupport} disabled={busy}>{busy ? "Applying support…" : selected.next_action.button_label}</button>}</div>}<div className="journey"><Icon name="route" size={14} /><span><small>Today's journey</small><strong>{PLACE_META[selected.current_hub]?.short || "Home"} <b>→</b> {journeyTargetOf(selected)}</strong></span></div></>}</section>
          <section className="place-panel panel-dark"><div className="panel-head compact"><div><span className="eyebrow">SELECTED DISTRICT</span><h2>{placeInfo.short}</h2></div><span className="place-orb" style={{ background: placeInfo.accent }}><Icon name={selectedPlace === "housing" ? "home" : selectedPlace === "workplace" ? "work" : selectedPlace === "market" ? "market" : selectedPlace === "education" ? "school" : selectedPlace === "bank" ? "bank" : "civic"} size={16} /></span></div><p className="place-description">{placeInfo.detail}</p><div className="place-counts"><div><strong>{selectedPlaceAgents.length}</strong><small>inside or moving in</small></div><div><strong>{selectedPlace === "housing" ? "06" : selectedPlace === "workplace" ? "12" : selectedPlace === "market" ? "18" : "08"}</strong><small>active locations</small></div></div></section></aside></section>
      <section className="lower-grid"><section className="people-panel panel-dark"><div className="panel-head"><div><span className="eyebrow">PEOPLE IN MOTION</span><h2>All agents · full profiles</h2></div><div className="filter-tabs">{[["all", "All"], ["workers", "Working"], ["risk", "At risk"], ["students", "Learning"]].map(([value, label]) => <button key={value} className={layer === value ? "active" : ""} onClick={() => setLayer(value)}>{label}</button>)}</div></div><div className="people-toolbar"><div className="search-box"><Icon name="search" size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search a name or occupation" /></div><span className="people-count">{filteredAgents.length} shown</span></div><div className="people-list">{filteredAgents.map((agent) => <details className={`agent-record ${selected?.id === agent.id ? "selected" : ""}`} key={agent.id} open><summary className="person-row" onClick={() => setSelectedAgent(agent)}><span className={`mini-avatar avatar-${statusOf(agent)}`}>{String(agent.name || "C").split(" ").map((word) => word[0]).slice(0, 2).join("")}</span><span className="person-main"><strong>{agent.name}</strong><small>{agent.occupation || "Resident"} · {activityOf(agent)} · {agentHub(agent.current_hub)}</small></span><span className="person-money"><strong>{agentMoney(agent.income || agent.monthly_income)}</strong><small>{riskOf(agent)}% risk</small></span><span className="agent-expand">⌄</span></summary><div className="agent-details"><div className="agent-detail-grid">{agentDetail(agent).map(([label, value]) => <div key={label}><small>{label}</small><strong>{agentText(value)}</strong></div>)}</div><div className="agent-action"><span>Recommended action</span><strong>{agent.next_action?.title || "No action required"}</strong><small>{agent.next_action?.description || "Agent is currently stable."}</small></div><button className="agent-select-button" onClick={() => setSelectedAgent(agent)}>Focus this agent</button><details className="agent-raw"><summary>Show raw simulation state</summary><pre>{JSON.stringify(agent, null, 2)}</pre></details></div></details>)}</div></section>
        <section className="scenario-panel panel-dark"><div className="panel-head"><div><span className="eyebrow">WHAT IF?</span><h2>Change the evening</h2></div><Icon name="pulse" size={18} /></div><p className="scenario-copy">Create a shock, inspect a dangerous household, then test a targeted response.</p><div className="scenario-buttons"><button onClick={() => event("food_price_shock", .30, "Food prices +30%")}><span className="scenario-icon amber"><Icon name="market" size={16} /></span><span><strong>Food prices rise</strong><small>+30% essentials · watch red agents</small></span><Icon name="arrow" size={14} /></button><button onClick={() => event("tax_change", .20, "Tax rate 20%")}><span className="scenario-icon blue"><Icon name="civic" size={16} /></span><span><strong>Tax rate changes</strong><small>Take-home pay shifts</small></span><Icon name="arrow" size={14} /></button><button onClick={() => event("cash_stimulus", 5000, "Support arrives")}><span className="scenario-icon green"><Icon name="leaf" size={16} /></span><span><strong>Support arrives</strong><small>5,000 BDT transfer</small></span><Icon name="arrow" size={14} /></button></div><button className="reset-button" onClick={() => event("reset_baseline", 0, "Baseline conditions")}><Icon name="refresh" size={13} /> Return to baseline</button></section></section>
      {error && <div className="notice"><span><i className="notice-dot" />{error}</span><button onClick={loadData}>Reconnect <Icon name="refresh" size={13} /></button></div>}<footer className="footer-note"><span>EcoSim AI · synthetic city data for exploration</span><span>Tick {state?.tick ?? 0} · {busy ? "Updating model…" : "Model ready"}</span></footer>
    </main></div>;
}

function CycloneControls() {
  const trigger = async (eventType, magnitude) => {
    await fetch("/api/event", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event_type: eventType, magnitude }) });
    window.location.reload();
  };
  return <div className="weather-controls"><span><Icon name="storm" size={15} /><strong>Weather scenario</strong></span><button onClick={() => trigger("cyclone_warning", .55)}>Warning</button><button onClick={() => trigger("cyclone_landfall", .85)}>Landfall</button><button onClick={() => trigger("cyclone_recovery", 0)}>Recover</button></div>;
}

ReactDOM.createRoot(document.getElementById("root")).render(<><App /><CycloneControls /></>);
