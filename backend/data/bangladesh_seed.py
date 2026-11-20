"""Privacy-safe Bangladesh-calibrated simulation population generator.

The output contains fictional names and generated finances. It is calibrated to
published aggregate statistics and must not be presented as records of real people.
"""
import csv
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "data" / "citizens.csv"
SOURCE_OUTPUT = PROJECT_ROOT / "backend" / "data" / "bangladesh_data_sources.json"

SOURCE_PROFILE = {
    "reference_year": 2022,
    "population": 169_384_897,
    "unemployment_rate": 0.04593,
    "average_monthly_household_income_bdt": 32_422,
    "notes": [
        "Profiles are synthetic household-level simulation agents, not real people.",
        "Names, ages, balances, debts, goals, and addresses are generated.",
        "Income values are modelling inputs calibrated around the published household-income benchmark."
    ],
    "sources": [
        {
            "publisher": "World Bank Open Data",
            "series": "Population, total - Bangladesh",
            "value": 169_384_897,
            "url": "https://api.worldbank.org/v2/country/BGD/indicator/SP.POP.TOTL?format=json"
        },
        {
            "publisher": "World Bank Open Data / ILO modeled estimate",
            "series": "Unemployment, total (% of total labor force) - Bangladesh",
            "value": 4.593,
            "url": "https://api.worldbank.org/v2/country/BGD/indicator/SL.UEM.TOTL.ZS?format=json"
        },
        {
            "publisher": "Bangladesh Bureau of Statistics",
            "series": "Household Income and Expenditure Survey 2022",
            "value": "Average monthly household income: BDT 32,422",
            "url": "https://bbs.portal.gov.bd/"
        }
    ]
}

FIRST_NAMES = [
    "Aarif", "Afsana", "Anika", "Arman", "Farhana", "Hasan", "Imran", "Jannat",
    "Kazi", "Lamia", "Mahmud", "Mehedi", "Nusrat", "Rifat", "Sabbir", "Samia",
    "Shakil", "Sumaiya", "Tanvir", "Tasnim"
]
LAST_NAMES = [
    "Ahmed", "Akter", "Chowdhury", "Das", "Haque", "Hossain", "Islam", "Karim",
    "Khan", "Noor", "Rahman", "Sultana", "Uddin"
]

OCCUPATIONS = [
    ("Garment Worker", "Secondary", "Machine Operation, Craft", 21_500, "workplace", 0.60, 0.25),
    ("Store Retailer", "Higher Secondary", "Sales, Customer Service", 27_000, "market", 0.70, 0.16),
    ("City Driver", "Secondary", "Driving, Navigation", 25_000, "city_center", 0.65, 0.12),
    ("School Teacher", "Bachelor", "Communication, Pedagogy", 34_000, "education", 0.90, 0.14),
    ("Healthcare Nurse", "Higher Secondary", "Patient Care, First Aid", 38_000, "workplace", 0.95, 0.06),
    ("Bank Officer", "Bachelor", "Accounting, Analysis", 52_000, "bank", 0.92, 0.06),
    ("Programmer", "Bachelor", "Coding, Problem Solving", 60_000, "workplace", 0.85, 0.06),
    ("University Lecturer", "Master", "Research, Pedagogy", 70_000, "education", 0.95, 0.02),
    ("Small Business Owner", "Higher Secondary", "Sales, Customer Service", 40_000, "market", 0.72, 0.06),
    ("Unemployed / Seeking", "Higher Secondary", "Problem Solving", 5_000, "city_center", 0.20, 0.05),
]

GOALS = [
    ("Build emergency fund", 90_000),
    ("Pay off household debt", 70_000),
    ("Children education fund", 120_000),
    ("Buy a laptop", 65_000),
    ("Start small retail business", 150_000),
    ("Renovate family residence", 180_000),
]


def generate_population(count=240, output_path=DEFAULT_OUTPUT, seed=2022):
    """Create deterministic, aggregate-calibrated simulation records."""
    rng = random.Random(seed)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    occupations = [entry[:-1] for entry in OCCUPATIONS]
    weights = [entry[-1] for entry in OCCUPATIONS]
    records = []
    for index in range(1, count + 1):
        title, education, skills, base_income, workplace_hub, stability = rng.choices(occupations, weights=weights, k=1)[0]
        income = max(4_000, round(base_income * rng.lognormvariate(0, 0.16), -2))
        essential_ratio = min(0.88, max(0.42, 0.78 - min(income, 80_000) / 250_000 + rng.uniform(-0.06, 0.06)))
        essential_expenses = round(income * essential_ratio, -2)
        discretionary_expenses = round(income * rng.uniform(0.08, 0.20), -2)
        savings = round(max(500, essential_expenses * rng.expovariate(1 / 2.1)), -2)
        debt = round(rng.uniform(5_000, income * 1.6), -2) if rng.random() < 0.35 else 0
        goal, goal_target = rng.choice(GOALS)
        risk = 0.15 + (0.30 if savings < essential_expenses else 0) + (0.18 if debt > income else 0)

        records.append({
            "id": f"bd2022_{index:04d}",
            "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "age": rng.randint(21, 58),
            "gender": rng.choice(["Female", "Male"]),
            "occupation": title,
            "education": education,
            "skills": skills,
            "monthly_income": float(income),
            "essential_expenses": float(essential_expenses),
            "discretionary_expenses": float(discretionary_expenses),
            "savings": float(savings),
            "debt": float(debt),
            "dependents": rng.choices([0, 1, 2, 3, 4], weights=[0.16, 0.31, 0.29, 0.16, 0.08], k=1)[0],
            "goal": goal,
            "goal_target_bdt": float(goal_target),
            "goal_progress_bdt": float(min(savings * 0.4, goal_target)),
            "risk_score": round(min(risk, 0.95), 3),
            "is_distressed": int(risk >= 0.55),
            "home_hub": "housing",
            "workplace_hub": workplace_hub,
        })

    with output_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    SOURCE_OUTPUT.write_text(json.dumps(SOURCE_PROFILE, indent=2), encoding="utf-8")
    return records


if __name__ == "__main__":
    generate_population()
