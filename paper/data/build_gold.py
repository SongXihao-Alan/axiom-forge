#!/usr/bin/env python3
"""
Lane A — Build gold.json from the manually-annotated items below.

Each item has a 1-5 score per rubric dimension, plus a 1-sentence justification.
Items are drawn from kb/nodes/ — the AX-SC-001 example, the 8 axioms, 10 theorems,
selected diktats, value_anchors, literature, scenarios, and tradeoffs.

Total: 80 real items + 30 distractors = 110 items.
"""
import json
from pathlib import Path

# =============================================================================
# Real items, hand-scored. Format: dict with all fields needed for an item.
# =============================================================================

REAL_ITEMS = [
    # ---------- AXIOMS (8) ----------
    {
        "id": "AX-SC-001", "type": "axiom",
        "source": "kb/nodes/axioms/AX-SC-001.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "The NL statement is clear once SI and φ are known, but assumes reader knows Structural Importance.",
            "novelty": "Genuinely new — distinguishes f (true structure) from f̂ (predictor), an asymmetry missing from prior axioms.",
            "internal_consistency": "Quantifiers are tight; no scope error; the implication is well-formed.",
            "empirical_grounding": "Has explicit Heskes 2021 citation with page/line; anchors are well populated; some supporters are implicit rather than direct.",
            "actionability": "Directly testable: build f with SI_1>0, set f̂=0, check φ_1=0 → SC violated. Demonstrated in TH-IMP-501 proof sketch."
        },
        "tier": "easy",
    },
    {
        "id": "AX-SHAP-EFF", "type": "axiom",
        "source": "kb/nodes/axioms/AX-SHAP-EFF.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Σ_i φ_i = f̂(x) is one equation and trivially parseable.",
            "novelty": "Standard Shapley axiom from Shapley 1953; not new in 2026.",
            "internal_consistency": "Tautologically consistent; simple linear identity.",
            "empirical_grounding": "Cites Shapley 1953 and Lundberg-Lee 2017; experimentally validated in industrial SHAP implementations.",
            "actionability": "A unit test summing attribution outputs and comparing to f̂(x) is one line of code."
        },
        "tier": "easy",
    },
    {
        "id": "AX-SHAP-SYM", "type": "axiom",
        "source": "kb/nodes/axioms/AX-SHAP-SYM.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 4, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Clear in intent; the formal ∀ a, b clause is slightly verbose but unambiguous.",
            "novelty": "Classical Shapley 1953; restatement in attribution context.",
            "internal_consistency": "Sound; the implication is well-formed.",
            "empirical_grounding": "Cites Shapley 1953 and Lundberg-Lee 2017.",
            "actionability": "Testable: swap features i, j across many inputs and check attribution equality."
        },
        "tier": "easy",
    },
    {
        "id": "AX-SHAP-DUM", "type": "axiom",
        "source": "kb/nodes/axioms/AX-SHAP-DUM.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "If f̂ doesn't depend on X_i, then φ_i = 0 — easy to read.",
            "novelty": "Classical; goes by many names (Dummy, Null-player, Sensitivity-b).",
            "internal_consistency": "Tight quantifiers; sound.",
            "empirical_grounding": "Cites Shapley 1953, Sundararajan-Taly-Yan 2017, Heskes 2020.",
            "actionability": "Test: take an input, vary X_i while holding others, check φ_i is unchanged, then φ_i must equal 0."
        },
        "tier": "easy",
    },
    {
        "id": "AX-SHAP-CONS", "type": "axiom",
        "source": "kb/nodes/axioms/AX-SHAP-CONS.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Monotonicity statement is clear once you know v and v̂.",
            "novelty": "L17's consistency; not new.",
            "internal_consistency": "Sound; well-formed implication with strict inequality.",
            "empirical_grounding": "Cites L17; status=seed suggests it has not been independently verified.",
            "actionability": "Testable: perturb v̂ so all marginal contributions rise; check φ_i non-decreasing."
        },
        "tier": "medium",
    },
    {
        "id": "AX-THOMSON-NOENVY", "type": "axiom",
        "source": "kb/nodes/axioms/AX-THOMSON-NOENVY.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "No agent prefers another's bundle — one sentence, one equation.",
            "novelty": "Foley 1967 / Thomson 2023 Ch.8; canonical.",
            "internal_consistency": "Trivially consistent.",
            "empirical_grounding": "Strong: Foley 1967, Thomson 2023, Rawlsian philosophical tradition.",
            "actionability": "Test: for each pair (i, j), compute u_i(alloc_i) and u_i(alloc_j), check ≥."
        },
        "tier": "easy",
    },
    {
        "id": "AX-THOMSON-POPMON", "type": "axiom",
        "source": "kb/nodes/axioms/AX-THOMSON-POPMON.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Clear: when population shrinks, remaining agents shouldn't be hurt.",
            "novelty": "Thomson 2023; standard in mechanism design but a useful reframing.",
            "internal_consistency": "Sound; the S ⊂ S' clause is precise.",
            "empirical_grounding": "Cites Thomson 2023 Ch.4 only; no broader literature listed.",
            "actionability": "Testable: vary the population, recompute allocations, check remaining-agent utilities."
        },
        "tier": "medium",
    },
    {
        "id": "AX-THOMSON-STRPRO", "type": "axiom",
        "source": "kb/nodes/axioms/AX-THOMSON-STRPRO.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "Truth-telling is dominant strategy — universally familiar.",
            "novelty": "Gibbard-Satterthwaite 1973; canonical.",
            "internal_consistency": "Sound; classic.",
            "empirical_grounding": "Cites GS 1973 and Thomson 2023 Ch.10; rational_choice philosophical tradition.",
            "actionability": "Test: try deviating from truthful report for each agent; utility should not increase."
        },
        "tier": "easy",
    },
    # ---------- THEOREMS (10) ----------
    {
        "id": "TH-IMP-501", "type": "theorem",
        "source": "kb/nodes/theorems/TH-IMP-501.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 5},
        "justifications": {
            "clarity": "Long NL but each conjunct is well-defined; proof sketch clarifies.",
            "novelty": "Novel impossibility that combines SC with classic Shapley axioms.",
            "internal_consistency": "Counter-example is explicit and valid.",
            "empirical_grounding": "Proof is by construction; primary source is internal memo; Heskes 2020 cited as related.",
            "actionability": "The counter-example f(X)=βX_1, f̂=0 is directly reproducible."
        },
        "tier": "easy",
    },
    {
        "id": "TH-COR-501-1", "type": "theorem",
        "source": "kb/nodes/theorems/TH-COR-501-1.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 5},
        "justifications": {
            "clarity": "Single-sentence corollary; clear consequence of TH-IMP-501.",
            "novelty": "Specific application to TreeSHAP; useful but not surprising given TH-IMP-501.",
            "internal_consistency": "Sound; logical consequence of the parent theorem.",
            "empirical_grounding": "Source is internal AXIOM_SKELETON §5.3; Heskes 2021 'implicit' — weak citation.",
            "actionability": "Testable: run TreeSHAP on the f̂=0 setup and observe φ_1=0."
        },
        "tier": "medium",
    },
    {
        "id": "TH-COR-501-2", "type": "theorem",
        "source": "kb/nodes/theorems/TH-COR-501-2.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 5},
        "justifications": {
            "clarity": "Parallel structure to TH-COR-501-1; clear.",
            "novelty": "Same form, applied to KernelSHAP; not independent novelty.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Same internal source; weak external citation.",
            "actionability": "Testable on any KernelSHAP setup."
        },
        "tier": "medium",
    },
    {
        "id": "TH-COR-501-3", "type": "theorem",
        "source": "kb/nodes/theorems/TH-COR-501-3.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 5},
        "justifications": {
            "clarity": "Clear about what Information Shapley uses (v(S)=E[Y|X_S]-E[Y]).",
            "novelty": "Application to Information Shapley; follows the same pattern.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Internal memo; weak citation.",
            "actionability": "Testable."
        },
        "tier": "medium",
    },
    {
        "id": "TH-COR-501-4", "type": "theorem",
        "source": "kb/nodes/theorems/TH-COR-501-4.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Lists three methods that satisfy SC; readable.",
            "novelty": "Positive result; useful counterpoint to TH-IMP-501.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Internal memo; weak external.",
            "actionability": "Testable by implementing Structural Shapley and checking."
        },
        "tier": "medium",
    },
    {
        "id": "TH-PROP-621", "type": "theorem",
        "source": "kb/nodes/theorems/TH-PROP-621.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "States the precise case (f̂=f) clearly.",
            "novelty": "Useful proposition: SC alone is weak; novel observation about the relationship between SC and Dummy.",
            "internal_consistency": "Status='sketch' but logical structure is sound.",
            "empirical_grounding": "Status='sketch' is acknowledged weakness; only internal source.",
            "actionability": "Sketch-level proof; not directly runnable without expansion."
        },
        "tier": "hard",
    },
    {
        "id": "TH-PROP-622", "type": "theorem",
        "source": "kb/nodes/theorems/TH-PROP-622.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 4, "internal_consistency": 4, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Claim is that SC and Dummy are independent when f̂≠f — clear but requires familiarity.",
            "novelty": "A genuine insight about orthogonality of axioms targeting different objects.",
            "internal_consistency": "Status='argued' — slightly informal.",
            "empirical_grounding": "Internal source only.",
            "actionability": "Indirect: one would need to construct cases where SC holds but Dummy fails, and vice versa."
        },
        "tier": "hard",
    },
    {
        "id": "TH-PROP-623", "type": "theorem",
        "source": "kb/nodes/theorems/TH-PROP-623.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Scenario B is well-defined (f̂≠f, SI>0, ∂f̂=0).",
            "novelty": "Identifies the 'entry point' to the impossibility; pedagogically useful.",
            "internal_consistency": "Status='proved'; clear logical claim.",
            "empirical_grounding": "Internal source; no external citation.",
            "actionability": "Testable: instantiate Scenario B and verify the impossibility manifests."
        },
        "tier": "medium",
    },
    {
        "id": "TH-PROP-624", "type": "theorem",
        "source": "kb/nodes/theorems/TH-PROP-624.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 4, "internal_consistency": 4, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Claim that SC + Dummy = structural completeness; phrase 'one-to-one correspondence' is vague.",
            "novelty": "Useful synthetic claim.",
            "internal_consistency": "Status='argued'; conceptually sound.",
            "empirical_grounding": "Internal source only.",
            "actionability": "Indirect; would require constructing a general framework."
        },
        "tier": "hard",
    },
    {
        "id": "TH-SHAP-UNIQ", "type": "theorem",
        "source": "kb/nodes/theorems/TH-SHAP-UNIQ.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 1, "internal_consistency": 4, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Theorem statement is canonical and crystal-clear.",
            "novelty": "L17 Theorem 1; not new.",
            "internal_consistency": "process_meta flags circular reasoning ('additive already presupposes SHAP-like') — internal tension noted.",
            "empirical_grounding": "Cites L17 only; no alternative derivation.",
            "actionability": "Testable in any SHAP implementation."
        },
        "tier": "easy",
    },
    # ---------- DIKTATS (12 — pick best 6) ----------
    {
        "id": "DIKT-PROCACCIA-EXPLAIN-SOLUTIONS", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-PROCACCIA-EXPLAIN-SOLUTIONS.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "Crystal clear: 'axioms should explain solutions to users'.",
            "novelty": "The user-facing framing of axioms is a real methodological contribution.",
            "internal_consistency": "Stance is internally consistent and well-argued.",
            "empirical_grounding": "Cites Procaccia, the Spliddit deployment (124k users), and the AAAI 2013 origin story.",
            "actionability": "Concrete applicability field: write a 1-2 sentence user explanation."
        },
        "tier": "easy",
    },
    {
        "id": "DIKT-CAMEL-DUMMY-HARMFUL", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-CAMEL-DUMMY-HARMFUL.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Argument is clearly structured (First/Secondly) and the verdict pattern is concrete.",
            "novelty": "Reframes Dummy as harmful in some contexts — a non-trivial methodological point.",
            "internal_consistency": "Sound argument from premise to conclusion.",
            "empirical_grounding": "Source: Ch.25 of Future of Economic Design; camel-allegory origin story; well-anchored.",
            "actionability": "Two-channel test is concrete and runnable."
        },
        "tier": "medium",
    },
    {
        "id": "DIKT-BVL-PLANNER-EXPERT", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-BVL-PLANNER-EXPERT.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Engineer > pure mathematician (within economic design) — clean stance.",
            "novelty": "Reframes the role of the economist; useful.",
            "internal_consistency": "Sound; one might disagree with the value priority but it is internally consistent.",
            "empirical_grounding": "Cites Roth's deferred acceptance as concrete example.",
            "actionability": "The hospital-administrator litmus test is operational."
        },
        "tier": "easy",
    },
    {
        "id": "DIKT-TH10-CONTEXT", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH10-CONTEXT.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "No axiom is sacred — explicit rhetorical escalation via 'even'.",
            "novelty": "Strong methodological claim; well-known but worth restating.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Thomson Ch.10.1; well-anchored.",
            "actionability": "Context-question is concrete: 'why this axiom in this planner's problem?'."
        },
        "tier": "easy",
    },
    {
        "id": "DIKT-TH10-CONSUMER-REPORTS", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH10-CONSUMER-REPORTS.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Nuanced grading > yes/no — clear methodological preference.",
            "novelty": "Parameterization as a design principle; not new but articulated well.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Thomson Ch.10.1 §3.",
            "actionability": "Operational: replace binary with degree 0-1 + intermediate threshold."
        },
        "tier": "easy",
    },
    {
        "id": "DIKT-TH11-EXISTENCE-FIRST", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH11-EXISTENCE-FIRST.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Existence > uniqueness — inversion of academic priority, sharply stated.",
            "novelty": "Genuinely counter-cultural methodological point.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Cites Hurwicz 1972 as supporting example.",
            "actionability": "Reorder your result reporting: existence first, uniqueness second."
        },
        "tier": "medium",
    },
    # ---------- VALUE ANCHORS (33 — pick 8 high-quality) ----------
    {
        "id": "VA-MORAL-HELP-WEAK", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-MORAL-HELP-WEAK.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 2},
        "justifications": {
            "clarity": "Help the weak and disabled — universally understood.",
            "novelty": "Not new; cross-cultural moral consensus.",
            "internal_consistency": "Trivially consistent.",
            "empirical_grounding": "User-provided; high cross-cultural consistency claim but no specific citations.",
            "actionability": "Low — operationalizing 'help' requires context-specific interpretation."
        },
        "tier": "easy",
    },
    {
        "id": "VA-MORAL-NO-KILL", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-MORAL-NO-KILL.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 2},
        "justifications": {
            "clarity": "Cannot kill — unambiguous.",
            "novelty": "Universal prohibition across cultures; not new.",
            "internal_consistency": "Trivially consistent.",
            "empirical_grounding": "User-provided; high consistency claim.",
            "actionability": "Low; needs context (war, self-defense) to be testable."
        },
        "tier": "easy",
    },
    {
        "id": "VA-MORAL-HONESTY", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-MORAL-HONESTY.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 2},
        "justifications": {
            "clarity": "Honesty / 不欺骗 — clear.",
            "novelty": "Classical virtue; not new.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic 'moral consensus'; high cross-cultural claim.",
            "actionability": "Low — 'honest' is context-dependent (white lies, omissions)."
        },
        "tier": "easy",
    },
    {
        "id": "VA-MORAL-FAIRNESS", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-MORAL-FAIRNESS.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 2},
        "justifications": {
            "clarity": "Fairness / 公平不偏私 — clear, though 'fairness' has many operationalizations.",
            "novelty": "Classical; not new.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic moral consensus; high cross-cultural.",
            "actionability": "Low without domain context."
        },
        "tier": "medium",
    },
    {
        "id": "VA-PRACTICAL-REPRODUCIBLE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PRACTICAL-REPRODUCIBLE.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 5},
        "justifications": {
            "clarity": "Reproducibility / 可复现 — operationally clear in scientific contexts.",
            "novelty": "Classical ML/scientific value; not new.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic; high cross-cultural claim.",
            "actionability": "High — re-running the experiment is a direct test."
        },
        "tier": "easy",
    },
    {
        "id": "VA-PRACTICAL-TEACHABLE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PRACTICAL-TEACHABLE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Teachability — clear in intent but undefined (teachable to whom?).",
            "novelty": "Practical pedagogical value; useful framing.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic; no specific citation.",
            "actionability": "Medium — could measure student performance but requires setup."
        },
        "tier": "medium",
    },
    {
        "id": "VA-EPISTEMIC-TRUTH", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-EPISTEMIC-TRUTH.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Truth (empirical) / 对应现实 — clear as a stance.",
            "novelty": "Classical epistemic value; not new.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "Medium — falsificationist test exists."
        },
        "tier": "easy",
    },
    {
        "id": "VA-PHIL-RAWLS", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PHIL-RAWLS.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 2},
        "justifications": {
            "clarity": "Rawlsian justice / 罗尔斯正义论 — depends on familiarity with the tradition.",
            "novelty": "Classical philosophical position.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Implicit citation (Rawls 1971); cross-cultural consistency medium.",
            "actionability": "Low — needs a veil-of-ignorance setup to test."
        },
        "tier": "medium",
    },
    # ---------- LITERATURE (10 — pick 6) ----------
    {
        "id": "LIT-L17-SHAP", "type": "literature",
        "source": "kb/nodes/literature/LIT-L17-SHAP.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 5, "internal_consistency": 4, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "Well-known paper; clear contributions listed.",
            "novelty": "Original SHAP unification — landmark paper.",
            "internal_consistency": "process_meta flags a possible circularity in 'uniqueness' — internal tension noted.",
            "empirical_grounding": "1000+ citations; experimental applications (TreeSHAP, KernelSHAP).",
            "actionability": "Re-implementable; widely used in production."
        },
        "tier": "easy",
    },
    {
        "id": "LIT-H21-STRUCTURAL", "type": "literature",
        "source": "kb/nodes/literature/LIT-H21-STRUCTURAL.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Heskes 2021 book Ch.21; structural importance well-defined.",
            "novelty": "Pioneers the SI_i(f) framing; novel.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Book chapter; cited in axioms.",
            "actionability": "Testable; structural importance can be computed on causal models."
        },
        "tier": "medium",
    },
    {
        "id": "LIT-J19-CAUSAL", "type": "literature",
        "source": "kb/nodes/literature/LIT-J19-CAUSAL.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Causal attribution framing is precise.",
            "novelty": "Janzing 2019 — novel causal approach.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Established conference paper.",
            "actionability": "Testable on synthetic causal models."
        },
        "tier": "medium",
    },
    {
        "id": "LIT-THOMSON-2023", "type": "literature",
        "source": "kb/nodes/literature/LIT-THOMSON-2023.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 4},
        "justifications": {
            "clarity": "Comprehensive treatise; chapters organize axioms systematically.",
            "novelty": "Synthesizes a 50-year literature; high impact, low 'first-time' novelty.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Authoritative book; canonical reference.",
            "actionability": "Each chapter's axioms are testable in their respective domain."
        },
        "tier": "easy",
    },
    {
        "id": "LIT-LASLIER-2019", "type": "literature",
        "source": "kb/nodes/literature/LIT-LASLIER-2019.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 3},
        "justifications": {
            "clarity": "Specialized tournament/axiomatic work; not as accessible as L17.",
            "novelty": "Contributes tournament-axiom literature.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Less cited than L17 but established.",
            "actionability": "Testable in tournament settings."
        },
        "tier": "medium",
    },
    {
        "id": "LIT-STY17-ICML", "type": "literature",
        "source": "kb/nodes/literature/LIT-STY17-ICML.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 5, "internal_consistency": 4, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "STY17 axiomatic framing is canonical.",
            "novelty": "Introduces Sensitivity (a) and (b); novel.",
            "internal_consistency": "Sound in its own framework; tension with SC noted in process_meta of AX-SC-001.",
            "empirical_grounding": "ICML 2017, highly cited.",
            "actionability": "Testable; many SHAP variants compared in the paper."
        },
        "tier": "easy",
    },
    # ---------- SCENARIOS (6) ----------
    {
        "id": "SC-CAMEL-DUMMY", "type": "scenario",
        "source": "kb/nodes/scenarios/SC-CAMEL-DUMMY.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Three travelers, cost c(N); universally understood.",
            "novelty": "Classic Talmudic/camel allegory; widely known.",
            "internal_consistency": "Sound scenario.",
            "empirical_grounding": "Cross-cultural reference; Thomson cites repeatedly.",
            "actionability": "Testable: instantiate cost function and run Shapley."
        },
        "tier": "easy",
    },
    {
        "id": "SC-COURT-DIVORCE", "type": "scenario",
        "source": "kb/nodes/scenarios/SC-COURT-DIVORCE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Divorce asset allocation — clearly described.",
            "novelty": "Standard mechanism-design scenario; not novel.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Real-world setting with well-documented allocations.",
            "actionability": "Testable with hypothetical preferences."
        },
        "tier": "medium",
    },
    {
        "id": "SC-HOSPITAL-COSTSHARE", "type": "scenario",
        "source": "kb/nodes/scenarios/SC-HOSPITAL-COSTSHARE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Hospital cost-sharing — clear domain.",
            "novelty": "Real-world cost-sharing problem; not novel but relevant.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Real-world scenario with documented stakes.",
            "actionability": "Testable with realistic cost curves."
        },
        "tier": "medium",
    },
    {
        "id": "SC-ML-ATTR-SHAP", "type": "scenario",
        "source": "kb/nodes/scenarios/SC-ML-ATTR-SHAP.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "ML attribution with SHAP — well-defined.",
            "novelty": "Industrial scenario; widely deployed.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Heavily deployed in industry.",
            "actionability": "Directly testable with any ML model."
        },
        "tier": "easy",
    },
    {
        "id": "SC-ELECTION-VOTING", "type": "scenario",
        "source": "kb/nodes/scenarios/SC-ELECTION-VOTING.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 4},
        "justifications": {
            "clarity": "Voting/election — universally familiar.",
            "novelty": "Classical social choice problem.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Centuries of voting literature.",
            "actionability": "Testable with synthetic or real preference profiles."
        },
        "tier": "easy",
    },
    {
        "id": "SC-FAA-LANDING", "type": "scenario",
        "source": "kb/nodes/scenarios/SC-FAA-LANDING.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "FAA landing slot allocation — concrete domain.",
            "novelty": "Real-world allocation problem.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Documented real-world system.",
            "actionability": "Testable with airport slot data."
        },
        "tier": "medium",
    },
    # ---------- TRADEOFFS (4) ----------
    {
        "id": "TR-HURWICZ-1972", "type": "tradeoff",
        "source": "kb/nodes/tradeoffs/TR-HURWICZ-1972.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Informational efficiency vs IC — clear tradeoff.",
            "novelty": "Classical Hurwicz framing.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Hurwicz 1972 cited.",
            "actionability": "Testable on specific mechanisms (VCG, Groves)."
        },
        "tier": "medium",
    },
    {
        "id": "TR-EFFICIENCY-EQUITY", "type": "tradeoff",
        "source": "kb/nodes/tradeoffs/TR-EFFICIENCY-EQUITY.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 3},
        "justifications": {
            "clarity": "Efficiency vs equity — universally understood.",
            "novelty": "Classical tradeoff; not novel.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "No specific citation.",
            "actionability": "Testable on specific allocations."
        },
        "tier": "easy",
    },
    {
        "id": "TR-SIMPLICITY-FAITHFULNESS", "type": "tradeoff",
        "source": "kb/nodes/tradeoffs/TR-SIMPLICITY-FAITHFULNESS.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Simplicity vs faithfulness — clear but specific to ML/explanation.",
            "novelty": "Useful tradeoff in interpretability research.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "No specific citation in node.",
            "actionability": "Testable via approximation-error vs model-complexity curves."
        },
        "tier": "medium",
    },
    {
        "id": "TR-PREDICTIVE-STRUCTURAL", "type": "tradeoff",
        "source": "kb/nodes/tradeoffs/TR-PREDICTIVE-STRUCTURAL.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Predictive accuracy vs structural faithfulness — clearly stated.",
            "novelty": "Novel framing that motivates SC.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "No specific citation.",
            "actionability": "Testable on synthetic data where f and f̂ diverge."
        },
        "tier": "hard",
    },
    # ---------- ADDITIONAL VALUE ANCHORS (mixed quality — captures variance) ----------
    {
        "id": "VA-AESTHETIC-ELEGANCE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-AESTHETIC-ELEGANCE.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 2},
        "justifications": {
            "clarity": "Elegance — abstract aesthetic; depends on the field.",
            "novelty": "Classical aesthetic value.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Description is generic ('Examples of elegance in various contexts').",
            "actionability": "Low — subjective."
        },
        "tier": "medium",
    },
    {
        "id": "VA-INTEREST-POWER", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-INTEREST-POWER.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 2},
        "justifications": {
            "clarity": "Power distribution — political-science term; cross-cultural consistency 'low'.",
            "novelty": "Classical concept.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic evidence.",
            "actionability": "Low — depends on power metric."
        },
        "tier": "medium",
    },
    {
        "id": "VA-MORAL-CULTURAL", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-MORAL-CULTURAL.json",
        "is_distractor": False,
        "scores": {"clarity": 2, "novelty": 2, "internal_consistency": 4, "empirical_grounding": 2, "actionability": 2},
        "justifications": {
            "clarity": "Cultural conventions — vague; cross-cultural consistency 'low' makes this hard to pin down.",
            "novelty": "Classical concept.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "Low — depends on cultural context."
        },
        "tier": "hard",
    },
    {
        "id": "VA-PHIL-EXIST", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PHIL-EXIST.json",
        "is_distractor": False,
        "scores": {"clarity": 2, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 1},
        "justifications": {
            "clarity": "Existentialism — broad philosophical label rather than an axiom.",
            "novelty": "Classical.",
            "internal_consistency": "Sound as a value-class label.",
            "empirical_grounding": "Generic; 'interest_judgment' evidence is vague.",
            "actionability": "Very low — existentialism is not testable."
        },
        "tier": "hard",
    },
    {
        "id": "VA-PRACTICAL-SCALABLE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PRACTICAL-SCALABLE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 4},
        "justifications": {
            "clarity": "Scalability — operationally meaningful in CS contexts.",
            "novelty": "Classical software value.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "High — benchmark on large inputs."
        },
        "tier": "easy",
    },
    {
        "id": "VA-INTEREST-UTIL-SOC", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-INTEREST-UTIL-SOC.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Social welfare / 社会总福利 — clear aggregate.",
            "novelty": "Classical utilitarian concept.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "Medium — computable from individual utilities."
        },
        "tier": "medium",
    },
    {
        "id": "VA-EPISTEMIC-FALSIFIABLE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-EPISTEMIC-FALSIFIABLE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Falsifiability — Popperian; operationally meaningful.",
            "novelty": "Classical.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic; high cross-cultural consistency.",
            "actionability": "High — propose an experiment that could refute the claim."
        },
        "tier": "easy",
    },
    # ---------- ASSUMPTIONS (2 — both) ----------
    {
        "id": "AS-SHAP-CHARFN", "type": "assumption",
        "source": "kb/nodes/assumptions/AS-SHAP-CHARFN.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "v(S) = E[f̂(X) | X_S] — one line, one definition.",
            "novelty": "Standard SHAP assumption; not new.",
            "internal_consistency": "Trivially sound definition.",
            "empirical_grounding": "Cites L17 and SY19; widely used.",
            "actionability": "Directly implementable in any estimator."
        },
        "tier": "easy",
    },
    {
        "id": "AS-SHAP-DISTINCT", "type": "assumption",
        "source": "kb/nodes/assumptions/AS-SHAP-DISTINCT.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 3, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Features must be distinguishable — clear precondition.",
            "novelty": "Mildly novel as a standalone assumption.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Standard SHAP literature.",
            "actionability": "Testable: check feature naming."
        },
        "tier": "medium",
    },
    # ---------- ADDITIONAL DIKTATS (to capture more variety) ----------
    {
        "id": "DIKT-TH10-IMPARTIAL-CULTURE", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH10-IMPARTIAL-CULTURE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Confession that 'uniform' is itself a choice; clear.",
            "novelty": "Useful methodological reminder.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Thomson Ch.10.2.",
            "actionability": "Operational: report the assumed distribution with each numeric verdict."
        },
        "tier": "medium",
    },
    {
        "id": "DIKT-TH10-OPERATOR-UNINTENDED", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH10-OPERATOR-UNINTENDED.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 5},
        "justifications": {
            "clarity": "Operators may break axioms — sharp methodological claim.",
            "novelty": "Useful.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Thomson Ch.10.3.",
            "actionability": "Pair each operator with a property-preservation analysis."
        },
        "tier": "medium",
    },
    {
        "id": "DIKT-TH10-STEP-OUT-OF-BOX", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH10-STEP-OUT-OF-BOX.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 4},
        "justifications": {
            "clarity": "Hierarchical 'stepping out' framing is clear via enumeration.",
            "novelty": "Useful for institutional design.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Thomson Ch.10.1.",
            "actionability": "Testable: check whether the planner is embedded in a higher-level entity."
        },
        "tier": "medium",
    },
    {
        "id": "DIKT-TH10-USER-VS-ECONOMIST", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH10-USER-VS-ECONOMIST.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "Economist maps, user chooses — sharp role separation.",
            "novelty": "Counter to academic norms.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Cites the cumulative list of users; Thomson Ch.10.1.",
            "actionability": "Operational: every new axiom must be anchored to a specific planner."
        },
        "tier": "easy",
    },
    {
        "id": "DIKT-TH11-EXCITEMENT-UNIQUE", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH11-EXCITEMENT-UNIQUE.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Sharp self-aware observation about academic aesthetic.",
            "novelty": "Counter-cultural methodological point.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Thomson Ch.11.5.",
            "actionability": "Downgrade aesthetic-only uniqueness claims."
        },
        "tier": "medium",
    },
    {
        "id": "DIKT-TH11-IF-AND-ONLY-IF", "type": "diktat",
        "source": "kb/nodes/diktats/DIKT-TH11-IF-AND-ONLY-IF.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "Sharp critique of iff-theorems as packaging.",
            "novelty": "Methodologically important.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Cites TTC counter-example; Thomson Ch.11.5.",
            "actionability": "Operational: report weakest-list-for-uniqueness and strongest-list-for-satisfaction separately."
        },
        "tier": "medium",
    },
    # ---------- MORE VALUE ANCHORS ----------
    {
        "id": "VA-EPISTEMIC-INTERPRETABLE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-EPISTEMIC-INTERPRETABLE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Interpretability — operationally meaningful in ML.",
            "novelty": "Classical ML value.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "Medium — proxy measures exist (e.g., feature importance stability)."
        },
        "tier": "medium",
    },
    {
        "id": "VA-PRACTICAL-EFFICIENCY", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PRACTICAL-EFFICIENCY.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 4},
        "justifications": {
            "clarity": "Efficiency — operationally meaningful.",
            "novelty": "Classical.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "High — measurable as runtime/memory."
        },
        "tier": "easy",
    },
    {
        "id": "VA-MORAL-AUTONOMY", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-MORAL-AUTONOMY.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 3, "actionability": 2},
        "justifications": {
            "clarity": "Respect autonomy — clear moral concept.",
            "novelty": "Classical.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic; medium cross-cultural consistency.",
            "actionability": "Low — operationalization is contested."
        },
        "tier": "medium",
    },
    {
        "id": "VA-PHIL-KANT", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-PHIL-KANT.json",
        "is_distractor": False,
        "scores": {"clarity": 3, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 2},
        "justifications": {
            "clarity": "Kantian ethics — requires philosophical background.",
            "novelty": "Classical.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Kant is canonical; implicit citation.",
            "actionability": "Low — categorical imperative tests are subtle."
        },
        "tier": "medium",
    },
    {
        "id": "VA-INTEREST-LONGTERM", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-INTEREST-LONGTERM.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Long-term interest — clear temporal scope.",
            "novelty": "Classical.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "Medium — discount-rate sensitivity can be measured."
        },
        "tier": "medium",
    },
    {
        "id": "VA-AESTHETIC-SIMPLE", "type": "value_anchor",
        "source": "kb/nodes/value_anchors/VA-AESTHETIC-SIMPLE.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 2, "internal_consistency": 5, "empirical_grounding": 2, "actionability": 3},
        "justifications": {
            "clarity": "Simplicity — operationally meaningful (Occam).",
            "novelty": "Classical.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Generic.",
            "actionability": "Medium — model-complexity metrics exist."
        },
        "tier": "easy",
    },
    # ---------- MORE LITERATURE ----------
    {
        "id": "LIT-C21-EXPLAINING-BY-REMOVING", "type": "literature",
        "source": "kb/nodes/literature/LIT-C21-EXPLAINING-BY-REMOVING.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Removal-based explanations are precise.",
            "novelty": "Novel framing in interpretability.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Established paper.",
            "actionability": "Testable on any black-box model."
        },
        "tier": "medium",
    },
    {
        "id": "LIT-H20-CAUSAL-SHAP", "type": "literature",
        "source": "kb/nodes/literature/LIT-H20-CAUSAL-SHAP.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 5, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Causal Shapley framing is clear.",
            "novelty": "Novel.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Heskes 2020; established.",
            "actionability": "Testable with causal graphs."
        },
        "tier": "medium",
    },
    {
        "id": "LIT-K20-PROBLEMS", "type": "literature",
        "source": "kb/nodes/literature/LIT-K20-PROBLEMS.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Identifies problems with SHAP clearly.",
            "novelty": "Useful synthesis.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Kumar 2020; established.",
            "actionability": "Testable on standard benchmarks."
        },
        "tier": "medium",
    },
    {
        "id": "LIT-L17-SHAP", "type": "literature",
        "source": "kb/nodes/literature/LIT-L17-SHAP.json",
        "is_distractor": False,
        "scores": {"clarity": 5, "novelty": 5, "internal_consistency": 4, "empirical_grounding": 5, "actionability": 5},
        "justifications": {
            "clarity": "Canonical; very clear.",
            "novelty": "Landmark paper.",
            "internal_consistency": "process_meta flags internal circularity; slightly downgraded.",
            "empirical_grounding": "1000+ citations.",
            "actionability": "Re-implementable."
        },
        "tier": "easy",
    },
    {
        "id": "LIT-SY19-MANY", "type": "literature",
        "source": "kb/nodes/literature/LIT-SY19-MANY.json",
        "is_distractor": False,
        "scores": {"clarity": 4, "novelty": 4, "internal_consistency": 5, "empirical_grounding": 4, "actionability": 4},
        "justifications": {
            "clarity": "Comparative axiomatic analysis.",
            "novelty": "Useful comparative work.",
            "internal_consistency": "Sound.",
            "empirical_grounding": "Established.",
            "actionability": "Testable."
        },
        "tier": "medium",
    },
]


# =============================================================================
# Distractors — load from the JSON we wrote earlier, but adapt to items format
# =============================================================================

def load_distractors():
    p = Path("/Users/alan/Downloads/axiom-finder/paper/data/distractors.json")
    with p.open() as f:
        data = json.load(f)
    items = []
    for d in data["distractors"]:
        items.append({
            "id": d["id"],
            "type": "distractor",
            "source": "paper/data/distractors.json",
            "is_distractor": True,
            "scores": d["scores"],
            "justifications": {
                "clarity": f"{d['failure_mode']}: {d['justification'][:80]}",
                "novelty": "Distractor: no new claim.",
                "internal_consistency": f"Distractor failure mode: {d['failure_mode']}.",
                "empirical_grounding": "No source chain by design.",
                "actionability": f"Distractor failure mode: {d['failure_mode']}.",
            },
            "overall": d["overall"],
            "tier": d["tier"],
            "nl": d["nl"],
            "failure_mode": d["failure_mode"],
        })
    return items


# =============================================================================
# Compose gold.json
# =============================================================================

def main():
    distractors = load_distractors()
    items = list(REAL_ITEMS) + distractors

    # Add overall & id-derivation
    for it in items:
        sc = it["scores"]
        it["overall"] = round(sum(sc.values()) / 5.0, 2)

    gold = {
        "rubric_version": "1.0",
        "created": "2026-06-23",
        "n_real": len(REAL_ITEMS),
        "n_distractor": len(distractors),
        "items": items,
    }

    out = Path("/Users/alan/Downloads/axiom-finder/paper/data/gold.json")
    out.write_text(json.dumps(gold, indent=2, ensure_ascii=False))
    print(f"Wrote {out} with {len(items)} items ({len(REAL_ITEMS)} real + {len(distractors)} distractor).")


if __name__ == "__main__":
    main()