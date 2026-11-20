from typing import List, Dict, Any, Optional, Set

EDU_RANKS = {
    "Secondary": 1,
    "Higher Secondary": 2,
    "Bachelor": 3,
    "Master": 4
}

class JobAllocationCSP:
    """
    Constraint Satisfaction Problem (CSP) Solver for labor market allocation.
    Matches open employer vacancies with job-seeking citizens under
    skill, education, wage reservation, and capacity constraints.
    Employs Backtracking Search with MRV (Minimum Remaining Values) and Forward Checking.
    """
    def __init__(self, job_vacancies: List[Dict[str, Any]], candidates: List[Dict[str, Any]]):
        self.jobs = job_vacancies
        self.candidates = candidates
        self.domains: Dict[str, List[str]] = {}
        self.trace_log: List[Dict[str, Any]] = []
        self._build_domains()

    def _build_domains(self):
        """
        Unary constraint enforcement (Node Consistency):
        For each job variable, domain is the subset of candidates who satisfy:
        1. Education qualification >= minimum required
        2. At least one overlapping skill
        3. Offered wage >= candidate reservation wage
        """
        for job in self.jobs:
            job_id = job["job_id"]
            min_edu = EDU_RANKS.get(job.get("required_education", "Secondary"), 1)
            req_skills = set([s.strip().lower() for s in job.get("required_skills", [])])
            offered_wage = float(job.get("offered_salary_bdt", 15000))

            legal_candidates = []
            for c in self.candidates:
                cand_edu = EDU_RANKS.get(c.get("education", "Secondary"), 1)
                cand_skills = set([s.strip().lower() for s in c.get("skills", "").split(",")])
                cand_reservation_wage = float(c.get("essential_expenses", 10000)) * 0.9

                # Check constraints
                if cand_edu >= min_edu and (not req_skills or req_skills.intersection(cand_skills)) and offered_wage >= cand_reservation_wage:
                    legal_candidates.append(c["id"])

            self.domains[job_id] = legal_candidates

    def select_unassigned_variable_mrv(self, assignment: Dict[str, str]) -> Optional[str]:
        """
        MRV Heuristic (Minimum Remaining Values):
        Chooses the job vacancy with the fewest eligible candidates remaining.
        """
        unassigned = [j["job_id"] for j in self.jobs if j["job_id"] not in assignment]
        if not unassigned:
            return None
        
        # Sort by domain size (MRV)
        unassigned.sort(key=lambda j_id: len(self.domains.get(j_id, [])))
        return unassigned[0]

    def solve(self) -> Dict[str, Any]:
        """
        Executes backtracking search with forward checking.
        Returns final assignment dict {job_id: candidate_id} and execution trace.
        """
        assignment: Dict[str, str] = {}
        self.trace_log = []
        success = self._backtrack(assignment, self.domains)
        
        # Enrich assignment with human-readable titles and agent names
        cand_lookup = {c["id"]: c for c in self.candidates}
        job_lookup = {j["job_id"]: j for j in self.jobs}

        results = []
        for job_id, cand_id in assignment.items():
            job = job_lookup.get(job_id, {})
            cand = cand_lookup.get(cand_id, {})
            results.append({
                "job_id": job_id,
                "job_title": job.get("title", "Unknown"),
                "sector": job.get("sector", "General"),
                "salary_bdt": job.get("offered_salary_bdt", 0),
                "agent_id": cand_id,
                "agent_name": cand.get("name", "Unknown"),
                "matched": True
            })

        return {
            "success": success,
            "matched_count": len(assignment),
            "total_vacancies": len(self.jobs),
            "allocations": results,
            "trace": self.trace_log[:25] # Cap trace for UI inspection
        }

    def _backtrack(self, assignment: Dict[str, str], current_domains: Dict[str, List[str]]) -> bool:
        if len(assignment) == len(self.jobs):
            return True

        var = self.select_unassigned_variable_mrv(assignment)
        if not var:
            return True

        candidates_pool = current_domains.get(var, [])
        assigned_cands = set(assignment.values())

        # If no candidates meet constraints for this vacancy, skip or leave vacant
        if not candidates_pool:
            self.trace_log.append({
                "step": f"Vacancy {var} has empty domain (no qualified candidate). Leaving open.",
                "status": "unfilled"
            })
            # Continue trying remaining jobs rather than complete dead-end
            assignment[var] = "NONE_AVAILABLE"
            if self._backtrack(assignment, current_domains):
                return True
            del assignment[var]
            return False

        for cand_id in candidates_pool:
            # Binary Constraint: One agent cannot be placed in two jobs simultaneously
            if cand_id not in assigned_cands:
                assignment[var] = cand_id
                self.trace_log.append({
                    "step": f"Assigned candidate {cand_id} to {var}",
                    "status": "assigned"
                })

                # Forward checking: remove cand_id from domains of other unassigned variables
                new_domains = {j: [c for c in c_list if c != cand_id] for j, c_list in current_domains.items()}

                if self._backtrack(assignment, new_domains):
                    return True

                # Backtrack
                del assignment[var]
                self.trace_log.append({
                    "step": f"Backtracking from {var} with candidate {cand_id}",
                    "status": "backtrack"
                })

        return False

def run_job_allocation_csp(vacancies: List[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    solver = JobAllocationCSP(vacancies, candidates)
    return solver.solve()
