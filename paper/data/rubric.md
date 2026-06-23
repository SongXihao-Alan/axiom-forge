# Axiom Evaluation Rubric (v1.0)

This rubric is used by human annotators (and serves as ground truth for LLM calibration studies)
to score social-science / feature-attribution **axioms** on five independent dimensions.
Each dimension is rated on an integer scale 1–5 (1 = worst, 5 = best).
Dimensions are deliberately independent — an axiom can be high on one and low on another.

The reference set comes from `kb/nodes/`, comprising 8 axiom, 10 theorem, 33 value_anchor,
10 literature, 12 diktat, 6 scenario, and 4 tradeoff nodes.

---

## 1. Clarity (Is the NL statement unambiguous?)

**Instructions.** Read the natural-language statement once. Could a domain expert (a Shapley-value
researcher, a mechanism-design economist, a moral philosopher) tell, after a single read, what
the axiom asserts and what it forbids? Score 5 if the statement can be parsed and operationalized
without further clarification. Score 1 if the statement is a vague gesture ("be fair in a meaningful
way") or requires substantial interpretation. Penalize mixed quantifier scope, undefined symbols,
or hidden domain assumptions. A formal restatement is a plus but does not compensate for a vague
NL.

**Anchor scale.**
- 5 = Single read yields the assertion; any domain expert can paraphrase it correctly.
- 4 = Minor notational ambiguity, but the claim is clear.
- 3 = Requires careful reading; the claim is identifiable but borders on hand-wavy.
- 2 = Substantial ambiguity; two experts might disagree on what is being asserted.
- 1 = Vague gesture or circular definition.

---

## 2. Novelty (Is this a new claim?)

**Instructions.** Is the axiom a novel contribution to the literature, or a restatement of
something already established? An axiom attributed to a canonical source (Shapley 1953,
Lundberg & Lee 2017, Thomson 2023) that is faithful to the original is **low novelty by design**,
not by failure — it does its job precisely because it is canonical. A *new* axiom that contributes
a previously-unarticulated property scores high. A *new* axiom that turns out to be a known
property in disguise scores low. Score 1 for genuinely tautological or self-referential statements.

**Anchor scale.**
- 5 = Genuinely new claim with no direct precedent.
- 4 = New claim, but a closely related precedent exists.
- 3 = New framing of a known result, useful in the present context.
- 2 = Mostly a restatement of a known axiom with minor reframing.
- 1 = Pure restatement, tautology, or known without citation.

---

## 3. Internal Consistency (Premises & conclusion agree?)

**Instructions.** Inspect the formal statement (and NL) for self-contradiction, scope errors,
type mismatches, or vacuous content. Does the conclusion follow logically from the premises, or
does the axiom assert something it cannot in principle deliver? Score 5 if the axiom is logically
tight. Score 1 if it asserts both p and ¬p, or makes a claim that violates its own scope. The
self-contradiction must be visible from the statement alone (not from how it interacts with
other axioms).

**Anchor scale.**
- 5 = Tautologically and structurally sound.
- 4 = Sound; minor notational or scope pedantry possible.
- 3 = Sound in the intended reading but slightly loose.
- 2 = Internal tension; experts would flag it.
- 1 = Self-contradictory, circular, or vacuous.

---

## 4. Empirical Grounding (Is there traceable evidence?)

**Instructions.** Examine the `source` and `anchors` fields of the node. Is there at least one
citable source, an empirical study, a known authority, or a verifiable origin story? Are the
`anchors` populated and informative? Is the `source.primary` non-empty? Is there a chain of
evidence the reader can follow? Axioms that cite *verified* papers / books / chapters / page
numbers score higher than axioms whose only evidence is a one-line author mention. Axioms whose
source is empty, generic ("compiled from X"), or self-referential ("this is true because it's
important") score low.

**Anchor scale.**
- 5 = Concrete citation(s) with page/line, plus populated anchors.
- 4 = Clear primary source; anchors populated; some detail missing.
- 3 = Source exists but is partially generic; anchors thin.
- 2 = Source is vague or only an internal memo; anchors minimal.
- 1 = No source, no anchors, no traceable evidence chain.

---

## 5. Actionability (Can you write a test case?)

**Instructions.** Given the axiom, could a competent engineer write a unit test, simulation, or
empirical check that determines whether a candidate rule / mechanism / attribution method
satisfies it? An axiom is *actionable* if its satisfaction is decidable on a concrete input
(in an allocation, an attribution problem, a vote, an auction). An axiom whose satisfaction
requires a subjective judgment ("fair", "good", "reasonable") is *less* actionable. An axiom
in pure philosophy may be un-actionable by design; this should be reflected in its score.

**Anchor scale.**
- 5 = A test function can be written in <1 day, with clear pass/fail.
- 4 = Testable; some interpretation needed to set thresholds.
- 3 = Conceptually testable but the test would be expensive or indirect.
- 2 = Borderline; would require a subjective rater or unclear setup.
- 1 = Not testable; assertion is purely philosophical or rhetorical.

---

## Tier assignment (used to stratify evaluation)

After scoring, each item receives a **tier**:

- **easy** — score spread across dims is high (≥1 point between best and worst dim); the distractor
  (if any) is obviously bad on at least two dims; an LLM evaluator should get this within ±1 of the
  gold standard on every dim.
- **medium** — some dims are subtle (the evaluator must read carefully); typical real axiom.
- **hard** — debatable even for a human expert; trade-off between two dims; or the distractor is
  subtle enough that a careless evaluator might approve it.

Target distribution: ~30% easy / 50% medium / 20% hard.
Distractor proportion in the final pool: ~20%.

---

## Notes on using this rubric

1. **Edge cases for `status: draft` or `status: seed`:** these nodes are intentionally weaker;
   score honestly lower. The benchmark is supposed to vary.
2. **Anchors vs. citations:** both count for empirical grounding; a node with strong anchors but
   no page numbers is fine, but a node with only page numbers and no anchors is suspicious.
3. **Internal consistency is purely local:** do not penalize an axiom for contradicting another
   axiom unless the contradiction is visible from the statement alone.
4. **Actionability is domain-sensitive:** a value_anchor (e.g., "Help the weak") is not directly
   testable — score honestly around 2. An allocation axiom like Strategy-Proofness is highly
   testable — score around 5.
5. **Calibration target:** if a real axiom averages ~4.0 across dims, and a distractor averages
   ~2.0, the rubric is doing its job. If the averages collapse to ~3.0 for both, the rubric is
   too lenient.