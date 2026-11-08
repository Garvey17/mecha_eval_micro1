# Mechatronics & Actuator Sizing Benchmark for LLMs (`micro1_hack`)

[![Benchmark](https://img.shields.io/badge/Benchmark-Mechatronics%20Dynamics-blue.svg)](#what-it-tests-and-why-it-matters)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 1. Short Description

This benchmark evaluates large language models (LLMs) on **Mechatronics, Robotics Actuator Sizing, and Rotational Dynamics**.

### The Gap Found
While frontier LLMs can fluently write kinematic transformations and recite textbook robotics equations, they experience catastrophic accuracy drops when solving **multi-variable physical dynamics and thermal boundary constraints**. Specifically, models systematically fail at:
1. **Reflected Rotor Inertia ($J_m \cdot N^2$):** Neglecting motor rotor inertia reflected through high gear reductions ($N \gg 1$), underpredicting peak acceleration torque requirements by up to 80–90%.
2. **RMS vs. Linear Torque Fallacy:** Confusing linear cycle-average torque with root-mean-square continuous thermal torque ($\tau_{\text{RMS}}$), directly miscalculating Joule ($I^2R$) resistive copper heating.
3. **Ambient Thermal Derating ($k_{\text{thermal}}$):** Omitting ambient operating temperature derating or using linear approximations instead of the non-linear square-root thermal headroom curve $k_{\text{thermal}} = \sqrt{\frac{T_{\text{wind,max}} - T_{\text{ambient}}}{T_{\text{wind,max}} - T_{\text{base}}}}$.

### Key Finding
**Flagship frontier models fail >80% of dynamic actuator sizing edge cases** (0% pass rate for GPT-4o and GPT-4o-mini across all 6 deterministic tasks), producing plausible, authoritative-sounding explanations while recommending actuators destined for catastrophic mechanical slippage or rapid thermal burnout.

---

## 2. Video Walkthrough Link

📺 **Watch the Walkthrough Video:**  
**[Loom Video Walkthrough](https://www.loom.com/share/4a7775c6db384a9f8ec863a9e400ecb8)**

---

## 3. Domain and Expertise

**Engineering Domain:** Mechatronics, Electromechanical Actuation Design, and Applied Robotic Dynamics.

This benchmark synthesizes core engineering principles across four foundational mechatronics domains:
- **Newton-Euler Rigid Body Rotational Dynamics:** Coupled load-gearbox-rotor inertia equations governing acceleration phase torque:
  $$\tau_{\text{peak}} = \left( J_m + \frac{J_L}{\eta \cdot N^2} \right) \cdot \alpha_m + \frac{\tau_L}{\eta \cdot N} = J_m \cdot N \cdot \alpha_L + \frac{J_L \cdot \alpha_L}{\eta \cdot N} + \frac{\tau_L}{\eta \cdot N}$$
- **Electromechanical Thermal Dissipation ($I^2R$ Copper Losses):** Continuous thermal load capacity evaluated via duty-cycle Root-Mean-Square (RMS) torque integration:
  $$\tau_{\text{RMS}} = \sqrt{ \frac{1}{T_{\text{cycle}}} \sum_{i=1}^n \tau_i^2 \, t_i }$$
- **Rotor-to-Load Mechanical Impedance Matching:** Analytical derivation of the optimal transmission ratio for maximum mechanical acceleration and minimal power dissipation:
  $$N_{\text{opt}} = \sqrt{\frac{J_L}{J_m}}$$
- **Back-EMF and Voltage/Thermal Boundary Envelopes:** Continuous torque limit derating governed by thermal dissipation ceilings in elevated ambient environments:
  $$k_{\text{thermal}} = \sqrt{\frac{T_{\text{max}} - T_{\text{amb}}}{T_{\text{max}} - T_{\text{base}}}}, \quad \tau_{\text{cont,derated}} = k_{\text{thermal}} \cdot \tau_{\text{cont,rated}}$$

---

## 4. What It Tests and Why It Matters

### Deterministic Parameters Tested
The benchmark evaluates 6 deterministic physics tasks across 6 explicit quantitative parameters per scenario:
1. **Required Peak Motor Shaft Torque ($\tau_{\text{peak}}$, $\text{N}\cdot\text{m}$):** Accounting for combined reflected inertia and gearbox transmission efficiency.
2. **Continuous RMS Motor Shaft Torque ($\tau_{\text{RMS}}$, $\text{N}\cdot\text{m}$):** Exact cyclic heating calculation over accelerating, constant-velocity, decelerating, and dwell phases.
3. **Ambient Thermal Derating Factor ($k_{\text{thermal}}$):** Non-linear thermal ceiling scaling based on ambient temperature.
4. **Derated Continuous Torque Limit ($\tau_{\text{cont,derated}}$, $\text{N}\cdot\text{m}$):** True continuous physical capacity of the motor at operating ambient temperatures.
5. **Ideal Transmission Gear Ratio ($N_{\text{opt}}$):** Inertia matching ratio maximizing dynamic joint responsiveness.
6. **Thermal Overload Determination (`thermal_overload`, boolean):** Binary verification of continuous thermal feasibility ($\tau_{\text{RMS}} > \tau_{\text{cont,derated}}$).

### Who It's For
- **Robotics Engineers & Actuator Designers:** Verifying whether AI coding assistants can correctly perform actuator sizing, gearhead selection, and thermal validation without introducing hazardous errors.
- **Autonomous System Architects:** Automating hardware-in-the-loop (HIL) design pipelines that convert trajectory profiles into mechanical specs.
- **AI Frontier Labs & Evaluators:** Benchmarking true physical grounding, unit consistency, and multi-step reasoning capabilities of LLMs on deterministic engineering problems.

### Real-World Impact
In physical electromechanical systems, an un-derated motor or an actuator selected by ignoring $J_m \cdot N^2$ results in:
- **Instantaneous Motor Stall / Dropped Payloads:** The actuator fails to reach target trajectory accelerations, violating safety-critical timing constraints.
- **Catastrophic Winding Burnout:** If continuous RMS torque exceeds the derated continuous torque limit, winding insulation degrades and suffers dielectric breakdown within minutes of physical operation.

---

## 5. Setup and Run Instructions

### Environment Setup

Clone the repository and install dependencies:
```bash
git clone https://github.com/<your-username>/micro1_hack.git
cd micro1_hack

# Install required dependencies
pip install openai python-dotenv
```

### Supplying API Keys

Export your provider API key as an environment variable (or place it in a `.env` file):

**Linux / macOS:**
```bash
export GROQ_API_KEY="your-groq-api-key"
# or
export OPENAI_API_KEY="your-openai-api-key"
# or
export OPENROUTER_API_KEY="your-openrouter-api-key"
```

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="your-groq-api-key"
# or
$env:OPENAI_API_KEY="your-openai-api-key"
# or
$env:OPENROUTER_API_KEY="your-openrouter-api-key"
```

### Execution Commands

Run the benchmark evaluation harness with a single command:

```bash
# Run using Groq (Fast & Free tier available)
python run_mechatronics_eval.py --provider groq --model llama-3.3-70b-versatile

# Run using OpenAI models
python run_mechatronics_eval.py --provider openai --model gpt-4o

# Run offline mock mode (no API key required, validates test harness)
python run_mechatronics_eval.py --provider mock --model test-dummy
```

### Runtime and Cost
- **Runtime:** ~10–30 seconds for all 6 benchmark tasks.
- **Estimated Cost:**
  - `mock`: **$0.00** (offline)
  - `groq`: **$0.00** (within free tier limits)
  - `openai` (GPT-4o / GPT-4o-mini): **<$0.05 per full run**

---

## 6. Models Tested and Results

All evaluations were executed under deterministic hyperparameters:
- **Temperature:** `0.0` (or native deterministic reasoning mode for reasoning models)
- **Runs per Task:** 1 evaluation run across all 6 physics scenarios
- **Error Tolerance:** $\pm 5\%$ relative error margin ($\text{tolerance} = 0.05$)
- **Scoring:** Strict per-task pass requires all 6 parameters within tolerance (`passed_all`). Precision score is the average accuracy across all individual parameters.

### Benchmark Results Table

| Model ID / Version | Provider | Date of Run | Temperature | Pass Rate (Perfect Tasks) | Avg Precision Score | Report File |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **o3** | OpenAI | Nov 7, 2026 | `0.0` (reasoning) | **33.33%** (2/6) | **80.50%** | [`eval_results/report_o3.json`](file:///eval_results/report_o3.json) |
| **openrouter/free** | OpenRouter | Nov 8, 2026 | `0.0` | **16.67%** (1/6) | **61.00%** | [`eval_results/report_openrouter_openrouter_free.json`](file:///eval_results/report_openrouter_openrouter_free.json) |
| **gpt-4o** | OpenAI | Nov 7, 2026 | `0.0` | **0.00%** (0/6) | **47.33%** | [`eval_results/report_gpt-4o.json`](file:///eval_results/report_gpt-4o.json) |
| **gpt-4o-mini** | OpenAI | Nov 7, 2026 | `0.0` | **0.00%** (0/6) | **41.83%** | [`eval_results/report_gpt-4o-mini.json`](file:///eval_results/report_gpt-4o-mini.json) |
| **mock (test-dummy)** | Mock | Nov 8, 2026 | N/A | **0.00%** (0/6) | **22.33%** | Validation harness |

---

## 7. Failure Analysis

Detailed inspection of the model outputs revealed three recurring, catastrophic failure modes:

```
                                  PHYSICS CALCULATION PITFALLS
                                  
   1. Rotor Inertia Ignorance              2. Arithmetic Mean Fallacy               3. Ambient Derating Omission
   
      ❌ Mistake:                             ❌ Mistake:                              ❌ Mistake:
         τ_acc = (J_L / N) * α                   τ_avg = (Σ τ_i * t_i) / T                k_thermal = 1.0 (or linear ΔT)
      
      ✅ Physics Ground Truth:                ✅ Physics Ground Truth:                 ✅ Physics Ground Truth:
         τ_acc = [J_m*N + J_L/(η*N)] * α         τ_RMS = sqrt((Σ τ_i^2 * t_i) / T)        k_thermal = sqrt((T_max - T_amb)/(T_max - T_base))
      
      🚨 Impact: 80-90% torque deficit        🚨 Impact: Severe copper loss undercount 🚨 Impact: Immediate winding insulation burnout
```

### 1. Rotor Inertia Ignorance
When calculating acceleration torque, non-reasoning frontier models (e.g. GPT-4o) compute torque using load inertia alone:
$$\tau_{\text{motor,acc}} \approx \frac{J_L \cdot \alpha_L}{N \cdot \eta}$$
They completely omit the rotor's own acceleration torque term $\tau_m = J_m \cdot \alpha_m = J_m \cdot N \cdot \alpha_L$. In Task 001, where $N = 40$, the motor rotor accelerates 40 times faster than the link; reflected rotor inertia is significant. Missing this term yields a predicted peak torque of $\approx 0.0353\,\text{N}\cdot\text{m}$ instead of the true required $0.1941\,\text{N}\cdot\text{m}$ (**an 81.8% error**).

### 2. Arithmetic Mean Torque Fallacy
Models frequently substitute the arithmetic average torque $\tau_{\text{avg}} = \frac{1}{T} \sum \tau_i t_i$ in place of the root-mean-square continuous thermal torque $\tau_{\text{RMS}} = \sqrt{\frac{1}{T} \sum \tau_i^2 t_i}$. Because resistive heating is proportional to $I^2 \propto \tau^2$, the arithmetic mean drastically underestimates winding thermal loading during high peak acceleration moves (e.g., Task 002), incorrectly certifying overloaded motors as thermally safe.

### 3. Ambient Thermal Derating Omission
Standard motor continuous torque ratings assume an ambient reference temperature of $25^\circ\text{C}$. In Task 003 ($T_{\text{ambient}} = 65^\circ\text{C}$, $T_{\text{max}} = 130^\circ\text{C}$), models either assume $k_{\text{thermal}} = 1.0$ or apply an ad-hoc linear temperature ratio $(130 - 65)/130 \approx 0.619$. The true thermal equilibrium equation requires:
$$k_{\text{thermal}} = \sqrt{\frac{130 - 65}{130 - 25}} = \sqrt{\frac{65}{105}} \approx 0.7868$$
Because of this miscalculation, models fail to correctly identify continuous thermal overload in enclosed robotic actuators.

---

## 8. Prior Work and Sources

- **Benchmark & Harness Origin:**  
  All 6 physical scenarios in [`eval_dataset.json`](file:///eval_dataset.json), the parameter boundaries, and the automated grading parser in [`run_mechatronics_eval.py`](file:///run_mechatronics_eval.py) were **designed, derived, and implemented completely from scratch** during the Micro1 Hackathon.
- **Physical Dynamics & Motor Sizing Principles:**
  - Choset, H., Lynch, K. M., Hutchinson, S., Kantor, G., Burgard, W., Kavraki, L. E., & Thrun, S. *Principles of Robot Motion: Theory, Algorithms, and Implementation*. MIT Press.
  - Spong, M. W., Hutchinson, S., & Vidyasagar, M. *Robot Modeling and Control*. John Wiley & Sons.
  - Maxon Motor AG. *The Selection of High-Precision Microdrives: A Formula Handbook for Actuator Selection and Thermal Sizing*.
  - Ellis, G. *Control System Design Guide: Using Your Computer to Understand and Diagnose Feedback Controllers*. Academic Press.
