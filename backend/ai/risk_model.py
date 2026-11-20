import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_WEIGHTS_FILE = os.path.join(_BASE_DIR, "backend/data/risk_model_weights.json")
TRAINING_DATA_FILE = os.path.join(_BASE_DIR, "backend/data/financial_risk_training.csv")

FEATURE_NAMES = [
    "essential_to_income_ratio",
    "savings_to_expense_ratio",
    "debt_to_income_ratio",
    "food_shock_pct",
    "inflation_rate",
    "job_stability",
    "dependents"
]

class FinancialRiskModel:
    """
    Logistic Regression Model predicting an agent's probability of financial distress.
    P(Distress) = 1 / (1 + exp(-(beta_0 + sum(beta_i * x_i))))
    """
    def __init__(self):
        self.model: Optional[LogisticRegression] = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.metrics = {}
        self.feature_weights = {}
        self.intercept = 0.0
        self.scaler_mean = []
        self.scaler_scale = []
        self._load_or_train()

    def train(self, data_path: str = TRAINING_DATA_FILE) -> Dict[str, Any]:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Training data not found at {data_path}")

        df = pd.read_csv(data_path)
        X = df[FEATURE_NAMES]
        y = df["is_distressed"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # Scale features for numerical stability and interpretable coefficients
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
        self.model.fit(X_train_scaled, y_train)

        # Predictions on test set
        y_pred = self.model.predict(X_test_scaled)
        y_prob = self.model.predict_proba(X_test_scaled)[:, 1]

        self.metrics = {
            "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
            "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
            "samples_trained": len(df)
        }

        # Save weights
        coeffs = self.model.coef_[0]
        self.feature_weights = {feat: round(float(c), 4) for feat, c in zip(FEATURE_NAMES, coeffs)}
        self.intercept = round(float(self.model.intercept_[0]), 4)
        self.scaler_mean = [float(m) for m in self.scaler.mean_]
        self.scaler_scale = [float(s) for s in self.scaler.scale_]
        self.is_trained = True

        self._export_weights()
        print(f"[Risk Model] Trained Logistic Regression successfully. Accuracy: {self.metrics['accuracy']:.2%}, AUC: {self.metrics['roc_auc']:.3f}")
        return self.metrics

    def _export_weights(self):
        export_data = {
            "feature_names": FEATURE_NAMES,
            "weights": self.feature_weights,
            "intercept": self.intercept,
            "scaler_mean": self.scaler_mean,
            "scaler_scale": self.scaler_scale,
            "metrics": self.metrics
        }
        os.makedirs(os.path.dirname(MODEL_WEIGHTS_FILE), exist_ok=True)
        with open(MODEL_WEIGHTS_FILE, "w") as f:
            json.dump(export_data, f, indent=2)

    def _load_or_train(self):
        if os.path.exists(MODEL_WEIGHTS_FILE):
            try:
                with open(MODEL_WEIGHTS_FILE, "r") as f:
                    data = json.load(f)
                self.feature_weights = data["weights"]
                self.intercept = data["intercept"]
                self.scaler_mean = data["scaler_mean"]
                self.scaler_scale = data["scaler_scale"]
                self.metrics = data.get("metrics", {})
                self.is_trained = True
                return
            except Exception:
                pass
        # If not cached, train now
        if os.path.exists(TRAINING_DATA_FILE):
            self.train()

    def predict_risk(self, agent: Dict[str, Any], macro_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates distress probability for an individual citizen.
        Returns:
            prob: float (0.0 to 1.0)
            is_distressed: bool
            drivers: list of top contributing risk factors
        """
        income = max(float(agent.get("income", agent.get("monthly_income", 25000))), 100.0)
        essential_exp = float(agent.get("essential_expenses", 15000))
        savings = float(agent.get("savings", 5000))
        debt = float(agent.get("debt", 0))
        dependents = float(agent.get("dependents", 1))
        job_stability = float(agent.get("job_stability", 0.75))

        food_shock = float(macro_state.get("food_shock_pct", 0.0))
        inflation = float(macro_state.get("inflation_rate", 0.05))
        tax_rate = float(macro_state.get("tax_rate", 0.10))
        environment = macro_state.get("environment", {}) or {}
        cyclone_severity = float(environment.get("severity", 0.0)) if environment.get("stage", "normal") != "normal" else 0.0
        # Risk is based on disposable income: a high tax rate leaves less money
        # for essentials, debt payments, and dependants.
        take_home_income = max(income * (1.0 - min(max(tax_rate, 0.0), 0.80)), 100.0)

        # Dynamically inflate essential expenses with shock
        shocked_essential = essential_exp * (1.0 + food_shock * 0.65 + cyclone_severity * 0.20)
        essential_ratio = shocked_essential / take_home_income
        savings_ratio = savings / max(shocked_essential, 100.0)
        debt_ratio = debt / take_home_income

        raw_features = [
            essential_ratio,
            savings_ratio,
            debt_ratio,
            food_shock,
            inflation,
            job_stability,
            dependents
        ]

        if not self.is_trained or not self.scaler_mean:
            # Fallback heuristic
            z = -2.0 + 3.0 * essential_ratio - 1.2 * min(savings_ratio, 5.0) + 1.5 * debt_ratio + 2.0 * food_shock + 1.2 * cyclone_severity
            prob = 1.0 / (1.0 + np.exp(-z))
            drivers = []
            if food_shock >= 0.15:
                drivers.append(f"Food Price Shock (+{food_shock*100:.0f}%)")
            if tax_rate >= 0.15:
                drivers.append(f"High Tax Burden ({tax_rate*100:.0f}% of income)")
            if cyclone_severity >= 0.20:
                drivers.append(f"Cyclone Exposure ({cyclone_severity*100:.0f}% severity)")
            return {"risk_score": round(float(prob), 3), "is_distressed": prob >= 0.50, "drivers": drivers}

        # Normalize features
        scaled_features = [
            (val - mean) / (scale if scale != 0 else 1.0)
            for val, mean, scale in zip(raw_features, self.scaler_mean, self.scaler_scale)
        ]

        # Logit: z = intercept + sum(w_i * x_i)
        z = self.intercept
        contributions = []
        for feat, x_val in zip(FEATURE_NAMES, scaled_features):
            w = self.feature_weights.get(feat, 0.0)
            contrib = w * x_val
            z += contrib
            contributions.append((feat, contrib, raw_features[FEATURE_NAMES.index(feat)]))

        prob = 1.0 / (1.0 + np.exp(-z))
        prob = float(np.clip(prob + cyclone_severity * 0.08, 0.01, 0.99))

        # Rank drivers
        contributions.sort(key=lambda item: item[1], reverse=True)
        top_drivers = []
        for feat, contrib, raw_val in contributions[:3]:
            if contrib > 0.1:
                label_map = {
                    "essential_to_income_ratio": f"High Essential Expense Burden ({raw_val*100:.0f}% of income)",
                    "savings_to_expense_ratio": f"Thin Savings Buffer ({raw_val:.1f} months)",
                    "debt_to_income_ratio": f"Heavy Debt Load ({raw_val*100:.0f}% of income)",
                    "food_shock_pct": f"Food Price Shock (+{raw_val*100:.0f}%)",
                    "inflation_rate": f"High Inflation ({raw_val*100:.1f}%)",
                    "job_stability": f"Low Job Security ({raw_val*100:.0f}%)",
                    "dependents": f"High Dependent Count ({int(raw_val)} persons)"
                }
                top_drivers.append(label_map.get(feat, feat))

        if tax_rate >= 0.15 and prob >= 0.35:
            tax_driver = f"High Tax Burden ({tax_rate*100:.0f}% of income)"
            if tax_driver not in top_drivers:
                top_drivers.insert(0, tax_driver)
                top_drivers = top_drivers[:3]

        if cyclone_severity >= 0.20 and prob >= 0.35:
            cyclone_driver = f"Cyclone Exposure ({cyclone_severity*100:.0f}% severity)"
            if cyclone_driver not in top_drivers:
                top_drivers.insert(0, cyclone_driver)
                top_drivers = top_drivers[:3]

        return {
            "risk_score": round(prob, 3),
            "is_distressed": prob >= 0.50,
            "drivers": top_drivers
        }

risk_model = FinancialRiskModel()
