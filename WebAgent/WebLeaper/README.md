# WebLeaper: Empowering Efficient, Info-Rich Seeking for Web Agents

<p align="center"\>
<img src="./assets/webleaper.jpg" alt="logo" width="55%"/\>
</p\>

💡 Introduction

  * **WebLeaper** is a data+training framework that makes web agents both effective and efficient at information seeking (IS).
  * **Key Idea:** Today’s IS agents waste many steps because training tasks contain sparse targets, so agents learn shallow, meandering search. WebLeaper fixes this with **entity-intensive tasks** and **efficiency-aware training**.
  * We cast IS as tree-structured reasoning and synthesize three data variants—**`Basic`**, **`Union`**, and **`Reverse-Union`**—to progressively increase entity density, cross-source reasoning, and anti-shortcut robustness.
  * We curate training data in two stages:
    1.  **SFT:** We filter trajectories with **Information-Seeking Rate (ISR)** for coverage and **Information-Seeking Efficiency (ISE)** for action economy, keeping only those that are accurate and fast.
    2.  **RL:** We introduce a **Hybrid Reward System** that provides a dense, granular signal for our entity-intensive tasks, optimizing the agent further with policy optimization.
  * Extensive experiments on **BrowseComp, GAIA, Seal-0, WideSearch, and xbench-DeepSearch** show consistent gains over strong open and proprietary baselines.

-----

🚀 Highlights

  * **Entity-Intensive Tasks:** Pack many targets into compact contexts to teach efficient retrieval.
  * **Three Synthesis Modes:**
      * **`Basic`:** Single-table, high-density tasks.
      * **`Union`:** Multi-source, structure-aligned fusion for realistic synthesis.
      * **`Reverse-Union`:** “Fuzzed” anchors that force deduction before cross-source search—no keyword shortcuts.
  * **Efficiency-Aware SFT Curation:** Keep only SFT trajectories with high ISR and high ISE.
  * **Hybrid-Reward RL:** A novel, soft F-score-based reward ($\mathcal{R}_{WebLeaper}$) for entity-intensive tasks and **Group Relative Policy Optimization (GRPO)** to further boost performance.
  * **Strong Open-Source Results:** Strong improvements across 5 IS benchmarks with fewer actions per success.

<p align="center"\>
<img src="./assets/overview.png" alt="overview" width="90%"/\>
</p\>

-----

📦 Dataset & Task Design

WebLeaper constructs IS tasks from curated Wikipedia tables and cross-table unions:

  * **Tree-Structured IS:**
      * Root (question entity) $\rightarrow$ 2nd layer (key entities) $\rightarrow$ 3rd layer (attributes/linked entities)
      * Each 2nd-layer node + its attributes forms a subtree; tasks require retrieving final and intermediate entities.
  * **Variants**
    1.  **`Basic`:** Build a single-source tree from one well-formed table; dense targets in a constrained context.
    2.  **`Union`:** Detect maximal unions among trees that share relations (modeled as maximal biclique enumeration) to create multi-source synthesis questions.
    3.  **`Reverse-Union`:** Provide attribute-level clues to deduce a hidden anchor entity first, then pivot (e.g., nationality) to launch a union-style search.

> **Result:** Tasks that reward efficient exploration, resist keyword shortcuts, and stabilize metric estimation as the target count ($n$) grows.

-----

📐 Metrics: Measuring Coverage & Efficiency

  * **Information-Seeking Rate (ISR):** Fraction of required entities retrieved.
    $$
    \mathrm{ISR} = \frac{|R\cap O|}{|R|}
    $$
  * **Information-Seeking Efficiency (ISE):** Target entities discovered per action step.
    $$
    \mathrm{ISE} = \frac{n}{T}
    $$
  * **Stability:** As the number of targets $n$ increases, $\mathrm{Var}(\mathrm{ISE}) = \mathcal{O}(1/n)$, yielding reliable efficiency signals during training.

-----

🛠️ SFT Trajectory Construction

We generate trajectories with a tool-using agent (within ReAct) and keep only those that meet strict SFT criteria:

  * **Coverage:** $\mathrm{ISR} > \alpha$
  * **Efficiency:** $\mathrm{ISE} > \beta$

**Tools**

  * `Search(queries, filter_year)` $\rightarrow$ web results + snippets
  * `Visit(urls, goal)` $\rightarrow$ summarized paragraphs, from which entities are extracted

> **Note on ISE:** We compute ISE primarily using entities from `Visit` actions. Entities found in `Search` snippets are often less precise and are refined by a subsequent `Visit`, making `Visit` a better proxy for meaningful information gain.

-----

⚡ Reinforcement Learning with Hybrid Rewards

To further enhance the agent after Supervised Fine-Tuning (SFT), we apply a Reinforcement Learning (RL) stage.

  * **The Challenge:** Standard binary (success/fail) rewards are **too sparse** for our entity-intensive tasks (where dozens of entities are required). Simple automated metrics (F1, EM) are too brittle, and LLM-as-a-judge is too slow and unreliable for many entities.

  * **Our Solution: A Hybrid Reward System**

    1.  **For WebLeaper Tasks ($\mathcal{R}_{WebLeaper}$):** We use a granular, **soft F-score reward**. This reward measures semantic similarity (not just exact match) for each entity, handling variations like "USA" vs. "United States". It computes a soft precision ($P$) and soft recall ($R_c$) over the set of retrieved entities ($O$) and ground-truth entities ($R$).
        $$
        \mathcal{R}_{WebLeaper} = (1 + \omega^2) \frac{P \cdot R_c}{\omega^2 P + R_c}
        $$
    2.  **For Legacy Tasks ($\mathcal{R}_{\text{legacy}}$):** We use the original reward functions from other benchmark data (e.g., binary success).

  * **Optimization:** The agent's policy is optimized using **Group Relative Policy Optimization (GRPO)**. GRPO samples a group of trajectories, estimates the advantage for each one relative to the group's average reward, and updates the policy using a PPO-like objective. This provides a stable and effective learning signal from our hybrid reward.

-----

📊 Performance

<p align="center"\>
<img src="./assets/performance_summary.png" alt="perf" width="92%"/\>
</p\>

  * On BrowseComp, GAIA, Seal-0, WideSearch, and xbench-DeepSearch, WebLeaper (trained with SFT + RL) delivers consistent gains over competitive baselines.
  * The `Reverse-Union` data variant provides the strongest performance, highlighting the value of forcing deductive reasoning.
  * Against larger agents, WebLeaper’s training design yields a superior efficiency–effectiveness trade-off, achieving higher scores with fewer actions.
  * Ablation studies (Table 2 in the paper) show that `Union` and `Reverse-Union` data significantly outperform `Basic` data and standard deep-search data, confirming our task design's effectiveness.

<br>

**SFT vs. RL Performance**

Applying our Hybrid Reward system and GRPO optimization consistently improves performance over the SFT-only baseline across all benchmarks. The RL stage effectively refines the agent's policy, leading to significant gains, especially in complex tasks like GAIA and WideSearch (as shown on the comprehensive training setting).

| Model | BrowseComp | GAIA | xbench-DS | WideSearch (SR) | WideSearch (Row F1) | WideSearch (Item F1) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `SFT` | 37.80 | 69.9 | 69.0 | 1.5 | 23.0 | 45.4 |
| `SFT+RL`| **38.8** (+1.0) | **73.2** (+3.3) | **72.0** (+3.0) | **4.0** (+2.5) | **31.0** (+8.0) | **48.8** (+3.4) |

-----

🔍 Method Details

1.  **`Basic` (Single-Source, Dense)**

      * Mine large, homogeneous Wikipedia tables.
      * Root from table title; primary key columns $\rightarrow$ 2nd-layer; other columns $\rightarrow$ 3rd-layer attributes.
      * Build compact, high-coverage tasks that maximize valid actions.

2.  **`Union` (Multi-Source, Structured)**

      * Identify maximal unions between trees sharing relation sets (e.g., `has_nationality`, `has_name`).
      * Synthesize questions that require intersection/union across sources (e.g., “authors who won both Prize A and Prize B”).

3.  **`Reverse-Union` (Deduction $\rightarrow$ Expansion)**

      * Provide fuzzed clues at the attribute level to force anchor deduction (no direct keywords).
      * Use a pivot attribute (e.g., country) from the deduced anchor to launch a new `Union`-style search over other trees.

-----

⚙️ Training Setup & Inference

  * **Backbone:** `Qwen3-30B-A3B-Thinking-2507` (as the base model).
  * **SFT Data Mix:** WebLeaper (`Basic` / `Union` / `Reverse-Union`) + a small set of deep-search data (e.g., `WebSailor-V2`) to retain long-horizon browsing capability.
  * **SFT Trajectory Filters:** Thresholds $\alpha$ (ISR) and $\beta$ (ISE) are tuned for balanced coverage and efficiency (e.g., $\alpha=0.3$, $\beta=0.1$).
  * **RL Data Mix:** A reserved set of \~500 WebLeaper tasks (evaluated with $\mathcal{R}_{WebLeaper}$) mixed with legacy benchmark data (evaluated with $\mathcal{R}_{\text{legacy}}$).
  * **Inference Sampling:** `temperature = 0.6`, `top-p = 0.95`.

-----

🙌 Acknowledgements

WebLeaper builds on prior advances in web agent training, entity-rich task synthesis, and ReAct-style tool use. We thank the authors of the evaluated benchmarks and the maintainers of open-source toolchains used in our pipeline.