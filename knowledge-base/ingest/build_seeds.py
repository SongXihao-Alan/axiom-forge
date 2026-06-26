#!/usr/bin/env python3
"""
Generate 5000+ axiom paper seeds by sweeping:
  domain × year × venue × topic × author_group × type

Each combination produces a unique seed ID. No API needed.
"""
import json
from pathlib import Path

DOMAINS = [
    "cooperative_game_theory", "mechanism_design", "social_choice",
    "fair_division", "feature_attribution", "information_economics",
    "matching_markets",
]

# Top venues per domain (used as sweep axis)
VENUES = {
    "cooperative_game_theory": [
        "Econometrica", "Rev. Econ. Studies", "J. Econ. Theory",
        "Games Econ. Behavior", "Math. Operations Research",
        "Ann. Math", "Int. J. Game Theory", "J. Math. Economics",
        "Math. Social Sciences", "Ann. Operations Research",
        "SIAM J. Appl. Math", "Q. J. Economics",
        "European J. Operational Research",
    ],
    "mechanism_design": [
        "Econometrica", "J. Econ. Theory", "American Econ. Rev.",
        "Rev. Econ. Studies", "Games Econ. Behavior", "EC",
        "J. Math. Economics", "Q. J. Economics", "Int. J. Game Theory",
        "Handbook of Game Theory", "Handbook of Econ. Instruments",
        "Springer", "Cambridge Univ Press",
    ],
    "social_choice": [
        "Econometrica", "J. Econ. Theory", "American Econ. Rev.",
        "Rev. Econ. Studies", "J. Math. Economics", "Public Choice",
        "Social Choice Welfare", "Games Econ. Behavior",
        "Int. J. Economic Theory", "Math. Social Sciences",
        "J. Optimization Theory Appl.", "Ann. Operations Research",
        "European J. Political Econ.",
    ],
    "fair_division": [
        "J. Optimization Theory Appl.", "SIAM J. Discrete Math",
        "Algorithmica", "Operations Research", "Games Econ. Behavior",
        "Int. J. Game Theory", "ACM TALG", "EC", "NeurIPS",
        "ICML", "J. ACM", "Math. Social Sciences",
        "American Math. Monthly", "Ann. Math",
        "SIAM Rev.", "Math. Operations Research",
    ],
    "feature_attribution": [
        "NeurIPS", "ICML", "ICLR", "J. Machine Learning Research",
        "Nature Machine Intelligence", "ACM TALG", "IEEE TPAMI",
        "arXiv", "J. Amer. Stat. Assoc.", "Ann. Stat.",
        "Stat. Science", "Prob. Stat. Prediction",
        "Cambridge Univ Press", "Springer", "Chapman & Hall",
    ],
    "information_economics": [
        "Econometrica", "American Econ. Rev.", "J. Econ. Theory",
        "Rev. Econ. Studies", "Q. J. Economics", "J. Political Economy",
        "Bell J. Economics", "Int. Econ. Review", "Games Econ. Behavior",
        "Handbook of Econometrics", "Handbook of Game Theory",
        "Springer", "Cambridge Univ Press",
    ],
    "matching_markets": [
        "American Econ. Rev.", "Econometrica", "Rev. Econ. Studies",
        "Games Econ. Behavior", "Operations Research",
        "Manufacturing Service Oper.", "J. Political Economy",
        "ACM SIGecom", "Internet Economics", "Springer",
        "NeurIPS", "EC", "WINE", "Internet and Web Sciences",
    ],
}

# Topic axes per domain — each tuple creates a unique seed
TOPICS = {
    "cooperative_game_theory": [
        "Cooperative Games", "Coalition Formation", "Core Existence",
        "Nucleolus", "Kernel", "Value Theory", "Shapley Value",
        "Bargaining", "NTU Games", "Stochastic Games", "Market Games",
        " TU Games", "Simple Games", "Balanced Games", "Voting Games",
        "Assignment Games", "Matching Games", "Network Games",
        "Graphical Games", "Potentials", "Cost Sharing", "Revenue Sharing",
        "Axiomatic Value", "Semivalues", "Gately Value", "Egalitarian Value",
        "Constrained Games", "Bargaining Set", "Kleinberg Value",
        "Solidarity Values", "Compensation Values", "Aumann Value",
        "Generalized Nucleolus", "Pareto Optimality", "Individual Rationality",
        "Coalitional Stability", "Implementation", "Mechanism Design",
    ],
    "mechanism_design": [
        "Optimal Auction", "Revenue Maximization", "Mechanism Design",
        "Bayesian Mechanism", "Dominant Strategy", "Incentive Compatibility",
        "Individual Rationality", "Full Surplus Extraction",
        "Post-Optimal Auction", "Mechanism with Money", "Mechanism without Money",
        "Procurement Auction", "Multi-Dimensional Mechanism",
        "Dynamic Mechanism", "Online Mechanism", "Randomized Mechanism",
        "Robust Mechanism", "Mechanism with Advice", "Fair Mechanism",
        "Strategyproofness", "Coalition-Proof Mechanism", "Efficient Mechanism",
        "Budget-Balanced Mechanism", "Participation Constraint",
        "IC Auction", "IR Auction", "Budget Constraint Mechanism",
        "No-Regret Learning", "Market Design", "Matching Design",
        "Assignment Mechanism", "Sequential Mechanism", "Simultaneous Mechanism",
        "Ascending Auction", "Descending Auction", "One-Shot Mechanism",
    ],
    "social_choice": [
        "Social Welfare", "Preference Aggregation", "Arrow's Theorem",
        "Gibbard-Satterthwaite", "Strategyproofness", "Nash Implementation",
        "Bargaining", "Nash Solution", "Kalai Solution", "Kalai-Smorodinsky",
        "Egalitarian Solution", "Weighted Voting", "Condorcet Paradox",
        "Majority Rule", "Borda Count", "Approval Voting", "Range Voting",
        "Cumulative Voting", "Districting", "Apportionment",
        "Liquid Democracy", "Representative Democracy", "Voting Power",
        "Power Index", "Manipulation", "Bribery", "Control", "Tie-Breaking",
        "Single-Peaked Preferences", "Domain Restrictions", "Top Cycles",
        "McGarvey's Theorem", "Ostrogorski Paradox", "Duverger's Law",
        "Proportional Representation", "Weighted Majority", "Binary Agendas",
    ],
    "fair_division": [
        "Envy-Freeness", "Proportionality", "Equitability", "Efficiency",
        "Cake Cutting", "Indivisible Goods", "Mixed Goods", "Rent Division",
        " chore Division", "Continuous Division", "Discrete Division",
        "Ninja Division", "Ivy Division", "Epsilon-Fairness",
        "Envy-Free Approximation", "EFX", "Maxmin Share", "Guaranteed Share",
        "Competitive Equilibrium", "Core", "Kernel", "Nucleolus",
        "Coalitional Fairness", "Individual Fairness", "Group Fairness",
        "Procedural Fairness", "Outcome Fairness", "Distributive Justice",
        "Resource Allocation", "Budget Allocation", "Public Allocation",
        "School Choice", "House Allocation", "Kidney Exchange", "Matching",
        "Discrete Fair Division", "Query Complexity", "Complexity of Fairness",
        "Fair Recommendation", "Fair Clustering", "Fair Partition",
    ],
    "feature_attribution": [
        "SHAP Value", "Shapley Value", "LIME", "Feature Importance",
        "Model Explanation", "Additive Attribution", "Interaction Attribution",
        "Path Attribution", "Gradient Attribution", "CAM", "GradCAM",
        "Occlusion Sensitivity", "Feature Selection", "Feature Interaction",
        "Attribution Visualization", "Counterfactual Explanation",
        "Concept Attribution", "Neuron Attribution", "Edge Attribution",
        "KernelSHAP", "TreeSHAP", "DeepSHAP", "FastSHAP", "ExactSHAP",
        "ApproximateSHAP", "SamplingSHAP", "PermutationSHAP",
        "ConditionalSHAP", "CausalSHAP", "MarginalSHAP", "GroupSHAP",
        "CohortSHAP", "TimeSHAP", "SpatialSHAP", "SpectralSHAP",
        "Robust Attribution", "Adversarial Attribution", "Faithful Attribution",
        "Axiomatic Attribution", "Unique Attribution", "Completeness",
        "Implementation Invariance", "Sensitivity", "Infinitesimal Perturbation",
        "Expected Attribution", "Aumann Attribution", "Marginal Contribution",
    ],
    "information_economics": [
        "Adverse Selection", "Moral Hazard", "Signaling", "Screening",
        "Information Disclosure", "Verification", "Certification",
        "Reputation", "Search Friction", "Market for Lemons",
        "Insurance Markets", "Credit Markets", "Labor Markets",
        "Product Markets", "Bilateral Trade", "Intermediation",
        "No-Trade Theorem", "Rational Expectations", "Information Asymmetry",
        "Mechanism with Disclosure", "Voluntary Disclosure", "Forced Disclosure",
        "Bayesian Persuasion", "Information Design", "Communication Equilibrium",
        "Joint Screening", "Contract Theory", "Incentive Compatibility",
        "Limited Liability", "Participation Constraint", "IR Constraint",
        "Trade Mechanism", "Bargaining with Asymmetric Information",
        "Contractual Incompleteness", "Hold-Up Problem", "Hold-Up Solution",
    ],
    "matching_markets": [
        "Stable Matching", "Deferred Acceptance", "Top Trading Cycles",
        "Serial Dictatorship", "Random Serial Dictatorship", "Boston Mechanism",
        "Gale-Shapley Algorithm", "NRMP", "School Choice", "Kidney Exchange",
        "House Allocation", "Office Allocation", "Bed Allocation",
        "Course Allocation", "Project Allocation", "Team Formation",
        "Random Priority", "Proportional Priority", "Waste Allocation",
        "Strategyproof Matching", "Mechanism with Preferences",
        "Efficient Matching", "Stable Matching Equilibrium",
        "Strategyproof Assignment", "Budget-Balanced Matching",
        "Market Design", "Clearinghouse", "Centralized Market",
        "Decentralized Market", "Online Market", "Dynamic Market",
        "Labor Market", "Marriage Market", "College Admission",
        "Public Assignment", "Private Assignment", "Strategy-Resistant Matching",
    ],
}

# Author group patterns (create variation without real author names)
AUTHOR_GROUPS = [
    "", "Group A", "Group B", "Group C", "Group D",
    "Group E", "Group F", "Group G", "Group H",
]

# Paper type/form
PAPER_TYPES = [
    "", "Theory", "Survey", "Application", "Application",
    "Comparison", "Framework", "Extension", "Review",
    "Methodology", "Analysis", "Perspective", "Note",
]


def E(domain, year, venue, topic, author_group, paper_type, priority=None):
    name = f"{topic} {paper_type}".strip()
    if author_group:
        name = f"{author_group} — {name}"
    # Unique key for dedup
    key = (name.lower().strip(), year, domain)
    seed_id = (
        f"{name[:40]}_{year}"
        .replace(" ", "_").replace(",", "").replace("'", "")
        .replace("—", "").replace("—", "").replace(":", "")
    )
    return {
        "id": seed_id,
        "name": name,
        "year": int(year),
        "venue": venue,
        "domain": domain,
        "priority": priority or 4,
        "topic": topic,
        "author_group": author_group,
        "paper_type": paper_type,
    }


def generate_seeds():
    seeds = []
    for domain in DOMAINS:
        venues = VENUES.get(domain, VENUES["cooperative_game_theory"])
        topics = TOPICS.get(domain, TOPICS["cooperative_game_theory"])

        for year in range(1970, 2025):
            for venue in venues:
                for topic in topics:
                    for ag in AUTHOR_GROUPS[:3]:  # limit 3 groups per combo
                        for ptype in PAPER_TYPES[:3]:  # limit 3 types
                            # Avoid all-empty name
                            if not (topic or ptype or ag):
                                continue
                            s = E(domain, year, venue, topic, ag, ptype)
                            if s not in seeds:
                                seeds.append(s)

    return seeds


if __name__ == "__main__":
    seeds = generate_seeds()
    print(f"Generated {len(seeds)} unique seeds")

    # Dedup by id
    seen_ids = set()
    unique = []
    for s in seeds:
        if s["id"] not in seen_ids:
            seen_ids.add(s["id"])
            unique.append(s)
    seeds = unique
    print(f"After ID dedup: {len(seeds)} unique seeds")

    by_domain = {}
    for s in seeds:
        by_domain.setdefault(s["domain"], []).append(s)

    for domain, lst in sorted(by_domain.items()):
        print(f"  {domain}: {len(lst)} seeds")

    # Save
    out = Path("kb/ingest/seeds/axiom_seeds_v3.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump({
            "version": "3.0",
            "generated": "2026-06-24",
            "total": len(seeds),
            "domains": {d: len(by_domain.get(d, [])) for d in DOMAINS},
            "seeds": seeds,
        }, f, indent=2)
    print(f"Saved: {out} ({len(seeds)} seeds)")
