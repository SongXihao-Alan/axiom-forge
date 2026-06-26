#!/usr/bin/env python3
"""
Z3 counterexample checker for axiom formal statements.
Supports 3-tier parsing:

  Tier A: Pattern detection (instant, regex-based)
  Tier B: Direct Z3 parsing (ms-level)
  Tier C: LLM-guided translation to SMT-LIB (used when Tier A/B fail)

3 modes:
  refute  — negate the axiom, check if satisfiable (sat = axiom is wrong)
  consistency — check if axiom is satisfiable (unsat = self-contradicting)
  full    — run all tiers

Also detects: vacuous, contradiction, tautology.
"""

import argparse, json, re, sys, time
from pathlib import Path

try:
    from z3 import *
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False

# ── Tier A: Pattern detection (instant, no Z3 needed) ───────────────
PATTERNS = [
    # Vacuous: quantified over empty set
    (r"∈∅", "vacuous"),
    (r"in_empty_set", "vacuous"),
    (r"∀.*?∈\s*∅", "vacuous"),
    (r"forall.*?in.*?emptyset", "vacuous"),
    (r"∀.*?empty", "vacuous"),
    (r"⊥", "falsum"),
    # Contradiction: p ∧ ¬p
    (r"∧.*?¬", "contradiction"),
    (r"And.*?Not", "contradiction"),
    # Tautology: A ↔ A
    (r"↔.*?↔", "tautology"),
    (r"==.*?==", "tautology"),
    # Trivial: True ↔ True
    (r"True.*True|True", "tautology"),
]


def detect_patterns(formal: str) -> list[str]:
    """Quick regex scan for known vacuous/contradiction/tautology patterns."""
    found = []
    for pattern, label in PATTERNS:
        if re.search(pattern, formal, re.IGNORECASE):
            found.append(label)
    return list(set(found))


# ── Tier B: Direct Z3 parsing ───────────────────────────────────────
def build_z3_expr(formal: str):
    """
    Parse formal statement into a Z3 expression.
    Supports SHAP/mechanism-design notation + SMT-LIB.
    """
    s = formal
    # Normalize unicode
    s = s.replace("∈", " in ").replace("∧", " and ").replace("∨", " or ")
    s = s.replace("¬", "Not ").replace("≠", " != ").replace("↔", " == ")
    s = s.replace("→", " Implies ").replace("∀", "ForAll").replace("∃", "Exists")
    s = s.replace("Σ", "Sum").replace("φ", "phi").replace("Φ", "Phi")
    s = s.replace("∂", "delta").replace("Δ", "Delta")
    s = s.replace("β", "beta").replace("λ", "lambda")
    s = s.replace("₀", "_0").replace("₁", "_1").replace("₂", "_2")
    s = s.replace("≤", " <=").replace("≥", " >=").replace("·", " * ")
    s = re.sub(r"\s+", " ", s).strip()

    safe = {
        "Real": Real, "Int": Int, "Bool": Bool, "String": String,
        "And": And, "Or": Or, "Not": Not,
        "Implies": Implies, "If": If, "ITE": If,
        "ForAll": ForAll, "Exists": Exists,
        "Sum": lambda *a: sum(a),
        "Abs": Abs,
        "True": True, "False": False,
        "SI_i": Real("SI_i"), "SI_j": Real("SI_j"),
        "phi_i": Real("phi_i"), "phi_ix": Real("phi_ix"),
        "f": Real("f"), "fhat": Real("fhat"),
        "beta": Real("beta"),
        "x": Real("x"), "X": Real("X"),
        "v_N": Real("v_N"), "w": Real("w"),
        "i": Int("i"), "j": Int("j"), "n": Int("n"),
        "S": Int("S"), "T": Int("T"), "N": Int("N"),
    }

    for var in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', s):
        if var not in safe and var[0].isupper() or var in ("i","j","n","x","S","T","N"):
            try:
                safe[var] = Real(var)
            except Exception:
                pass

    try:
        return eval(s, {"__builtins__": {}}, safe)
    except Exception:
        pass
    try:
        return parse_smtlib_string(s)
    except Exception:
        raise ValueError(f"Cannot parse: {s[:80]}")


def verify_z3(expr, mode: str):
    """Run Z3 on a parsed expression. Returns (status, model, time_ms)."""
    solver = Solver()
    solver.set(timeout=15000)
    try:
        if mode == "refute":
            solver.add(Not(expr))
            check = solver.check()
        elif mode == "consistency":
            solver.add(expr)
            check = solver.check()
        else:
            raise ValueError(f"Unknown mode: {mode}")

        if check == sat:
            m = solver.model()
            return "sat", {str(d): str(m[d]) for d in m.decls() if m[d] is not None}
        elif check == unsat:
            return "unsat", None
        return "unknown", None
    except Exception as e:
        return "error", str(e)[:100]


# ── Tier C: LLM-guided translation to SMT-LIB ───────────────────────
Z3_TRANSLATOR_PROMPT = """You are a formal verification expert. Your task is to translate a mathematical statement into a valid SMT-LIB 2 expression for Z3 solver.

RULES:
- Use only Z3-supported operators: and, or, not, =>, =, !=, <, <=, >, >=, +, -, *, /, forAll, exists
- Declare all variables with their sort: (declare-const x Real) or (declare-fun x () Real)
- Foralls: (forall ((x Real)) (and ...))
- Exists: (exists ((x Real)) (and ...))
- Comparisons must be Booleans
- DO NOT use: sum, Σ, φ, ∂, ∈ symbols — expand them
- Translate "SI_i > 0" → (> SI_i 0)
- Translate "φ_i(fhat, x) > 0" → (> (phi_ix fhat x) 0)
- Translate "v(S) = E[f|X_S]" → (v S) = ...

STATEMENT:
{formal}

OUTPUT: ONLY the SMT-LIB expression, nothing else. Start with (assert ...) or the bare formula.

EXAMPLES:
Input:  "SI_i > 0  ==>  exists x: phi_i(fhat, x) > 0"
Output: (=> (> SI_i 0) (exists ((x Real)) (> (phi_ix fhat x) 0)))

Input:  "forall x: if x in S then f(x) >= 0"
Output: (forall ((x Real)) (=> (in S x) (>= (f x) 0)))
"""


def _call_m3(prompt: str, user: str, max_tokens: int = 800) -> str:
    import urllib.request, urllib.error, json
    api_key = ""
    for p in [Path(__file__).resolve().parent.parent.parent / ".env",
              Path.home() / ".axiom-forge.env"]:
        try:
            for line in p.read_text().splitlines():
                if "MINIMAX_API_KEY" in line:
                    api_key = line.split("=", 1)[1].strip()
        except Exception:
            pass
    try:
        api_key = api_key or __import__("os").getenv("MINIMAX_API_KEY", "")
    except Exception:
        pass

    if not api_key:
        return "ERROR: no MINIMAX_API_KEY"

    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user}
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    try:
        req = urllib.request.Request(
            "https://api.minimaxi.com/v1/text/chatcompletion_v2",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = json.loads(resp.read())["choices"][0]["message"]["content"]
            return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    except Exception as e:
        return f"ERROR: {e}"


def llm_translate_to_smtlib(formal: str) -> tuple[str, str]:
    """
    Use LLM to translate informal formal to SMT-LIB.
    Returns (smtlib_expr, error_or_success).
    """
    user = f"## Statement to translate\n\n{formal}\n\n## Output:"
    raw = _call_m3(Z3_TRANSLATOR_PROMPT.format(formal=formal), user)
    if raw.startswith("ERROR"):
        return "", raw
    # Strip markdown fences
    m = re.search(r"```(?:smtlib)?\s*(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    return raw.strip(), "ok"


def verify_z3_smtlib(smtlib_expr: str, mode: str):
    """Parse SMT-LIB string and run Z3."""
    try:
        expr = parse_smtlib_string(smtlib_expr)
    except Exception as e:
        return "unknown", f"smtlib parse error: {e}"

    solver = Solver()
    solver.set(timeout=15000)
    try:
        if mode == "refute":
            solver.add(Not(expr))
            check = solver.check()
        elif mode == "consistency":
            solver.add(expr)
            check = solver.check()
        else:
            return "unknown", "unknown mode"

        if check == sat:
            m = solver.model()
            return "sat", {str(d): str(m[d]) for d in m.decls() if m[d] is not None}
        elif check == unsat:
            return "unsat", None
        return "unknown", None
    except Exception as e:
        return "error", str(e)[:100]


# ── Main verification function ────────────────────────────────────────
def verify_axiom(axiom_id: str, formal_stmt: str, mode: str = "refute") -> dict:
    """
    3-tier verification:
      Tier A: pattern regex (instant)
      Tier B: direct Z3 (ms-level)
      Tier C: LLM translation → Z3 (used when A+B fail AND formal is non-empty)

    Returns:
      status: "sat" | "unsat" | "vacuous" | "contradiction" | "tautology" | "unknown" | "error"
      tier: "A" | "B" | "C" (which tier gave the verdict)
      flags: list of detected issues
      model: counterexample if sat
      time_ms: elapsed time
      smtlib_translation: (Tier C only) the LLM-generated SMT-LIB
      error: error message if error
    """
    result = {
        "axiom": axiom_id,
        "mode": mode,
        "status": "unknown",
        "tier": None,
        "flags": [],
        "model": None,
        "smtlib_translation": None,
        "time_ms": 0.0,
        "error": None,
    }
    if not formal_stmt or not formal_stmt.strip():
        result["status"] = "no_formal"
        return result

    start = time.time()

    # ── Tier A: Pattern detection ─────────────────────────────────
    flags = detect_patterns(formal_stmt)
    result["flags"] = flags

    if "vacuous" in flags:
        result["status"] = "vacuous"
        result["tier"] = "A"
        result["time_ms"] = round((time.time() - start) * 1000, 1)
        return result
    if "contradiction" in flags:
        result["status"] = "contradiction"
        result["tier"] = "A"
        result["time_ms"] = round((time.time() - start) * 1000, 1)
        return result
    if "tautology" in flags:
        result["status"] = "tautology"
        result["tier"] = "A"
        result["time_ms"] = round((time.time() - start) * 1000, 1)
        return result

    # ── Tier B: Direct Z3 ──────────────────────────────────────────
    if not Z3_AVAILABLE:
        result["status"] = "error"
        result["error"] = "z3-solver not installed"
        result["tier"] = "B_error"
        result["time_ms"] = round((time.time() - start) * 1000, 1)
        return result

    try:
        expr = build_z3_expr(formal_stmt)
        status, model = verify_z3(expr, mode)
        result["status"] = status
        result["model"] = model
        result["tier"] = "B"
    except Exception as e:
        status_str = str(e)
        result["tier"] = "B_fail"
        # Tier B failed → try Tier C
        if "Cannot parse" in status_str or "parse" in status_str.lower():
            result["tier"] = "C_try"

    # ── Tier C: LLM-guided SMT-LIB translation ───────────────────────
    if result["tier"] in ("B_fail", "B_unknown", "C_try"):
        smtlib, llm_err = llm_translate_to_smtlib(formal_stmt)
        if llm_err == "ok" and smtlib:
            result["smtlib_translation"] = smtlib
            status, model = verify_z3_smtlib(smtlib, mode)
            if status in ("sat", "unsat"):
                result["status"] = status
                result["model"] = model
                result["tier"] = "C"
            elif status == "unknown":
                result["tier"] = "C_fail"
            elif status == "error":
                result["error"] = f"Tier C: {model}"
                result["tier"] = "C_error"
        else:
            result["tier"] = "C_error"
            result["error"] = llm_err

    result["time_ms"] = round((time.time() - start) * 1000, 1)
    return result


# ── Human-readable output ──────────────────────────────────────────────
STATUS_ICON = {
    "sat": "❌ REFUTED (counterexample found)",
    "unsat": "✅ CONSISTENT (no counterexample)",
    "vacuous": "⚠ VACUOUS (quantified over empty set)",
    "contradiction": "❌ CONTRADICTION (p ∧ ¬p)",
    "tautology": "⚠ TAUTOLOGY (always true)",
    "unknown": "⚠ UNKNOWN",
    "no_formal": "— NO FORMAL",
    "error": "⚠ ERROR",
}


def print_result(result: dict):
    icon = STATUS_ICON.get(result["status"], result["status"])
    print(f"{result['axiom']} [{result['tier']}]: {icon} ({result['time_ms']}ms)")
    if result.get("flags"):
        print(f"  Flags: {result['flags']}")
    if result.get("model"):
        print(f"  Counterexample: {result['model']}")
    if result.get("smtlib_translation"):
        print(f"  SMT-LIB: {result['smtlib_translation'][:100]}")
    if result.get("error"):
        print(f"  Error: {result['error']}")


# ── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Z3 axiom verifier (3-tier: pattern → Z3 → LLM)")
    p.add_argument("--axiom", required=True)
    p.add_argument("--formal", required=True)
    p.add_argument("--mode", choices=["refute", "consistency"], default="refute")
    p.add_argument("--output", required=True)
    p.add_argument("--no-llm", dest="use_llm", action="store_false", default=True,
                    help="Skip Tier C LLM translation")
    args = p.parse_args()

    r = verify_axiom(args.axiom, args.formal, args.mode)
    print_result(r)

    with open(args.output, "w") as f:
        json.dump(r, f, indent=2)
