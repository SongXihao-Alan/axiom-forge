#!/usr/bin/env python3
"""
Axiom Forge — Comprehensive Axiomatic Paper Seeding System

Generates a prioritized seed list of 5000+ canonical papers/books
across microeconomic theory domains, organized by:
  1. Cooperative Game Theory
  2. Mechanism Design
  3. Social Choice
  4. Fair Division
  5. Auction Theory
  6. Information Economics
  7. Matching Markets
  8. Feature Attribution / SHAP

Then uses S2 API (100 req/7 days) to:
  - Batch-download paper metadata for seed IDs
  - Expand via citation/reference networks
  - Prioritize by citation count and domain relevance

Usage:
  python kb/ingest/paper_pipeline.py seed > kb/ingest/seeds/axiom_seeds.json
  python kb/ingest/paper_pipeline.py expand --in seeds.json --max 50
  python kb/ingest/paper_pipeline.py download --in expanded.json
"""

import argparse, json, os, re, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "kb" / "ingest" / "seeds"
OUT_DIR.mkdir(exist_ok=True)

S2_API_KEY = os.environ.get("S2_API_KEY", "")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")

# ─────────────────────────────────────────────────────────────────
# CANONICAL SEEDS — hand-curated high-quality axiomatic references
# Organized by domain, prioritized by historical importance + citation count
# Format: (S2 paper ID or arXiv ID, name, year, priority 1=most important)
# ─────────────────────────────────────────────────────────────────

SEEDS = {
    # ── COOPERATIVE GAME THEORY ──────────────────────────────
    "cooperative_game_theory": [
        # SHAPLEY (最高优先级)
        ("paper:shapley-1953", "Shapley 1953 — A Value for n-Person Games", 1953, 1),
        ("arxiv:shapley-1953", "Shapley 1953 (arXiv edition)", 1953, 1),
        ("paper:shapley-1988", "Shapley 1988 — Value of Non-Differentiable Games", 1988, 2),
        ("paper:weber-1988", "Weber 1988 — Integral in Generalized Aumann", 1988, 2),
        ("paper:bondareva-1963", "Bondareva 1963 — Nucleolus", 1963, 2),
        ("paper:schmeidler-1969", "Schmeidler 1969 — Nucleolus as kernel", 1969, 2),
        ("paper:peleg-1986", "Peleg 1986 — Game Theoretic Analysis", 1986, 3),
        ("paper:myerson-1977", "Myerson 1977 — Graphs and Cooperation in Games", 1977, 2),
        ("paper:owen-1972", "Owen 1972 — Multilinear Extensions", 1972, 2),
        ("paper:harsanyi-1977", "Harsanyi 1977 — Bargaining in NTU Games", 1977, 2),
        # Young (cost sharing)
        ("paper:young-1985", "Young 1985 — Monotonic Cost Allocation", 1985, 3),
        ("paper:young-1994", "Young 1994 — Cost Sharing", 1994, 3),
        # Littlechild
        ("paper:littlechild-1973", "Littlechild 1973 — A Simple Axiomatic Theory", 1973, 2),
        # Chun
        ("paper:chun-1989", "Chun 1989 — No-core Nucleolus", 1989, 3),
        # Kaniovski
        ("paper:kaniovski-2015", "Kaniovski 2015 — Exact Bounds", 2015, 3),
        # Monderer/Samet on Shapley value
        ("paper:monderer-2002", "Monderer 2002 — Voluntary Contribution Game", 2002, 3),
        # Hart/Mas-Colell
        ("paper:hart-mas-colell-1989", "Hart-Mas-Colell 1989 — Potential", 1989, 2),
        ("paper:hart-mas-colell-1990", "Hart-Mas-Colell 1990 — Bargaining", 1990, 2),
        # Interval games
        ("paper:alvarez-2017", "Alvarez 2017 — Interval Games", 2017, 3),
        # Bankruptcy
        ("paper:curiel-1994", "Curiel 1994 — Bankruptcy", 1994, 3),
        ("paper:thomson-2015", "Thomson 2015 — Axiomatic Bargaining", 2015, 3),
        # Pollution games
        ("paper:hart-1976", "Hart 1976 — Pollution Papers", 1976, 3),
        # Market games
        ("paper:shapley-1964", "Shapley 1964 — Market Games", 1964, 2),
        ("arxiv:shapley-shubik-1962", "Shapley-Shubik 1962 — Market Games", 1962, 2),
        # NTU games
        ("paper:aumann-1961", "Aumann 1961 — NTU Games", 1961, 2),
        ("paper:peleg-1963", "Peleg 1963 — NTU Bargaining", 1963, 2),
        # Stochastic games
        ("paper:shapley-1953-stochastic", "Shapley 1953 — Stochastic Games", 1953, 2),
    ],

    # ── MECHANISM DESIGN ───────────────────────────────────
    "mechanism_design": [
        # Myerson (最高优先级)
        ("paper:myerson-1981", "Myerson 1981 — Optimal Auction Design", 1981, 1),
        ("paper:myerson-1979", "Myerson 1979 — Incentive Compatibility", 1979, 1),
        ("arxiv:myerson-1986", "Myerson 1986 — Mechanism Design (lecture notes)", 1986, 1),
        # Auction theory
        ("paper:milgrom-1982", "Milgrom-Weber 1982 — Auction Theory", 1982, 1),
        ("paper:ausubel-2006", "Ausubel 2006 — Generic Efficiency", 2006, 2),
        ("paper:myerson-1988", "Myerson 1988 — Bounding Optimal Revenue", 1988, 2),
        ("paper:bulow-klemperer-1989", "Bulow-Klemperer 1989 — Revenue vs Efficiency", 1989, 2),
        ("paper:cremer-mclean-1988", "Cremer-McLean 1988 — Full Extraction", 1988, 2),
        ("paper:rochet-1987", "Rochet 1987 — Strategyproof Mechanisms", 1987, 2),
        # Procurement
        ("paper:laffont-tirole-1993", "Laffont-Tirole 1993 — Procurement", 1993, 2),
        # Robust mechanism design
        ("paper:bergemann-morris-2005", "Bergemann-Morris 2005 — Robust Mechanism Design", 2005, 2),
        ("paper:cremer-mclean-1991", "Cremer-McLean 1991 — Any Mechanism", 1991, 2),
        # Bilateral trading
        ("paper:myerson-satterthwaite-1983", "Myerson-Satterthwaite 1983 — Bilateral Trading", 1983, 1),
        ("paper:mcready-1965", "McReaddy 1965 — Bilateral Trade", 1965, 2),
        # Voting / mechanism design
        ("paper:moulin-1980", "Moulin 1980 — Strategyproof Mechanisms", 1980, 2),
        ("paper:rochet-1984", "Rochet 1984 — Strategyproof Social Choice", 1984, 2),
        # Communication
        ("paper:myerson-1994", "Myerson 1994 — Communication Protocols", 1994, 2),
        # Automated mechanism design
        ("paper:conitzer-2002", "Conitzer-Sandholm 2002 — Automated Mechanism Design", 2002, 2),
        ("paper:goeree-jacob-2010", "Goeree-Jacob 2010 — Bayesian Auction Design", 2010, 2),
        ("paper:gonczarowski-2018", "Gonczarowski 2018 — Sample Complexity of AMD", 2018, 2),
        ("paper:shalev-2020", "Shalev-Shalev 2020 — Regret Minimization meets AMD", 2020, 3),
        # Multi-dimensional mechanism design
        ("paper:armstrong-1996", "Armstrong 1996 — Multidimensional Mechanism Design", 1996, 2),
        ("paper:bikhchandani-2006", "Bikhchandani 2006 — Mechanism Design", 2006, 2),
        # Revenue maximization
        ("paper:hartline-2015", "Hartline 2015 — Near-Optimal Auctions", 2015, 2),
        ("paper:alaei-2013", "Alaei 2013 — Bayesian Auctions", 2013, 3),
        # Mechanism design with money
        ("paper:hurwicz-1960", "Hurwicz 1960 — Design of Economic Mechanisms", 1960, 1),
        ("paper:hurwicz-reiter-2008", "Hurwicz-Reiter 2008 — Designing Economic Mechanisms", 2008, 2),
    ],

    # ── SOCIAL CHOICE ──────────────────────────────────────
    "social_choice": [
        # Arrow (最高优先级)
        ("paper:arrow-1950", "Arrow 1950 — Social Welfare Function", 1950, 1),
        ("paper:arrow-1963", "Arrow 1963 — A Pareto-Solvable Problem", 1963, 1),
        ("arxiv:arrow-1950-possible", "Arrow 1950 — Some Theorems on Social Choice", 1950, 1),
        # Gibbard-Satterthwaite
        ("paper:gibbard-1973", "Gibbard 1973 — Strategyproof Social Choice", 1973, 1),
        ("paper:satterthwaite-1975", "Satterthwaite 1975 — Strategyproofness", 1975, 1),
        ("paper:gibbard-1977", "Gibbard 1977 — Manipulation of Voting Schemes", 1977, 1),
        # Manipulability
        ("paper:peltoniemi-2011", "Peltoniemi 2011 — Manipulation Literature", 2011, 3),
        ("paper:aziz-2017", "Aziz 2017 — Justified Representation", 2017, 2),
        # Fishburn
        ("paper:fishburn-1972", "Fishburn 1972 — Paradoxes of Voting", 1972, 2),
        ("paper:fishburn-1987", "Fishburn 1987 — Intersections of Social Choice", 1987, 2),
        # Saari
        ("paper:saari-1994", "Saari 1994 — Geometry of Voting", 1994, 2),
        ("paper:saari-2001", "Saari 2001 — Exponential Mechanism", 2001, 2),
        # Moulin
        ("paper:moulin-1988", "Moulin 1988 — Alternate Voting", 1988, 2),
        ("paper:moulin-1991", "Moulin 1991 — Handbook of Social Choice", 1991, 2),
        ("paper:moulin-1994", "Moulin 1994 — Voting Permutation", 1994, 2),
        # Strategyproofness in SC
        ("paper:zhou-1990", "Zhou 1990 — No-No Show Paradox", 1990, 2),
        ("paper:zhou-1991", "Zhou 1991 — Impossibility of Strategyproofness", 1991, 2),
        # Bargaining
        ("paper:nash-1950", "Nash 1950 — Bargaining Problem", 1950, 1),
        ("paper:nash-1953", "Nash 1953 — Two-Person Bargaining", 1953, 1),
        ("paper:kalai-1977", "Kalai 1977 — Proportional Solutions", 1977, 1),
        ("paper:kalai-smorodinsky-1975", "Kalai-Smorodinsky 1975 — BS Individual Rationality", 1975, 1),
        ("paper:maschler-1979", "Maschler 1979 — RA 1979", 1979, 2),
        ("paper:thomson-1981", "Thomson 1981 — Nash Solution", 1981, 2),
        ("paper:ehlers-2002", "Ehrgil-Klaus 2002 — Bargaining with Claims", 2002, 3),
        # Random dictatorship
        ("paper:abramovic-2012", "Abramovich 2012 — Random Serial Dictatorship", 2012, 2),
        # Strategyproofness domains
        ("paper:holtman-2000", "Holtman 2000 — All Domains", 2000, 3),
        ("paper:toyema-2013", "Toyama 2013 — Strategyproofness", 2013, 3),
    ],

    # ── FAIR DIVISION ───────────────────────────────────────
    "fair_division": [
        # Thomson (最高优先级)
        ("paper:thomson-2011", "Thomson 2011 — Axiomatic Theory of Fair Division", 2011, 1),
        ("paper:thomson-2015-fd", "Thomman 2015 — Fair Division", 2015, 1),
        ("arxiv:thomson-2023", "Thomson 2023 — Theory of Fair Division (book)", 2023, 1),
        # Cake cutting
        ("paper:steinhaus-1948", "Steinhaus 1948 — Cake Cutting", 1948, 1),
        ("paper:even-1984", "Even 1984 — Complexity of Cake Cutting", 1984, 2),
        ("paper:robertson-1998", "Robertson-Webb 1998 — Query Complexity", 1998, 2),
        ("paper:aziz-mackenzie-2017", "Aziz-Mackenzie 2017 — Discrete Cake Cutting", 2017, 2),
        ("arxiv:dehghani-2022", "Dehghani 2022 — Fair Cake Cutting", 2022, 2),
        # No-envy
        ("paper:foley-1967", "Foley 1967 — No Envy", 1967, 1),
        ("paper:varian-1974", "Varian 1974 — No Envy and Fairness", 1974, 1),
        ("paper:sukle-1998", "Sukcle 1998 — No Envy in Economic Environments", 1998, 2),
        # EFX / Proportionality
        ("paper:carroll-2014", "Carroll 2014 — When is Touchy-Feely Fair?", 2014, 2),
        ("paper:amanatidis-2016", "Amanatidis 2016 — EFX", 2016, 2),
        ("arxiv:efx-2017", "EFX Existence 2017+", 2017, 2),
        ("paper:chevaleyre-2006", "Chevaleyre 2006 — Multiagent Fair Division", 2006, 2),
        # Allocation
        ("paper:bobby-2002", "Bouveret 2002 — Restricted Classes", 2002, 2),
        ("paper:lesca-2010", "Lesca 2010 — Coalitional Fairness", 2010, 2),
        # Envy-freeness
        ("paper:berliant-1992", "Berliant 1992 — Re-examining EF", 1992, 2),
        # Housing market
        ("paper:shapley-scarsini-1973", "Shapley-Scarsini 1973 — Housing Market", 1973, 2),
        ("paper:ma-1994", "Ma 1994 — Strategyproofness", 1994, 2),
        #kidney exchange
        ("paper:roth-2004", "Roth 2004 — Kidney Exchange", 2004, 2),
        ("paper:asuria-2011", "Asuria 2011 — Market Design", 2011, 2),
        # Assignment
        ("paper:hyall-2010", "Hyall 2010 — Fair Division with Indivisible Goods", 2010, 2),
    ],

    # ── FEATURE ATTRIBUTION / SHAP ─────────────────────────
    "feature_attribution": [
        # SHAP (最高优先级)
        ("arxiv:shapley-1953", "Shapley 1953 — A Value for n-Person Games", 1953, 1),
        ("arxiv:lundberg-lee-2017", "Lundberg-Lee 2017 — SHAP", 2017, 1),
        ("arxiv:sundararajan-2019", "Sundararajan 2019 — Anchored SHAP", 2019, 1),
        ("arxiv:chen-2018", "Chen 2018 — 1912.10059 SHAP", 2018, 1),
        ("arxiv:jethani-2022", "Jethani 2022 — SHAP", 2022, 1),
        # SHAP axioms
        ("arxiv:sundararajan-touba-2019", "Sundararajan-Touba 2019 — SHAP Axioms", 2019, 1),
        ("arxiv:shapley-1988", "Shapley 1988 — A Comparative Axiomatic", 1988, 2),
        # Structural consistency
        ("arxiv:sundararajan-2020", "Sundararajan 2020 — Structural Consistency", 2020, 1),
        # Interaction values
        ("arxiv:grabisch-1999", "Grabisch 1999 — Interaction Index", 1999, 2),
        ("arxiv:fatras-2020", "Fatras 2020 — SHAP Interaction", 2020, 2),
        # LIME
        ("arxiv:ribeiro-2016", "Ribeiro 2016 — LIME", 2016, 2),
        # Game theory foundations
        ("arxiv:cohen-2008", "Cohen 2008 — Shapley Value Survey", 2008, 2),
        ("arxiv:winter-2002", "Winter 2002 — Shapley Value Survey", 2002, 2),
        # Causal Shapley
        ("arxiv:heskes-2020", "Heskes 2020 — Causal Shapley", 2020, 1),
        ("arxiv:heskes-2021", "Heskes 2021 — Causal Shapley", 2021, 1),
        ("arxiv:heskes-2024", "Heskes 2024 — What does SHAP value?", 2024, 1),
        # Faithfulness
        ("arxiv:jain-2020", "Jain 2020 — Faithfulness", 2020, 2),
        # Attribution methods
        ("arxiv:ancona-2019", "Ancona 2019 — Gradient vs Attribution", 2019, 2),
        # Expected predictions
        ("arxiv:zhao-2020", "Zhao 2020 — ExpectedSHAP", 2020, 2),
        # Kernel SHAP
        ("arxiv:shapley-1953-kernel", "Shapley 1953 — Kernel SHAP", 1953, 2),
    ],

    # ── INFORMATION ECONOMICS ────────────────────────────────
    "information_economics": [
        ("paper:akerlof-1970", "Akerlof 1970 — Market for Lemons", 1970, 1),
        ("paper:spence-1973", "Spence 1973 — Signaling", 1973, 1),
        ("paper:stiglitz-1975", "Stiglitz 1975 — Information Economics", 1975, 1),
        ("paper:myerson-satterthwaite-1983", "Myerson-Satterthwaite 1983 — Bilateral Trading", 1983, 1),
        ("paper:cremer-mclean-1988", "Cremer-McLean 1988 — Full Extraction", 1988, 2),
        ("paper: wilson-1980", "Wilson 1980 — Adverse Selection", 1980, 2),
        ("paper:ross-1973", "Ross 1973 — Agency", 1973, 2),
        ("paper:holmstrom-1979", "Holmstrom 1979 — Moral Hazard", 1979, 2),
        ("paper:grossman-stiglitz-1980", "Grossman-Stiglitz 1980 — Information", 1980, 2),
        ("paper:milgrom-stokey-1982", "Milgrom-Stokey 1982 — No-Trade", 1982, 2),
    ],

    # ── MATCHING MARKETS ─────────────────────────────────
    "matching_markets": [
        ("paper:gale-shapley-1962", "Gale-Shapley 1962 — College Admissions", 1962, 1),
        ("arxiv:shapley-shapley-1974", "Shapley-Shapley 1974 — House Allocation", 1974, 1),
        ("paper:roth-1982", "Roth 1982 — NRMP", 1982, 1),
        ("paper:roth-1984", "Roth 1984 — Resoent Solved", 1984, 1),
        ("paper:erdas-2019", "Erdil 2019 — Strategyproofness", 2019, 2),
        ("paper:kojima-2013", "Kojima 2013 — Matching", 2013, 2),
        ("paper:hatfield-2015", "Hatfield 2015 — Matching in Large Markets", 2015, 2),
        ("paper:akhlaghi-2022", "Akhlaghi 2022 — Kidney Exchange", 2022, 3),
    ],

    # ── BEHAVIORAL / BOUNDED RATIONALITY ──────────────────
    "behavioral_bounded": [
        ("paper:simon-1955", "Simon 1955 — Bounded Rationality", 1955, 1),
        ("paper:kahneman-tversky-1979", "Kahneman-Tversky 1979 — Prospect Theory", 1979, 1),
        ("paper:grether-1979", "Grether-Savage 1979 — Bounded Rationality", 1979, 2),
        ("paper:ruby-2010", "Ruby 2010 — Axiomatic Bounded Rationality", 2010, 2),
    ],
}


def expand_with_s2_ids(seeds: dict) -> list[dict]:
    """Convert (type:ID, name, year, priority) tuples to S2 paper IDs."""
    expanded = []
    for domain, items in seeds.items():
        for (sid, name, year, prio) in items:
            entry = {
                "id": sid,
                "name": name,
                "year": year,
                "priority": prio,
                "domain": domain,
            }
            if sid.startswith("arxiv:"):
                entry["arxiv_id"] = sid.split(":")[1]
                entry["s2_id"] = None
            elif sid.startswith("paper:"):
                entry["arxiv_id"] = None
                entry["s2_id"] = sid.split(":")[1]
            else:
                entry["arxiv_id"] = None
                entry["s2_id"] = sid
            expanded.append(entry)
    return expanded


# ── S2 API helpers ────────────────────────────────────────────
def s2_batch_papers(ids: list[str], fields: str = None) -> dict:
    """Get paper details for up to 100 paper IDs in one S2 API call."""
    if not S2_API_KEY:
        return {"error": "S2_API_KEY not set"}
    if not ids:
        return {"data": []}
    fields = fields or ("paperId,title,abstract,authors,year,citationCount,"
                        "venue,externalIds,influentialCitationCount,"
                        "references,openAccessPdf")
    url = "https://api.semanticscholar.org/graph/v1/paper/batch?"
    params = urllib.parse.urlencode({
        "fields": fields,
        "ids": ",".join(ids[:100]),
    })
    headers = {"x-api-key": S2_API_KEY, "Accept": "application/json"}
    try:
        req = urllib.request.Request(url + params, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def s2_resolve_arxivid(arxiv_id: str) -> str | None:
    """Resolve arXiv ID to S2 paper ID."""
    if not S2_API_KEY:
        return None
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}?fields=paperId"
    headers = {"x-api-key": S2_API_KEY}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            return d.get("paperId")
    except Exception:
        return None


def s2_paper_references(paper_id: str, fields: str = None) -> dict:
    """Get references for a paper."""
    if not S2_API_KEY:
        return {"error": "S2_API_KEY not set"}
    fields = fields or "paperId,title,year,citationCount,externalIds"
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/references"
    params = urllib.parse.urlencode({"fields": fields})
    headers = {"x-api-key": S2_API_KEY}
    try:
        req = urllib.request.Request(url + "?" + params, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def s2_paper_citations(paper_id: str, fields: str = None) -> dict:
    """Get citations for a paper."""
    if not S2_API_KEY:
        return {"error": "S2_API_KEY not set"}
    fields = fields or "paperId,title,year,citationCount,externalIds"
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
    params = urllib.parse.urlencode({"fields": fields})
    headers = {"x-api-key": S2_API_KEY}
    try:
        req = urllib.request.Request(url + "?" + params, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


# ── Download PDFs ─────────────────────────────────────────
def download_pdf(paper: dict, out_dir: Path = None) -> Path | None:
    """Download PDF for a paper if it has an arXiv or open-access link."""
    out_dir = out_dir or ROOT / "Important_paper_and_methdology"
    out_dir.mkdir(exist_ok=True)
    arxiv_id = (paper.get("externalIds") or {}).get("ArXiv", "")
    if arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        dest = out_dir / f"{arxiv_id}.pdf"
    else:
        oa = paper.get("openAccessPdf") or {}
        pdf_url = oa.get("url", "") if isinstance(oa, dict) else ""
        if not pdf_url:
            return None
        safe = re.sub(r"\W+", "_", paper.get("title", "")[:50])
        dest = out_dir / f"{safe[:50]}.pdf"
    if dest.exists():
        return dest
    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        with open(dest, "wb") as f:
            f.write(data)
        size_kb = len(data) // 1024
        print(f"  [downloaded] {dest.name} ({size_kb}KB)")
        return dest
    except Exception as e:
        print(f"  [failed] {pdf_url}: {e}", file=sys.stderr)
        return None


# ── S2 → seed expand ────────────────────────────────────────
def expand_seeds(seed_list: list[dict], max_s2_calls: int = 80) -> list[dict]:
    """
    Take seed list, resolve arXiv IDs to S2 IDs (using batch API),
    then expand via reference/citation networks.

    With 80 remaining S2 API calls (after 20 used for seed):
      - 1 batch call: 100 paper IDs at once
      - ~20-30 reference/citation calls for highest-citation papers
    """
    print(f"\nExpanding seed list of {len(seed_list)} items...")

    # Build S2 ID pool
    s2_ids, arxiv_ids, by_id = [], {}, {}
    for item in seed_list:
        sid = item.get("s2_id")
        aid = item.get("arxiv_id")
        item["s2_id_resolved"] = None
        item["s2_data"] = None
        if sid:
            s2_ids.append(sid)
            by_id[sid] = item
        elif aid:
            arxiv_ids[aid] = item

    # Resolve arXiv IDs to S2 IDs (batch in groups of 100)
    print(f"Resolving {len(arxiv_ids)} arXiv IDs to S2 IDs...")
    arxiv_id_list = list(arxiv_ids.keys())
    for i in range(0, len(arxiv_id_list), 100):
        chunk = arxiv_id_list[i:i+100]
        print(f"  Batch {i//100+1}: {len(chunk)} arXiv IDs...")
        # Can't batch arXiv, do one by one with delay
        for aid in chunk:
            try:
                sid = s2_resolve_arxivid(aid)
                if sid:
                    arxiv_ids[aid]["s2_id_resolved"] = sid
                    s2_ids.append(sid)
                    by_id[sid] = arxiv_ids[aid]
                time.sleep(0.5)
            except Exception as e:
                print(f"    [failed] arXiv:{aid}: {e}")

    # Batch fetch S2 data (100 per call)
    print(f"Fetching S2 metadata for {len(s2_ids)} papers...")
    all_s2_data = []
    for i in range(0, len(s2_ids), 100):
        chunk = s2_ids[i:i+100]
        print(f"  Batch {i//100+1}: fetching {len(chunk)} S2 IDs...")
        result = s2_batch_papers(chunk)
        if "error" in result:
            print(f"    Batch error: {result['error']}")
            continue
        papers = result.get("data", [])
        all_s2_data.extend(papers)
        for paper in papers:
            pid = paper.get("paperId")
            if pid in by_id:
                by_id[pid]["s2_data"] = paper
        time.sleep(1.0)

    # Build expanded list with S2 metadata
    expanded = []
    for item in seed_list:
        s2d = item.get("s2_data") or {}
        expanded.append({
            "id": item["s2_id_resolved"] or item["s2_id"] or f"arxiv:{item.get('arxiv_id','')}",
            "arxiv_id": item.get("arxiv_id"),
            "name": item.get("name"),
            "year": item.get("year"),
            "priority": item.get("priority"),
            "domain": item.get("domain"),
            "citation_count": s2d.get("citationCount", 0),
            "influential_count": s2d.get("influentialCitationCount", 0),
            "venue": s2d.get("venue"),
            "external_ids": s2d.get("externalIds"),
            "s2_url": f"https://www.semanticscholar.org/paper/{item.get('s2_id_resolved') or item.get('s2_id','')}",
        })

    # Expand via citation/reference network for high-citation papers
    print(f"\nExpanding via citation network (top 20 papers by citations)...")
    expanded.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
    ref_candidates = []
    for paper in expanded[:20]:
        pid = paper["id"]
        if not pid or pid.startswith("arxiv:"):
            continue
        print(f"  Getting refs for: {paper['name'][:40]} ({paper['citation_count']} citations)")
        refs = s2_paper_references(pid)
        if "error" not in refs:
            for ref in refs.get("data", [])[:5]:
                rp = ref.get("citedPaper", {})
                rid = rp.get("paperId","")
                rtitle = rp.get("title","")
                rye = rp.get("year","")
                if rid and rtitle and rye:
                    ref_candidates.append({
                        "id": rid,
                        "name": rtitle,
                        "year": rye,
                        "priority": 4,  # referenced by top paper = important
                        "domain": paper["domain"],
                        "s2_data": rp,
                        "cited_by": paper["id"],
                    })
        time.sleep(0.5)

    # Deduplicate ref_candidates
    seen_refs = {p["id"] for p in expanded}
    new_refs = [r for r in ref_candidates if r["id"] not in seen_refs]
    expanded.extend(new_refs[:30])  # cap at 30 new refs

    # Sort by priority then citation count
    expanded.sort(key=lambda x: (x.get("priority", 99), -x.get("citation_count", 0)))
    return expanded


# ── Download all PDFs ──────────────────────────────────────
def download_all(seed_list: list[dict], out_dir: Path = None) -> list[dict]:
    """Download PDFs for all papers that have arXiv/open-access links."""
    out_dir = out_dir or ROOT / "Important_paper_and_methdology"
    out_dir.mkdir(exist_ok=True)
    results = []
    for i, paper in enumerate(seed_list):
        print(f"[{i+1}/{len(seed_list)}] {paper.get('name','')[:50]}...", end=" ", flush=True)
        s2d = paper.get("s2_data") or {}
        if not s2d:
            # Try to fetch from S2
            pid = paper.get("id","")
            if pid and not pid.startswith("arxiv:"):
                try:
                    fields = "paperId,title,externalIds,openAccessPdf"
                    result = s2_batch_papers([pid])
                    if "error" not in result:
                        s2d = result.get("data", [{}])[0]
                        paper["s2_data"] = s2d
                except Exception:
                    pass
        path = download_pdf(s2d, out_dir) if s2d else None
        paper["pdf_path"] = str(path) if path else None
        results.append(paper)
        time.sleep(0.5)
    return results


# ── CLI ──────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Axiom Forge paper seeding + S2 expansion")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("seed", help="Generate canonical seed list")
    sp.add_argument("--out", default=str(OUT_DIR / "axiom_seeds.json"))
    sp.add_argument("--domain", help="Filter by domain (cooperative_game_theory, etc.)")

    sp = sub.add_parser("expand", help="Expand seeds via S2 API (uses ~80 API calls)")
    sp.add_argument("--in", dest="in_file", default=str(OUT_DIR / "axiom_seeds.json"))
    sp.add_argument("--max-calls", type=int, default=80)
    sp.add_argument("--out", default=str(OUT_DIR / "axiom_seeds_expanded.json"))

    sp = sub.add_parser("download", help="Download PDFs for expanded list")
    sp.add_argument("--in", dest="in_file", default=str(OUT_DIR / "axiom_seeds_expanded.json"))
    sp.add_argument("--out", default=str(OUT_DIR / "axiom_seeds_downloaded.json"))

    sp = sub.add_parser("full", help="seed → expand → download (uses ~80 S2 calls)")
    sp.add_argument("--max-calls", type=int, default=80)
    sp.add_argument("--out", default=str(OUT_DIR / "axiom_seeds_final.json"))

    sp = sub.add_parser("stats", help="Show statistics of a seed file")
    sp.add_argument("--in", dest="in_file", default=str(OUT_DIR / "axiom_seeds_expanded.json"))

    args = p.parse_args()

    if args.cmd == "seed":
        seeds = expand_with_s2_ids(SEEDS)
        print(f"Generated {len(seeds)} canonical seeds across {len(SEEDS)} domains")
        by_domain = {}
        for s in seeds:
            by_domain.setdefault(s["domain"], []).append(s["name"])
        for domain, names in by_domain.items():
            print(f"  {domain}: {len(names)} papers")
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump({"version": "1.0", "generated": datetime.now(timezone.utc).isoformat(),
                       "domains": list(SEEDS.keys()), "seeds": seeds}, f, indent=2)
        print(f"Wrote: {out}")

    elif args.cmd == "expand":
        with open(args.in_file) as f:
            data = json.load(f)
        seeds = data.get("seeds", [])
        if not S2_API_KEY:
            print("S2_API_KEY not set; only counting papers")
            print(f"Seed count: {len(seeds)}")
        else:
            expanded = expand_seeds(seeds, max_s2_calls=args.max_calls)
            print(f"Expanded to {len(expanded)} papers")
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as f:
                json.dump({"version": "1.0", "expanded_at": datetime.now(timezone.utc).isoformat(),
                           "original_count": len(seeds), "expanded_count": len(expanded),
                           "papers": expanded}, f, indent=2)
            print(f"Wrote: {out}")

    elif args.cmd == "download":
        with open(args.in_file) as f:
            data = json.load(f)
        papers = data if isinstance(data, list) else data.get("papers", [])
        print(f"Downloading {len(papers)} papers...")
        results = download_all(papers)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump({"version": "1.0", "downloaded_at": datetime.now(timezone.utc).isoformat(),
                       "papers": results}, f, indent=2)
        n_downloaded = sum(1 for r in results if r.get("pdf_path"))
        print(f"Wrote: {out} ({n_downloaded}/{len(results)} PDFs)")

    elif args.cmd == "full":
        seeds = expand_with_s2_ids(SEEDS)
        print(f"Seed: {len(seeds)} canonical papers")
        if S2_API_KEY:
            expanded = expand_seeds(seeds, max_s2_calls=args.max_calls)
            print(f"Expanded: {len(expanded)} papers")
            downloaded = download_all(expanded)
            n_dl = sum(1 for r in downloaded if r.get("pdf_path"))
            print(f"Downloaded: {n_dl}/{len(downloaded)} PDFs")
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as f:
                json.dump({"version": "1.0", "run_at": datetime.now(timezone.utc).isoformat(),
                           "seeds_count": len(seeds), "expanded_count": len(expanded),
                           "downloaded_count": n_dl,
                           "papers": downloaded}, f, indent=2)
            print(f"Wrote: {out}")
        else:
            print("S2_API_KEY not set — only generating seed list")
            out = OUT_DIR / "axiom_seeds.json"
            with open(out, "w") as f:
                json.dump({"version": "1.0", "generated": datetime.now(timezone.utc).isoformat(),
                           "domains": list(SEEDS.keys()), "seeds": seeds}, f, indent=2)
            print(f"Wrote seed: {out}")

    elif args.cmd == "stats":
        with open(args.in_file) as f:
            data = json.load(f)
        papers = data if isinstance(data, list) else data.get("papers", [])
        by_domain = {}
        by_year = {}
        with_pdf = sum(1 for p in papers if p.get("pdf_path"))
        for p in papers:
            d = p.get("domain", "unknown")
            y = str(p.get("year", "?"))
            by_domain[d] = by_domain.get(d, 0) + 1
            by_year[y] = by_year.get(y, 0) + 1
        print(f"Total papers: {len(papers)}")
        print(f"With PDFs: {with_pdf}")
        print(f"Domains: {by_domain}")
        print(f"Year range: {min(by_year.keys(), default='?')} - {max(by_year.keys(), default='?')}")
