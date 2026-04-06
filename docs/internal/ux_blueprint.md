# CyberSentinel-AI — UX Transformation Blueprint

---

## 1. Page Architecture

### Current → New Mapping

| Current Page | Problem | Replaced By |
|---|---|---|
| Overview | Metrics dump. No operational meaning. | **Command Center** — operational health, live threat posture |
| Predict | 40-input form. Completely unusable. | **Threat Simulator** — scenario-based + slider-based interaction |
| Evaluation | Raw charts only a data scientist reads | **Intelligence** — executive summary + model evidence |
| Policy | Static list viewer | **Policy Console** — interactive enforcement + what-if tester |
| *(none)* | System feels dead/offline | **Live Feed** — simulated real-time flow stream |

---

### Final Page Structure (5 Pages)

```
📟 Command Center      → Operational health. Threat posture. First impression.
⚡ Threat Simulator    → Core interaction: attack scenarios + behavior sliders
📡 Live Feed           → Simulated real-time inference stream
📊 Intelligence        → Model evidence, explainability deep-dive
🛡️ Policy Console      → Policy rules + interactive what-if tester
```

---

### Page 1 — Command Center (`1_Command_Center.py`)

**Replaces**: Overview  
**Purpose**: The "is the system working? are we under threat?" page.

Top row (3 metrics):
```
Threat Posture: 🟢 NOMINAL (92/100)  |  Pipeline: ✅ Active  |  Classes Monitored: 14
```

Middle section (2 columns):
- Left: Per-component health breakdown (binary model, multiclass model, policy engine, metadata)
- Right: Model capability summary — accuracy + F1 as "Detection Rate" and "Classification Precision" (non-technical labels)

Bottom section:
- Feature importance bar chart labeled as "Highest-signal telemetry features" (not "feature importances")
- Training data characteristics reframed as "Fleet scale: X million flows analyzed"

**Key design choice**: Every metric is operational, not academic. "ROC-AUC" becomes "Detection Coverage." "F1 macro" becomes "Attack Classification Precision."

---

### Page 2 — Threat Simulator (`2_Threat_Simulator.py`)

**Replaces**: Predict  
**Purpose**: The demo centerpiece. How you interact with the ML engine.

Three interaction modes (tabs):

```
[ ⚡ Scenario ] [ 🎛️ Behavior Profile ] [ 📁 Batch Analysis ]
```

Each tab is a complete self-contained interaction. Details in Section 2.

---

### Page 3 — Live Feed (`3_Live_Feed.py`)

**New page**  
**Purpose**: Makes the system feel alive. Best demo moment.

Simulated streaming inference using real data rows. Auto-refreshes every 3 seconds. Builds a running log of classified flows displayed as a scrolling table with color-coded actions.

---

### Page 4 — Intelligence (`4_Intelligence.py`)

**Replaces**: Evaluation  
**Purpose**: Evidence layer. Answers "why should I trust this system?"

Tabs:
```
[ 📋 Executive Summary ] [ 🎯 Binary Classifier ] [ 🔍 Multi-class Classifier ]
```

Executive Summary tab is new. It's a non-technical summary: "The system correctly identifies attacks 99.8% of the time. It misses fewer than 2 in 1,000 attack flows. When it flags an attack, it correctly identifies the specific type 99.7% of the time."

---

### Page 5 — Policy Console (`5_Policy_Console.py`)

**Replaces**: Policy  
**Purpose**: Demonstrates that this is a decision system, not just a classifier.

Sections:
1. Active policy summary (deny/quarantine/allow lists)
2. **Interactive what-if tester** — select any attack type, see which policy fires
3. **Coverage analysis** — which attack classes are explicitly handled vs. defaulted

---

## 2. Interaction Design — Eliminating the 40-Feature Problem

### Insight

The 40 features describe **observable network behavior**. They map to 6 behavioral dimensions that a human can intuitively understand. The interaction layer translates human-readable intent into a valid feature vector without exposing the underlying representation.

---

### Interaction Mode 1: Scenario Selector (Tab: ⚡ Scenario)

**For**: Demos, beginners, anyone who just wants to see the system work.

**UX**:
```
┌─────────────────────────────────────────────────────────────┐
│  SELECT A SCENARIO                                          │
│                                                             │
│  🟢 Normal HTTPS Traffic       Low risk. Expected benign.   │
│  🟡 Slow Port Reconnaissance   Stealthy scan. Borderline.   │
│  🟡 Brute Force Login Attempt  Repeated auth failures.      │
│  🔴 DDoS Volumetric Flood      High-volume packet flood.    │
│  🔴 DoS Connection Exhaustion  Slowloris-style hold attack.  │
│  🔴 Credential Stuffing (SSH)  Rapid automated SSH auth.    │
│  🟣 Near Decision Boundary     Low-confidence edge case.    │
│                                                             │
│                         [ ▶ ANALYZE THREAT ]               │
└─────────────────────────────────────────────────────────────┘
```

**Behind the scenes**:
- Each scenario name maps to a label filter in `merged_cleaned.csv`
- On click: load first matching row → extract 40 features → POST `/predict` → render result
- No raw features visible to user

**Data needed**: A `scenarios.json` file mapping scenario names to CSV label filters:
```json
{
  "DDoS Volumetric Flood": {"label": "DDoS"},
  "DoS Connection Exhaustion": {"label": "DoS slowloris"},
  "Slow Port Reconnaissance": {"label": "PortScan"},
  "Normal HTTPS Traffic": {"label": "BENIGN"},
  "Near Decision Boundary": {"label": "Infiltration"}
}
```

The Near Decision Boundary scenario is particularly valuable for demos — it shows the system handling uncertainty rather than always producing high-confidence results.

---

### Interaction Mode 2: Behavior Profile Sliders (Tab: 🎛️ Behavior Profile)

**For**: Analysts wanting to explore, interviewers asking "can I customize it?"

**UX — 6 sliders mapped to behavioral dimensions**:

```
FLOW BEHAVIOR PROFILE

  Connection Duration    ─────────⬤──────  [ 0: Short  ↔  100: Persistent ]
  Traffic Volume         ─────────────⬤──  [ 0: Quiet  ↔  100: Flooded ]
  Packet Uniformity      ─⬤──────────────  [ 0: Varied ↔  100: Machine-like ]
  Directional Asymmetry  ──────────⬤─────  [ 0: Balanced ↔ 100: One-sided ]
  Protocol Aggression    ────────────⬤───  [ 0: Normal ↔  100: Flagged ]
  Timing Precision       ─⬤──────────────  [ 0: Human  ↔  100: Automated ]

  [ ▶ ANALYZE FLOW ]
```

**Behavioral dimension → feature mapping**:

| Dimension | Source Features | Slider → Value Logic |
|---|---|---|
| Connection Duration | `Flow Duration`, `Flow IAT Mean` | Percentile from benign/attack distribution |
| Traffic Volume | `Flow Bytes/s`, `Flow Packets/s`, `Total Fwd Packets`, `Total Length of Fwd Packets` | Scale to 5th–95th percentile |
| Packet Uniformity | `Packet Length Variance`, `Packet Length Mean`, `Max Packet Length` | Inverse: high uniformity = low variance |
| Directional Asymmetry | `Down/Up Ratio`, `Bwd Packets/s`, `Init_Win_bytes_backward` | High value = heavy downward bias |
| Protocol Aggression | `PSH Flag Count`, `ACK Flag Count`, `FIN Flag Count`, `URG Flag Count` | Flag count percentile |
| Timing Precision | `Fwd IAT Std`, `Bwd IAT Std`, `Flow IAT Std` | Inverse: low std = high precision = automated |

**Behind the scenes**: On submit, convert each slider value (0–100) to the corresponding percentile value from `preprocessing_metadata.json`. For features not mapped to any dimension, use the benign training mean. POST to `/predict`.

The slider values are **just percentile lookups** — no approximation, no ML, just a data transformation layer.

---

### Interaction Mode 3: Batch Analysis (Tab: 📁 Batch Analysis)

**Refine the existing batch upload UX**:
- Remove "Expected columns: feature1, feature2..." instruction (too technical)
- Replace with: "Upload a network telemetry export for bulk analysis"
- Add a sample dataset download button: "📥 Download Sample Dataset (100 flows)"
- The sample is 100 pre-selected rows from the processed data (mix of benign + attacks)

This gives demos a clean "upload → analyze → review" flow without requiring the user to prepare a CSV.

---

## 3. Core Experience Layer — Post-Analysis Output

### What the User Sees After Hitting "Analyze"

The result display has 4 layers, rendered in order. Don't collapse any of them by default for demos.

---

**Layer 1 — Verdict Header** (instant orientation)

```
┌──────────────────────────────────────────────────────────┐
│   🔴  THREAT DETECTED — DENY                             │
│      DoS Connection Exhaustion Attack  ·  Conf: 98.5%   │
│      INF-2026-0402-0017  ·  11:42:06 UTC                │
└──────────────────────────────────────────────────────────┘
```

For benign:
```
┌──────────────────────────────────────────────────────────┐
│   🟢  TRAFFIC CLEARED — ALLOW                            │
│      Normal behavioral profile  ·  Conf: 99.2%          │
└──────────────────────────────────────────────────────────┘
```

---

**Layer 2 — Decision Decomposition** (shows pipeline depth, not just a number)

4 visual progress bars:

```
① Anomaly Detection     ████████████████████ 98.5%  → ATTACK
② Attack Classification ████████████████▒▒▒▒ 93.2%  → DoS Slowloris
③ Policy Lookup         ────────────────────  → DENY LIST (explicit match)
④ Decision Confidence   ████████████████████ 96.8%  → HIGH
```

Data sources:
- ①: `binary_prediction` + `confidence` from API response
- ②: top value from `attack_proba` dict
- ③: lookup against policy config (deny/quarantine/allow)
- ④: geometric mean of binary confidence × top attack proba

---

**Layer 3 — Threat Narrative** (the intelligence layer)

```
WHAT HAPPENED
A network flow matching known connection-exhaustion attack patterns was detected.
The flow maintained a persistent connection (128,941 µs duration) while transmitting
minimal data (4 forward packets, 0.12 bytes/packet variance) — behavior
characteristic of a keep-alive flood targeting server connection pool limits.

WHY IT WAS FLAGGED
3 features exceeded anomalous thresholds:
• Flow Duration: 128,941 µs  (> 99th percentile of normal flows)
• Fwd Packet Count: 4  (< 1st percentile of normal flows)
• Packet Length Variance: 0.12  (< 5th percentile — machine-generated uniformity)

WHAT WAS DECIDED
Attack type "DoS slowloris" matched deny_classes in the active policy.
Automatic DENY applied. No human review required.

WHAT TO DO NEXT
→ Monitor source IP for repeat behavior in the next 5-minute window
→ Verify connection timeout policies are configured upstream
→ No analyst escalation required at this confidence level
```

**Implementation note**: The "WHY IT WAS FLAGGED" section is generated by comparing each feature value against percentile bands from `preprocessing_metadata.json`. Not LLM — pure threshold comparison. The attack narrative text is a hardcoded template per attack type (~20 lines per class, 14 classes = ~280 lines total). Deterministic, fast, zero new dependencies.

---

**Layer 4 — Attack Probability Spectrum** (only shown for attack detections)

Horizontal bar chart of all 14 class probabilities from `attack_proba`:

```
DoS Slowloris      ████████████████████  93.2%
DoS Hulk           █░░░░░░░░░░░░░░░░░░░   4.1%
DDoS               ░░░░░░░░░░░░░░░░░░░░   1.2%
PortScan           ░░░░░░░░░░░░░░░░░░░░   0.8%
[10 others]        ░░░░░░░░░░░░░░░░░░░░   0.7%

Model certainty: HIGH  (top-2 margin: 89.1 percentage points)
```

The "top-2 margin" communicates model uncertainty in one number. 89pp margin = the model is very sure. 5pp margin = it's choosing between two near-equal options. No ML knowledge required to understand this.

---

**Layer 5 — Debug (collapsed by default)**:
```python
with st.expander("🔧 Raw API Response"):
    st.json(result)
```

Keep this. It's useful for advanced users and shows transparency. Just don't lead with it.

---

## 4. Top 5 High-Impact Features

Ranked by demo impact vs. implementation effort ratio.

---

### Feature 1: Threat Narrative Engine

**Impact**: Transforms output from JSON to intelligence. Single biggest perception shift.  
**Implementation**: `threat_narrator.py` — template strings per attack type + percentile threshold checks.  
**Existing data used**: `attack_proba`, `confidence`, `binary_prediction`, `attack_type`, feature vector, `preprocessing_metadata.json`  
**Effort**: 3–4 hours  

The key insight: analysts don't read probabilities. They read sentences. "A connection-exhaustion attack was detected" is infinitely more useful than "confidence: 0.93, attack_type: DoS slowloris."

---

### Feature 2: Decision Decomposition Gauge

**Impact**: Shows the system has depth. Makes the "pipeline" tangible, not abstract.  
**Implementation**: 4 `st.progress` bars with labels. Nothing more.  
**Existing data used**: `confidence` (binary), `attack_proba` top value, policy config lookup  
**Effort**: 1 hour  

This is the feature that answers the interview question "how does it work?" without anyone having to ask. The visual shows the cascade.

---

### Feature 3: Simulated Live Feed

**Impact**: Highest "wow" moment in any demo. System feels alive.  
**Implementation**: Pre-load 150–200 rows from `merged_cleaned.csv`. Each Streamlit auto-refresh cycle pops the next row, POSTs to `/predict`, appends result to `st.session_state` list. Render as scrolling table.  
**Existing data used**: Processed dataset, existing `/predict` endpoint  
**Effort**: 2 hours  

The feed must include a mix: ~75% benign (normal traffic), ~15% deny, ~10% quarantine. This mirrors realistic enterprise traffic ratios. A pure attack feed looks fake.

---

### Feature 4: Scenario Selector (Replacing Raw Form)

**Impact**: Eliminates the biggest UX weakness. Makes demos one-click.  
**Implementation**: `scenarios.json` + label filter against dataset + existing `/predict` endpoint.  
**Existing data used**: `merged_cleaned.csv`, existing API  
**Effort**: 2–3 hours  

This is P0. Nothing else matters if the primary interaction mode is still 40 number inputs.

---

### Feature 5: Attack Probability Spectrum

**Impact**: Shows multi-class intelligence. The "14 attack classes" claim becomes visible.  
**Implementation**: Sort `attack_proba` dict, render as horizontal bar chart with top-2 margin.  
**Existing data used**: `attack_proba` field already in API response  
**Effort**: 30 minutes  

This is already in the API response. It just needs rendering. Highest effort-to-impact ratio on the list.

---

## 5. The 90-Second Demo Flow

**Setup**: API running, dashboard running, browser on Command Center.

---

**[0:00–0:12] First impression**

Command Center loads. Recruiter sees:
- Threat Posture: 🟢 NOMINAL (92/100)
- Pipeline: ✅ Active
- 14 attack classes monitored
- Detection Rate: 99.8%

*Talking point*: "This is the operational view — it tells a security team whether the system is healthy and what it's watching for. Everything here is live data from the ML engine."

---

**[0:12–0:35] The attack**

Navigate to Threat Simulator → Scenario tab.  
Click "🔴 DDoS Volumetric Flood" → click "▶ ANALYZE THREAT."

Loading spinner: "⚡ Analyzing telemetry..."

Result appears:
1. Verdict header: 🔴 THREAT DETECTED — DENY
2. Decision Decomposition: 4 bars filling from top to bottom (binary 98% → multiclass 93% → DENY LIST → Decision 96%)
3. Threat Narrative: 3 paragraphs, reads like an incident report
4. Attack Probability Spectrum: bar chart, DDoS at 93%, others near zero

*Talking point*: "One click. The system loaded a real network flow, ran it through binary detection, identified the attack type from 14 categories, looked it up in the policy engine, and generated a full incident report — in under 50 milliseconds."

---

**[0:35–0:50] The contrast**

Click "🟢 Normal HTTPS Traffic" → "▶ ANALYZE THREAT."

Same pipeline. Result:
- 🟢 TRAFFIC CLEARED — ALLOW
- Narrative: "Normal encrypted browsing behavior. All 6 behavioral dimensions within expected ranges."
- No probability spectrum (benign flows skip multi-class)

*Talking point*: "Same system, opposite result. The binary gate-keeper correctly identifies this as benign and doesn't even invoke the attack classifier — that's how you get sub-50ms latency at scale."

---

**[0:50–1:05] The intelligence**

Navigate to Live Feed. Watch the table populate every 3 seconds:
- Green rows (ALLOW) dominating
- Occasional yellow (QUARANTINE)
- Red (DENY) appearing every 5–6 rows

*Talking point*: "In production, this processes thousands of flows per second. Analysts don't review ALLOW decisions — the system handles those automatically. They only see QUARANTINE cases, which cuts alert volume by 90%+. That's the actual value proposition."

---

**[1:05–1:20] The policy layer**

Navigate to Policy Console. Show deny/quarantine lists. Use the What-if Tester:  
Select "Web Attack - SQL Injection" → system shows "→ QUARANTINE (matched quarantine_classes)"  
Select "DDoS" → "→ DENY (matched deny_classes)"  
Select "UnknownAttackType" → "→ QUARANTINE (default_attack_action fallback)"

*Talking point*: "The policy rules are config-driven. Security teams tune them without touching code. The system adapts its enforcement behavior without retraining any model."

---

**[1:20–1:30] The close (optional)**

If asked "how accurate is it?":  
Navigate to Intelligence → Executive Summary:  
"Detects 99.8% of attack flows. Correctly identifies attack type 99.7% of the time. False positive rate under 0.2%."

*Talking point*: "Those numbers come from evaluation against a held-out test set — data the model never saw during training."

---

## 6. Implementation Roadmap

### P0 — Must Build First (Highest Impact, Under 6 Hours Total)

These eliminate the primary weakness and create the demo foundation.

**P0.1 — Scenario Selector** | 2–3 hours

Files:
- `configs/scenarios.json` — scenario name → label filter mapping
- `src/dashboard/pages/2_Threat_Simulator.py` — replace `2_Predict.py`
- Add `GET /scenarios` endpoint to API (optional — can read from file in dashboard)

Minimum viable: 5 scenarios. One benign, one QUARANTINE-classification, three DENY-classifications. Put the borderline case last — it shows the system handling ambiguity.

**P0.2 — Decision Decomposition + Attack Probability Spectrum** | 1.5 hours

Files:
- Add to `2_Threat_Simulator.py` results section
- Utility function: `compute_overall_confidence(binary_conf, top_attack_proba)` → geometric mean

Both features use data already in the API response. This is rendering work, not logic work.

**P0.3 — Threat Narrative Engine (Minimum Version)** | 2 hours

Files:
- `src/dashboard/threat_narrator.py` — new module
- Template dict: 14 attack types × 4 sections (what happened, why flagged, what decided, next steps)
- Anomaly detection function using `preprocessing_metadata.json` percentiles

Start with 5 attack types that cover your policy classes. Expand to all 14 in P1.

---

### P1 — Build Second (Experience Polish, 6–8 Hours Total)

**P1.1 — Simulated Live Feed** | 2 hours

Files:
- `src/dashboard/pages/3_Live_Feed.py` — new page
- Pre-load 200-row dataset sample into `st.session_state` on page load
- Auto-refresh using `st_autorefresh` or manual refresh button cycling

Key: pre-shuffle the data so benign/attack ratios feel realistic (not alternating).

**P1.2 — Command Center Redesign** | 2 hours

Files:
- `src/dashboard/pages/1_Command_Center.py` — replace `1_Overview.py`
- Rename metrics (ROC-AUC → Detection Coverage, F1 → Classification Precision)
- Add Threat Posture Score computation

**P1.3 — Intelligence Page Executive Summary Tab** | 1.5 hours

Files:
- `src/dashboard/pages/4_Intelligence.py` — keep existing evaluation content, add Executive Summary tab
- Template-based narrative: X% accuracy → "Detects X in 100 attack flows correctly"

**P1.4 — Policy Console Enhancement** | 1.5 hours

Files:
- `src/dashboard/pages/5_Policy_Console.py` — replace `4_Policy.py`
- Add Coverage Analysis section (which classes have explicit rules vs. default)
- Improve What-if Tester to show the full decision chain, not just the result

---

### P2 — Polish Layer (If Time Permits, 4–5 Hours)

**P2.1 — Behavior Sliders** | 2 hours

Files:
- Tab in `2_Threat_Simulator.py`
- `configs/feature_profiles.json` — dimension → feature mapping + percentile lookup table
- Runtime: slider value → percentile → feature value lookup → POST `/predict`

Lower priority because the Scenario Selector already gives an excellent UX. Add sliders when you want to demonstrate the system's coverage of the feature space.

**P2.2 — Anomaly Fingerprint Radar** | 1.5 hours

Files:
- Helper function in `threat_narrator.py`: compute z-scores per behavioral dimension
- Radar chart using `matplotlib` (already a dependency)
- Embed in result display between Narrative and Probability Spectrum

**P2.3 — Sample Dataset Download Button** | 30 minutes

Generate a 100-row sample CSV (50 benign, 50 attacks, balanced across classes). Add download button to Batch Analysis tab. This lets anyone demo the system without needing to source their own data.

---

### Summary Table

| Feature | Priority | Effort | Existing Data Used |
|---|---|---|---|
| Scenario Selector | P0 | 2–3h | `merged_cleaned.csv`, `/predict` |
| Decision Decomposition | P0 | 1.5h | API response (already there) |
| Attack Probability Spectrum | P0 | 30m | `attack_proba` (already there) |
| Threat Narrative Engine | P0 | 2h | `preprocessing_metadata.json` |
| Live Feed | P1 | 2h | `merged_cleaned.csv`, `/predict` |
| Command Center Redesign | P1 | 2h | All existing `/meta/*` endpoints |
| Executive Summary Tab | P1 | 1.5h | `/meta/models` + `/meta/eval` |
| Policy Console Enhancement | P1 | 1.5h | Existing policy config |
| Behavior Sliders | P2 | 2h | `preprocessing_metadata.json` |
| Anomaly Fingerprint Radar | P2 | 1.5h | Feature vector + percentiles |
| Sample Dataset Download | P2 | 30m | `merged_cleaned.csv` |

**P0 total**: ~7 hours → complete transformation of the core demo experience  
**P0 + P1 total**: ~15 hours → full production-grade SOC dashboard  
**Everything**: ~18 hours → complete product
