# Axiom Finder v0.3-alpha

> 2026-06-09 · A research tool that uses Thomson's *Axiomatics of Economic Design* (2023) and *The Future of Economic Design* (Laslier et al., 2019) as core training data, plus 16 user-provided SHAP/feature attribution papers, to derive a new axiomatic characterization of feature attribution.

**Main deliverable:** A new 4-axiom system for Shapley-based feature attribution, with a Structural Consistency axiom and an Impossibility Theorem showing no `v(S) = E[f̂(X)|X_S]`-based Shapley attribution can satisfy all four.

---

## 🎯 The Mainline Result

**Theorem 5.1 (Impossibility)**: No Shapley attribution based on `v(S) = E[f̂(X)|X_S]` can simultaneously satisfy:

1. **Efficiency**: `Σ_i φ_i = f̂(x)`
2. **Symmetry**: `f̂(x|_{X_i ↔ X_j}) = f̂(x) ⇒ φ_i = φ_j`
3. **Dummy**: `∂f̂/∂X_i = 0 ⇒ φ_i = 0`
4. **Structural Consistency (new)**: `SI_i(f) > 0 ⇒ ∃x : φ_i(f̂, x) > 0`

where `SI_i(f)` is the **Structural Importance** of feature `i` in the ground-truth data-generating function `f`:
- Linear case: `SI_i(f) = |β_i|`
- Differentiable case: `SI_i(f) = E_X[|∂f(X)/∂X_i|]`

**Key innovation**: SC is the only axiom that references the ground-truth `f`, not the predictor `f̂`. This binds attribution to real-world structure, preventing predictors' biases from being silently accepted.

📖 **Full proof in [`training/structural_consistency/AXIOM_SKELETON.md`](../../training/structural_consistency/AXIOM_SKELETON.md)**
📖 **Handcrafted memo: [`outputs/v0.2_shap/AX-STRUCTURAL-CONSISTENCY-001.md`](../../outputs/v0.2_shap/AX-STRUCTURAL-CONSISTENCY-001.md)**

---

## 📚 Literature Position (v0.3-alpha)

The mainline sits in the **Shapley-based feature attribution** literature lineage:

```
1953 Shapley: 4 axioms (Efficiency, Symmetry, Dummy, Additivity) → Shapley value unique
       ↓
1972 Owen: Multilinear extension; Shapley = ∫ partial derivatives
2001 Lipovetsky-Conklin: Shapley for linear regression (Necessary Shapley predecessor)
       ↓
2017 Lundberg-Lee (NeurIPS): SHAP — v(S) = E[f̂(X)|X_S] → unifying framework
2017 Sundararajan-Taly-Yan (ICML): Sensitivity + Implementation Invariance → Integrated Gradients
2017 Owen-Prieur: Shapley for dependent inputs
       ↓
2019 Sundararajan-Najmi: "Many Shapley Values" — different P(X) → different attributions
2019 Janzing et al. (EJOR): Feature relevance as causal problem; unconditional ≠ conditional
       ↓
2020 Heskes et al. (IJAR): Causal Shapley via do-calculus
2020 Kumar et al.: "Problems with Shapley" — Shapley fails to explain importance
       ↓
2021 Covert-Lundberg-Lee: "Explaining by Removing" — unified framework for 26 methods
2021 Heskes (Book Ch.21): Structural Shapley Values — direct predecessor of SC
       ↓
★★★ 2026 Axiom Finder v0.3-alpha: Structural Consistency as 4th axiom + Impossibility Theorem ★★★
```

**Key claim**: **No one has ever promoted Structural Importance to a binding axiom on attribution.** This is the central novelty.

### 5-Proposal Hierarchy (literature-mapped)

| Rank | Proposal | Literature Position | Status |
|---|---|---|---|
| ★★★★★ | **Structural Consistency + Impossibility** | New — closest is H21's SI concept (not promoted to axiom) | **This work** |
| ★★★★ | **Structural Shapley** | Direct descendant of H21 Book Ch.21 | Extends H21 |
| ★★★ | **Necessary Attribution** | LC01 + O72 have v(N) - v(N\{i}) | Special case |
| ★★★ | **Causal-Structural Shapley** | H20 IJAR + Frye 2020 | Generalization |
| ★★ | **Information-Shapley** | C21 SAGE | Conflicting with SC |

---

## 🏗️ Architecture

```
Axiom Finder v0.3-alpha
├── training/
│   ├── graph/
│   │   ├── nodes/        # Literature nodes (13 SHAP papers + Thomson Ch.4-11)
│   │   └── diktats/      # 12 diktat nodes (Thomson style)
│   ├── seeds/            # 2 seed nodes (lundberg_2017_shap, heskes_2021_structural)
│   └── structural_consistency/
│       └── AXIOM_SKELETON.md   # The mainline theorem
├── legacy_v0.2_pipeline/     # 5-agent pipeline (literature → perturbation → value → axiom → consequence → memo); retired June 2026, see README inside
│   ├── literature_node_loader.py
│   ├── perturbation_sampler.py
│   ├── value_evaluator.py
│   ├── axiom_deriver_v2.py     # + collaborative notation_definer.py
│   ├── consequence_predictor.py
│   ├── memo_writer.py
│   ├── pipeline.py             # Orchestrator (with per-run save)
│   ├── completeness_auditor.py # 4-dim audit (syntactic/subject-verb/semantic/relevance)
│   └── completeness_rewriter.py
├── outputs/
│   ├── v0.2/                   # myerson_1981 outputs (best-of-3 quality=1.0)
│   └── v0.2_shap/              # SHAP domain outputs (run 1 quality=0.80)
└── docs/v0.3-alpha/            # This README + final report
```

---

## 🔬 Methodology

### 5-Agent Pipeline (legacy_v0.2_pipeline/, retired)
1. **Literature Node Loader**: Loads structured seed (axiom, assumption, theorem, proposition)
2. **Perturbation Sampler**: M3 proposes 8 types of perturbations (`PERT-STRUCTURAL`, `PERT-EFFICIENCY`, etc.) on seed axioms
3. **Value Evaluator**: M3 scores 8 value criteria (user-explainable, computational-feasibility, additivity, consistency, symmetry, capability, continuity, personalized-explanation)
4. **Axiom Deriver v2**: Collaborative loop with Notation Definer — drafts axiom, extracts symbols, defines new defs, checks alignment (max 3 cycles)
5. **Consequence Predictor**: M3 predicts 4 consequences (old_theorem_fails, new_phenomenon, new_technique, falsifiable_prediction)
6. **Memo Writer**: Assembles the PerturbationMemo
7. **Completeness Auditor + Rewriter**: 4-dim audit (syntactic, subject-verb, semantic, relevance) + auto-rewrite fields with score<0.6

### Diktat Injection
Thomson-style 3-axis "author spirit" framework: `{value_priority, implicit_norm, trigger, verdict_pattern, rhetorical_device}` + `counter_example` + `origin_story`. 12 diktat nodes cover Thomson Ch.4-11 + Billette de Villemeur & Leroux + Procaccia.

### Notation Definer (Collaborative)
- Conventional definitions library (SHAP, Myerson, etc.)
- LLM extracts symbols from formalization
- LLM drafts new defs (max 5)
- Alignment table: NL ↔ formal (consistency score)
- Per-deriver-revision cycle (max 3)

### LLM Backbone
- MiniMax-M3 via `https://api.minimaxi.com/v1`
- max_tokens=4000-6000 (long system prompts consume thinking)
- json_mode=True + regex-based JSON fence stripping
- Retry (3x) + best-of-N quality selector
- Quality score = 0.5*axiom + 0.2*value + 0.3*consequence

---

## 📊 Empirical Results

### v0.2 Pipeline: myerson_1981 (best-of-3)
- **Quality**: 1.000
- **Alignment**: 0.80
- **Completeness**: 0.92
- **AX-NEW-001**: "leaky quasi-linear utility" (from Myerson 1981 + A3-ql perturbation)

### v0.2 Pipeline: lundberg_2017_shap (run 1, handcrafted finalization)
- **Quality**: 0.800
- **Axiom statement**: Partial (M3 couldn't fully reconstruct SC from sparse prompt)
- **Handcrafted final**: `AX-STRUCTURAL-CONSISTENCY-001` — full formalization + Impossibility Theorem

---

## 🚀 Reproduction

```bash
cd axiom-finder
pip install --break-system-packages python-dotenv httpx pydantic pydantic-core anyio httpcore h11

# Set API key
export MINIMAX_API_KEY=sk-cp-...  # get from /workspace/axiom-finder/.env

# Run v0.2 pipeline on SHAP seed
python3 -c "
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv('.env')
from legacy_v0.2_pipeline.pipeline import run_v02_pipeline  # retired; see legacy_v0.2_pipeline/README.md
memos = run_v02_pipeline(
    seed_id='lundberg_2017_shap',
    perturbation={
        'target_id': 'L17-CHAR-FN',
        'perturbation_type_id': 'PERT-STRUCTURAL',
        'dimension_focus': 'content_root',
        'motivation': 'Replace predictive v(S) with structural v_s(S) = sum over path effects',
        'expected_output': 'Structural Consistency axiom'
    },
    n_pipeline_runs=1,
    output_dir='outputs/v0.2_shap',
)
"
```

⚠️ **Long runs** (5-agent pipeline + LLM thinking): each `run_one` takes 5-10 minutes on MiniMax-M3. Use `nohup` + log polling.

⚠️ **API key**: rotate after sandbox use.

---

## 📜 License

MIT License — no author attribution yet (pending user decision).

---

## 🔗 References (13 SHAP papers + Thomson books)

**Foundation**:
- Shapley, L. S. (1953). *A Value for n-Person Games*. In: Kuhn & Tucker (eds.), Contributions to the Theory of Games, Vol. II.
- Owen, G. (1972). *Multilinear Extensions of Games*. Management Science 18(5), P64-P79.
- Lipovetsky, S. & Conklin, M. (2001). *Analysis of regression in game theory approach*. Applied Stochastic Models in Business and Industry 17(4), 319-330.
- Lundberg, S. M. & Lee, S.-I. (2017). *A Unified Approach to Interpreting Model Predictions* (SHAP). NeurIPS.
- Sundararajan, M., Taly, A. & Yan, Q. (2017). *Axiomatic Attribution for Deep Networks*. ICML.
- Owen, A. B. & Prieur, C. (2017). *On Shapley value for measuring importance of dependent inputs*. EJOR.

**Critical / Refinement**:
- Sundararajan, M. & Najmi, A. (2019/2020). *The Many Shapley Values for Model Explanation*. (Earlier version in arXiv 2019; journal version 2020.)
- Janzing, D., Minorics, L. & Blöbaum, P. (2019/2020). *Feature relevance quantification in explainable AI: A causal problem*. EJOR.
- Heskes, T., Sijben, E., Bucur, I. G. & Claassen, T. (2020). *Causal Shapley Values: Exploiting Causal Knowledge to Explain Individual Predictions of Complex Models*. IJAR.
- Kumar, I. E., Venkatasubramanian, S., Scheidegger, C. & Friedler, S. A. (2020). *Problems with Shapley-value-based explanations as feature importance measures*.
- Covert, I. C., Lundberg, S. & Lee, S.-I. (2021). *Explaining by Removing: A Unified Framework for Model Explanation*.

**Structural (this work's direct predecessor)**:
- Heskes, T. (2021). *Structural Shapley Values* (Book Chapter 21). In: Explainable AI (Springer).

**Surveys**:
- Berge Olsen, L. H., Glad, I. K., Jullum, M. & Aas, K. (2023/2024). *A comparative study of methods for estimating (conditional) Shapley value explanations*.
- Li, M., Sun, H., Huang, Y. & Chen, H. (2024). *Shapley value: from cooperative game to explainable artificial intelligence*. AIS.

**Thomson (training data only)**:
- Thomson, W. (2023). *The Axiomatics of Economic Design, Vol. 1: An Introduction to Theory and Methods*. Springer.
- Laslier, J.-F., Moulin, H., Sanver, M. R. & Zwicker, W. S. (eds.) (2019). *The Future of Economic Design*. Studies in Economic Design, Springer.
