import csv
import json
import random
import os
import numpy as np
import pandas as pd
from typing import List, Dict, Any

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure repeatable realism with deterministic seed option
random.seed(42)
np.random.seed(42)

FIRST_NAMES = [
    "Rohan", "Sadika", "Emon", "Tanvir", "Anika", "Shakil", "Farhana", "Kazi", "Nusrat", 
    "Mahmud", "Sumaiya", "Afsana", "Tareq", "Tasnim", "Arif", "Jannat", "Hasan", "Rifat",
    "Fatima", "Sabbir", "Mehedi", "Fahmida", "Nazmul", "Lamia", "Zubair", "Samia", "Imran"
]

LAST_NAMES = [
    "Rahman", "Noor", "Ahmed", "Islam", "Hossain", "Chowdhury", "Khan", "Akter", "Uddin",
    "Sultana", "Haque", "Miah", "Sikder", "Molla", "Barua", "Das", "Bhuiyan", "Karim"
]

OCCUPATIONS = [
    {"title": "Programmer", "sector": "Technology", "min_edu": "Bachelor", "base_income": 35000, "skills": ["Coding", "Problem Solving"], "stability": 0.85},
    {"title": "School Teacher", "sector": "Education", "min_edu": "Bachelor", "base_income": 25000, "skills": ["Communication", "Pedagogy"], "stability": 0.90},
    {"title": "Garment Worker", "sector": "Manufacturing", "min_edu": "Secondary", "base_income": 14500, "skills": ["Machine Operation", "Craft"], "stability": 0.60},
    {"title": "Bank Officer", "sector": "Banking", "min_edu": "Bachelor", "base_income": 45000, "skills": ["Accounting", "Analysis"], "stability": 0.92},
    {"title": "Store Retailer", "sector": "Retail", "min_edu": "Higher Secondary", "base_income": 18000, "skills": ["Sales", "Customer Service"], "stability": 0.70},
    {"title": "City Driver", "sector": "Transport", "min_edu": "Secondary", "base_income": 16000, "skills": ["Driving", "Navigation"], "stability": 0.65},
    {"title": "Healthcare Nurse", "sector": "Healthcare", "min_edu": "Higher Secondary", "base_income": 28000, "skills": ["Patient Care", "First Aid"], "stability": 0.95},
    {"title": "University Lecturer", "sector": "Education", "min_edu": "Master", "base_income": 58000, "skills": ["Research", "Pedagogy"], "stability": 0.95},
    {"title": "Unemployed / Seeking", "sector": "None", "min_edu": "Higher Secondary", "base_income": 3000, "skills": ["Problem Solving"], "stability": 0.20}
]

GOALS = [
    "Buy a laptop",
    "Build 6-month emergency fund",
    "Pay off microfinance debt",
    "Children higher education fund",
    "Start small retail business",
    "Renovate family residence",
    "Buy a motorbike"
]

def generate_citizens_dataset(n_agents: int = 50, output_path: str = None) -> pd.DataFrame:
    citizens = []
    
    if output_path is None:
        output_path = os.path.join(_BASE_DIR, "backend/data/citizens.csv")
    
    # 1. Guarantee Seed Profile from Slide 10: Rohan (Programmer, 30,000 BDT/mo, 5,000 BDT savings, Goal: Buy a laptop)
    rohan = {
        "id": "agent_rohan_001",
        "name": "Rohan Rahman",
        "age": 24,
        "gender": "Male",
        "occupation": "Programmer",
        "education": "Bachelor",
        "skills": "Coding, Problem Solving",
        "monthly_income": 30000.0,
        "essential_expenses": 17500.0,
        "discretionary_expenses": 7500.0,
        "savings": 5000.0,
        "debt": 0.0,
        "dependents": 1,
        "goal": "Buy a laptop",
        "goal_target_bdt": 65000.0,
        "goal_progress_bdt": 5000.0,
        "risk_score": 0.18,
        "is_distressed": 0,
        "home_hub": "housing",
        "workplace_hub": "workplace"
    }
    citizens.append(rohan)

    # 2. Guarantee Key Lab Collaborator Agents
    citizens.append({
        "id": "agent_sadika_002",
        "name": "Sadika Noor",
        "age": 23,
        "gender": "Female",
        "occupation": "University Lecturer",
        "education": "Master",
        "skills": "Research, Pedagogy",
        "monthly_income": 55000.0,
        "essential_expenses": 24000.0,
        "discretionary_expenses": 12000.0,
        "savings": 45000.0,
        "debt": 0.0,
        "dependents": 1,
        "goal": "Children higher education fund",
        "goal_target_bdt": 150000.0,
        "goal_progress_bdt": 45000.0,
        "risk_score": 0.08,
        "is_distressed": 0,
        "home_hub": "housing",
        "workplace_hub": "education"
    })

    citizens.append({
        "id": "agent_emon_003",
        "name": "Emon Rahman",
        "age": 25,
        "gender": "Male",
        "occupation": "Bank Officer",
        "education": "Bachelor",
        "skills": "Accounting, Analysis",
        "monthly_income": 48000.0,
        "essential_expenses": 22000.0,
        "discretionary_expenses": 10000.0,
        "savings": 38000.0,
        "debt": 5000.0,
        "dependents": 2,
        "goal": "Build 6-month emergency fund",
        "goal_target_bdt": 120000.0,
        "goal_progress_bdt": 38000.0,
        "risk_score": 0.12,
        "is_distressed": 0,
        "home_hub": "housing",
        "workplace_hub": "bank"
    })

    # Generate remaining population representing realistic income deciles
    for i in range(4, n_agents + 1):
        occ = random.choices(
            OCCUPATIONS, 
            weights=[0.12, 0.14, 0.28, 0.10, 0.16, 0.12, 0.06, 0.02, 0.08] # Realistic urban distribution
        )[0]
        
        # Log-normal variation around occupation base income
        income_mult = np.random.lognormal(mean=0, sigma=0.22)
        income = max(5000.0, round(occ["base_income"] * income_mult, -2))
        
        # Essential expenses: food + shelter + transit (typically 50-80% for low income, 30-50% for high income)
        essential_pct = 0.75 - (min(income, 80000.0) / 80000.0) * 0.35 + random.uniform(-0.05, 0.05)
        essential_pct = min(max(essential_pct, 0.35), 0.90)
        essential_exp = round(income * essential_pct, -2)
        
        # Discretionary expenses
        discretionary_pct = random.uniform(0.10, 0.25)
        discretionary_exp = round(income * discretionary_pct, -2)
        
        # Savings buffer
        savings_months = np.random.exponential(scale=2.5)
        savings = round(max(500.0, income * savings_months), -2)
        
        # Debt
        debt = 0.0
        if random.random() < 0.35: # 35% carry some credit or informal loans
            debt = round(random.uniform(5000, income * 2.0), -2)
            
        dependents = random.choices([0, 1, 2, 3, 4], weights=[0.25, 0.35, 0.25, 0.10, 0.05])[0]
        
        # Map workplace hub
        hub_map = {
            "Technology": "workplace",
            "Banking": "bank",
            "Education": "education",
            "Retail": "market",
            "Manufacturing": "workplace",
            "Transport": "city_center",
            "Healthcare": "workplace",
            "None": "housing"
        }
        
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        
        goal = random.choice(GOALS)
        goal_target = 60000.0 if "laptop" in goal else 100000.0
        
        # Preliminary risk heuristic (will be refined by ML model)
        net_flow = income - (essential_exp + discretionary_exp)
        risk_score = 0.15
        if savings < essential_exp * 1.5 or net_flow < 0:
            risk_score = 0.65
        if income < 12000:
            risk_score = max(risk_score, 0.75)
            
        citizens.append({
            "id": f"agent_{i:03d}",
            "name": f"{first} {last}",
            "age": random.randint(21, 58),
            "gender": random.choice(["Male", "Female"]),
            "occupation": occ["title"],
            "education": occ["min_edu"],
            "skills": ", ".join(occ["skills"]),
            "monthly_income": float(income),
            "essential_expenses": float(essential_exp),
            "discretionary_expenses": float(discretionary_exp),
            "savings": float(savings),
            "debt": float(debt),
            "dependents": dependents,
            "goal": goal,
            "goal_target_bdt": goal_target,
            "goal_progress_bdt": min(savings * 0.4, goal_target),
            "risk_score": round(risk_score, 3),
            "is_distressed": 1 if risk_score >= 0.55 else 0,
            "home_hub": "housing",
            "workplace_hub": hub_map.get(occ["sector"], "workplace")
        })

    df = pd.DataFrame(citizens)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[Dataset Generator] Generated {len(df)} realistic citizens saved to {output_path}")
    return df

def generate_risk_training_dataset(n_samples: int = 50000, output_path: str = None) -> pd.DataFrame:
    """
    Generates a realistic historical dataset for training the Logistic Regression Risk Predictor.
    Simulates various economic shock conditions (food price spikes, inflation, layoff events).
    """
    if output_path is None:
        output_path = os.path.join(_BASE_DIR, "backend/data/financial_risk_training.csv")
    
    records = []
    
    for _ in range(n_samples):
        # Monthly income in BDT: 10,000 to 120,000
        income = np.random.lognormal(mean=10.2, sigma=0.55)
        income = np.clip(income, 8000.0, 150000.0)
        
        # Macro shock injected at measurement time
        food_shock_pct = random.uniform(0.0, 0.50) # up to +50% food inflation
        general_inflation = random.uniform(0.04, 0.18)
        
        # Expenses
        base_essential_ratio = random.uniform(0.35, 0.85)
        essential_expenses = income * base_essential_ratio * (1.0 + food_shock_pct * 0.6)
        discretionary_expenses = income * random.uniform(0.05, 0.30)
        
        # Savings
        savings_ratio = np.random.exponential(scale=2.2)
        savings = income * savings_ratio
        
        # Debt
        debt_ratio = random.choices([0.0, random.uniform(0.1, 0.8), random.uniform(0.8, 2.5)], weights=[0.5, 0.35, 0.15])[0]
        debt = income * debt_ratio
        
        dependents = random.choices([0, 1, 2, 3, 4, 5], weights=[0.2, 0.3, 0.25, 0.15, 0.07, 0.03])[0]
        job_stability = random.uniform(0.3, 0.98)
        
        # Latent Financial Stress Score (Ground Truth generator)
        # Higher essential cost ratio, lower savings buffer, high debt, inflation shock, dependents -> higher distress
        months_of_buffer = savings / max(essential_expenses, 1.0)
        monthly_balance = income - (essential_expenses + discretionary_expenses + (debt * 0.05))
        
        z = (
            - 2.8 
            + 3.5 * (essential_expenses / income)
            - 1.4 * min(months_of_buffer, 6.0)
            + 1.8 * (debt / income)
            + 2.2 * food_shock_pct
            + 1.2 * general_inflation
            + 0.3 * dependents
            - 2.0 * job_stability
            + (1.5 if monthly_balance < 0 else -0.8)
            + np.random.normal(0, 0.4) # realistic econometric error term
        )
        prob = 1.0 / (1.0 + np.exp(-z))
        is_distressed = 1 if prob >= 0.50 else 0
        
        records.append({
            "monthly_income": round(income, 2),
            "essential_expenses": round(essential_expenses, 2),
            "discretionary_expenses": round(discretionary_expenses, 2),
            "savings": round(savings, 2),
            "debt": round(debt, 2),
            "dependents": dependents,
            "food_shock_pct": round(food_shock_pct, 3),
            "inflation_rate": round(general_inflation, 3),
            "job_stability": round(job_stability, 3),
            "savings_to_expense_ratio": round(months_of_buffer, 3),
            "debt_to_income_ratio": round(debt / income, 3),
            "essential_to_income_ratio": round(essential_expenses / income, 3),
            "is_distressed": is_distressed
        })
        
    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[Dataset Generator] Generated {len(df)} ML training records saved to {output_path} (Distress Rate: {df['is_distressed'].mean():.2%})")
    return df

if __name__ == "__main__":
    generate_citizens_dataset(50)
    generate_risk_training_dataset(50000)
