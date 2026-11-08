import argparse
import json
import math
import os
import re
import sys
import time
from typing import Any, Dict, List
from dotenv import load_dotenv

load_dotenv()

try:
    import openai
except ImportError:
    openai = None

# ==========================================
# 1. BENCHMARK DATASET (6 PHYSICS TASKS)
# ==========================================

BENCHMARK_TASKS = [
    {
        "task_id": "task_001_rotor_inertia_trap",
        "category": "rotor_inertia",
        "prompt": "You are a mechatronics engineer sizing a BLDC motor and gearbox combination for a robotic link.\nGiven System Parameters:\n- Load Inertia (J_L): 0.012 kg*m^2\n- Motor Rotor Inertia (J_m): 0.000025 kg*m^2\n- Selected Gearbox Reduction Ratio (N): 40.0:1\n- Gearbox Mechanical Efficiency: 85.0%\n- Required Load Acceleration (alpha): 100.0 rad/s^2\n- Acceleration Phase Duration: 0.1 s\n- Constant Speed Phase Load Torque: 2.0 N*m\n- Constant Speed Phase Duration: 0.5 s\n- Deceleration Phase Duration: 0.1 s\n- Rest/Dwell Phase Duration: 1.3 s\n- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.25 N*m\n- Operating Ambient Temperature: 25.0°C\n- Maximum Allowable Winding Temperature: 130.0°C\n\nTask: Compute the following values step-by-step:\n1. Required Peak Motor Shaft Torque (N*m).\n2. Required Continuous RMS Motor Shaft Torque (N*m).\n3. Ambient Temperature Derating Factor k_thermal.\n4. Derated Motor Continuous Torque Limit (N*m).\n5. Ideal Gear Ratio N_opt for maximum inertia matching.\n6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)\n\nProvide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: \"peak_torque\", \"rms_torque\", \"derating_factor\", \"derated_continuous_limit\", \"optimal_gear_ratio\", \"thermal_overload\".",
        "ground_truth": {
            "peak_torque": 0.1941,
            "rms_torque": 0.0551,
            "derating_factor": 1.0,
            "derated_continuous_limit": 0.25,
            "optimal_gear_ratio": 21.91,
            "thermal_overload": False
        }
    },
    {
        "task_id": "task_002_duty_cycle_thermal_stress",
        "category": "rms_thermal_trap",
        "prompt": "You are a mechatronics engineer sizing a BLDC motor for an automated pick-and-place gantry.\nGiven System Parameters:\n- Load Inertia (J_L): 0.005 kg*m^2\n- Motor Rotor Inertia (J_m): 0.000010 kg*m^2\n- Selected Gearbox Reduction Ratio (N): 20.0:1\n- Gearbox Mechanical Efficiency: 90.0%\n- Required Load Acceleration (alpha): 150.0 rad/s^2\n- Acceleration Phase Duration: 0.2 s\n- Constant Speed Phase Load Torque: 4.0 N*m\n- Constant Speed Phase Duration: 0.8 s\n- Deceleration Phase Duration: 0.2 s\n- Rest/Dwell Phase Duration: 0.3 s\n- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.19 N*m\n- Operating Ambient Temperature: 25.0°C\n- Maximum Allowable Winding Temperature: 130.0°C\n\nTask: Compute the following values step-by-step:\n1. Required Peak Motor Shaft Torque (N*m).\n2. Required Continuous RMS Motor Shaft Torque (N*m).\n3. Ambient Temperature Derating Factor k_thermal.\n4. Derated Motor Continuous Torque Limit (N*m).\n5. Ideal Gear Ratio N_opt for maximum inertia matching.\n6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)\n\nProvide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: \"peak_torque\", \"rms_torque\", \"derating_factor\", \"derated_continuous_limit\", \"optimal_gear_ratio\", \"thermal_overload\".",
        "ground_truth": {
            "peak_torque": 0.2939,
            "rms_torque": 0.2022,
            "derating_factor": 1.0,
            "derated_continuous_limit": 0.19,
            "optimal_gear_ratio": 22.36,
            "thermal_overload": True
        }
    },
    {
        "task_id": "task_003_ambient_thermal_derating",
        "category": "ambient_temp_trap",
        "prompt": "You are a mechatronics engineer sizing a motor for a joint module inside a sealed enclosure.\nGiven System Parameters:\n- Load Inertia (J_L): 0.008 kg*m^2\n- Motor Rotor Inertia (J_m): 0.000015 kg*m^2\n- Selected Gearbox Reduction Ratio (N): 25.0:1\n- Gearbox Mechanical Efficiency: 88.0%\n- Required Load Acceleration (alpha): 80.0 rad/s^2\n- Acceleration Phase Duration: 0.15 s\n- Constant Speed Phase Load Torque: 4.2 N*m\n- Constant Speed Phase Duration: 0.8 s\n- Deceleration Phase Duration: 0.15 s\n- Rest/Dwell Phase Duration: 0.9 s\n- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.16 N*m\n- Operating Ambient Temperature: 65.0°C\n- Baseline Rating Ambient Temperature: 25.0°C\n- Maximum Allowable Winding Temperature: 130.0°C\n\nTask: Compute the following values step-by-step:\n1. Required Peak Motor Shaft Torque (N*m).\n2. Required Continuous RMS Motor Shaft Torque (N*m).\n3. Ambient Temperature Derating Factor k_thermal.\n4. Derated Motor Continuous Torque Limit (N*m).\n5. Ideal Gear Ratio N_opt for maximum inertia matching.\n6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)\n\nProvide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: \"peak_torque\", \"rms_torque\", \"derating_factor\", \"derated_continuous_limit\", \"optimal_gear_ratio\", \"thermal_overload\".",
        "ground_truth": {
            "peak_torque": 0.2500,
            "rms_torque": 0.1434,
            "derating_factor": 0.7868,
            "derated_continuous_limit": 0.1259,
            "optimal_gear_ratio": 23.09,
            "thermal_overload": True
        }
    },
    {
        "task_id": "task_004_optimal_inertia_matching",
        "category": "inertia_mismatch",
        "prompt": "You are sizing an actuator for a high-speed robotic arm joint with significant load inertia.\nGiven System Parameters:\n- Load Inertia (J_L): 0.045 kg*m^2\n- Motor Rotor Inertia (J_m): 0.000050 kg*m^2\n- Selected Gearbox Reduction Ratio (N): 10.0:1\n- Gearbox Mechanical Efficiency: 90.0%\n- Required Load Acceleration (alpha): 50.0 rad/s^2\n- Acceleration Phase Duration: 0.2 s\n- Constant Speed Phase Load Torque: 5.0 N*m\n- Constant Speed Phase Duration: 0.6 s\n- Deceleration Phase Duration: 0.2 s\n- Rest/Dwell Phase Duration: 1.0 s\n- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.40 N*m\n- Operating Ambient Temperature: 25.0°C\n- Maximum Allowable Winding Temperature: 130.0°C\n\nTask: Compute the following values step-by-step:\n1. Required Peak Motor Shaft Torque (N*m).\n2. Required Continuous RMS Motor Shaft Torque (N*m).\n3. Ambient Temperature Derating Factor k_thermal.\n4. Derated Motor Continuous Torque Limit (N*m).\n5. Ideal Gear Ratio N_opt for maximum inertia matching.\n6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)\n\nProvide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: \"peak_torque\", \"rms_torque\", \"derating_factor\", \"derated_continuous_limit\", \"optimal_gear_ratio\", \"thermal_overload\".",
        "ground_truth": {
            "peak_torque": 0.8306,
            "rms_torque": 0.4116,
            "derating_factor": 1.0,
            "derated_continuous_limit": 0.40,
            "optimal_gear_ratio": 30.00,
            "thermal_overload": True
        }
    },
    {
        "task_id": "task_005_back_emf_voltage_limit",
        "category": "electrical_voltage_saturation",
        "prompt": "You are evaluating an actuator operating at high rotational velocity.\nGiven System Parameters:\n- Load Inertia (J_L): 0.002 kg*m^2\n- Motor Rotor Inertia (J_m): 0.000008 kg*m^2\n- Selected Gearbox Reduction Ratio (N): 15.0:1\n- Gearbox Mechanical Efficiency: 90.0%\n- Required Load Acceleration (alpha): 200.0 rad/s^2\n- Acceleration Phase Duration: 0.15 s\n- Constant Speed Phase Load Torque: 1.5 N*m\n- Constant Speed Phase Duration: 0.5 s\n- Deceleration Phase Duration: 0.15 s\n- Rest/Dwell Phase Duration: 1.2 s\n- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.15 N*m\n- Operating Ambient Temperature: 25.0°C\n- Maximum Allowable Winding Temperature: 130.0°C\n\nTask: Compute the following values step-by-step:\n1. Required Peak Motor Shaft Torque (N*m).\n2. Required Continuous RMS Motor Shaft Torque (N*m).\n3. Ambient Temperature Derating Factor k_thermal.\n4. Derated Motor Continuous Torque Limit (N*m).\n5. Ideal Gear Ratio N_opt for maximum inertia matching.\n6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)\n\nProvide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: \"peak_torque\", \"rms_torque\", \"derating_factor\", \"derated_continuous_limit\", \"optimal_gear_ratio\", \"thermal_overload\".",
        "ground_truth": {
            "peak_torque": 0.1647,
            "rms_torque": 0.0733,
            "derating_factor": 1.0,
            "derated_continuous_limit": 0.15,
            "optimal_gear_ratio": 15.81,
            "thermal_overload": False
        }
    },
    {
        "task_id": "task_006_combined_multi_variable_edge_case",
        "category": "combined_multi_variable",
        "prompt": "You are sizing a heavy-duty industrial joint motor operating under extreme ambient conditions.\nGiven System Parameters:\n- Load Inertia (J_L): 0.020 kg*m^2\n- Motor Rotor Inertia (J_m): 0.000030 kg*m^2\n- Selected Gearbox Reduction Ratio (N): 35.0:1\n- Gearbox Mechanical Efficiency: 75.0%\n- Required Load Acceleration (alpha): 110.0 rad/s^2\n- Acceleration Phase Duration: 0.12 s\n- Constant Speed Phase Load Torque: 4.5 N*m\n- Constant Speed Phase Duration: 0.5 s\n- Deceleration Phase Duration: 0.12 s\n- Rest/Dwell Phase Duration: 0.5 s\n- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.30 N*m\n- Operating Ambient Temperature: 70.0°C\n- Baseline Rating Ambient Temperature: 25.0°C\n- Maximum Allowable Winding Temperature: 130.0°C\n\nTask: Compute the following values step-by-step:\n1. Required Peak Motor Shaft Torque (N*m).\n2. Required Continuous RMS Motor Shaft Torque (N*m).\n3. Ambient Temperature Derating Factor k_thermal.\n4. Derated Motor Continuous Torque Limit (N*m).\n5. Ideal Gear Ratio N_opt for maximum inertia matching.\n6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)\n\nProvide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: \"peak_torque\", \"rms_torque\", \"derating_factor\", \"derated_continuous_limit\", \"optimal_gear_ratio\", \"thermal_overload\".",
        "ground_truth": {
            "peak_torque": 0.3707,
            "rms_torque": 0.1588,
            "derating_factor": 0.7559,
            "derated_continuous_limit": 0.2268,
            "optimal_gear_ratio": 25.82,
            "thermal_overload": False
        }
    }
]

# ==========================================
# 2. EVALUATION & PARSING ENGINE
# ==========================================

class Evaluator:
    @staticmethod
    def parse_json(response_text: str) -> Dict[str, Any]:
        if not response_text:
            return {}
        
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
                
        brace_match = re.search(r"(\{.*?\})", response_text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except json.JSONDecodeError:
                pass
                
        return {}

    @classmethod
    def score(cls, response_text: str, ground_truth: Dict[str, Any], tolerance: float = 0.05) -> Dict[str, Any]:
        parsed = cls.parse_json(response_text)
        keys = [
            ("peak_torque", "peak_torque"),
            ("rms_torque", "rms_torque"),
            ("derating_factor", "derating_factor"),
            ("derated_continuous_limit", "derated_continuous_limit"),
            ("optimal_gear_ratio", "optimal_gear_ratio"),
        ]

        metrics = {}
        correct_count = 0
        total_checks = len(keys) + 1

        if not parsed:
            return {
                "json_valid": False,
                "score": 0.0,
                "passed_all": False,
                "metrics": {}
            }

        for parsed_key, gt_key in keys:
            val = parsed.get(parsed_key)
            gt_val = ground_truth.get(gt_key)

            if val is not None and isinstance(val, (int, float)):
                rel_diff = abs(val - gt_val) / abs(gt_val) if gt_val != 0 else abs(val)
                is_correct = rel_diff <= tolerance
            else:
                rel_diff = None
                is_correct = False

            if is_correct:
                correct_count += 1

            metrics[parsed_key] = {
                "expected": gt_val,
                "predicted": val,
                "rel_error": round(rel_diff, 4) if rel_diff is not None else None,
                "passed": is_correct
            }

        pred_overload = parsed.get("thermal_overload")
        gt_overload = ground_truth.get("thermal_overload")
        if isinstance(pred_overload, str):
            pred_overload = pred_overload.strip().lower() in ["true", "yes", "1"]

        bool_passed = (pred_overload == gt_overload)
        if bool_passed:
            correct_count += 1

        metrics["thermal_overload"] = {
            "expected": gt_overload,
            "predicted": pred_overload,
            "passed": bool_passed
        }

        return {
            "json_valid": True,
            "score": round(correct_count / total_checks, 2),
            "passed_all": correct_count == total_checks,
            "metrics": metrics
        }

# ==========================================
# 3. UNIFIED MODEL DISPATCHER
# ==========================================

def call_model(provider: str, model_name: str, prompt: str) -> str:
    if provider == "mock":
        # Offline simulation of standard flawed LLM answers (shows eval engine works)
        time.sleep(0.3)
        return '''
        Based on basic mechanics calculations:
        1. Peak Torque = J_L * alpha / N = 0.08 N*m
        2. Average Torque = 0.04 N*m
        ```json
        {
          "peak_torque": 0.08,
          "rms_torque": 0.04,
          "derating_factor": 1.0,
          "derated_continuous_limit": 0.25,
          "optimal_gear_ratio": 20.0,
          "thermal_overload": false
        }
        ```
        '''

    if not openai:
        raise ImportError("Please install openai package: pip install openai")

    if provider == "groq":
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        client = openai.OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return response.choices[0].message.content

    elif provider == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
        client = openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        return response.choices[0].message.content

    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        client = openai.OpenAI(api_key=key)
        is_reasoning = any(m in model_name for m in ["o1", "o3"])
        kwargs = {} if is_reasoning else {"temperature": 0.0}
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return response.choices[0].message.content

    else:
        raise ValueError(f"Unknown provider: {provider}")

# ==========================================
# 4. BENCHMARK HARNESS RUNNER
# ==========================================

def run_mechatronics_eval(provider: str, model_name: str, tolerance: float = 0.05, outdir: str = "eval_results"):
    os.makedirs(outdir, exist_ok=True)

    print("\n==================================================")
    print(f"  RUNNING EVAL BENCHMARK [{provider.upper()}]")
    print(f"  Model Target : {model_name}")
    print(f"  Tasks        : {len(BENCHMARK_TASKS)} | Error Margin: ±{int(tolerance*100)}%")
    print("==================================================\n")

    results = []
    total_score = 0.0
    perfect_passes = 0

    for idx, task in enumerate(BENCHMARK_TASKS, 1):
        task_id = task["task_id"]
        category = task["category"]
        print(f"[{idx}/{len(BENCHMARK_TASKS)}] Testing {task_id}... ", end="", flush=True)

        start_time = time.time()
        try:
            raw_text = call_model(provider, model_name, task["prompt"])
            latency = round(time.time() - start_time, 2)

            eval_res = Evaluator.score(raw_text, task["ground_truth"], tolerance)
            eval_res["task_id"] = task_id
            eval_res["category"] = category
            eval_res["latency_sec"] = latency
            eval_res["raw_response"] = raw_text

            if eval_res["passed_all"]:
                perfect_passes += 1
                print(f"PASSED [{latency}s]")
            else:
                print(f"FAILED (Score: {eval_res['score']}) [{latency}s]")

            total_score += eval_res["score"]

        except Exception as e:
            print(f"ERROR: {str(e)}")
            eval_res = {
                "task_id": task_id,
                "category": category,
                "score": 0.0,
                "passed_all": False,
                "error": str(e)
            }

        results.append(eval_res)

    avg_score = round(total_score / len(BENCHMARK_TASKS), 4)
    pass_rate = round((perfect_passes / len(BENCHMARK_TASKS)) * 100, 2)

    summary = {
        "provider": provider,
        "model": model_name,
        "total_tasks": len(BENCHMARK_TASKS),
        "passed_tasks": perfect_passes,
        "pass_rate_pct": pass_rate,
        "avg_precision_score": avg_score,
        "details": results
    }

    report_path = os.path.join(outdir, f"report_{provider}_{model_name.replace('/', '_')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n==================================================")
    print("                SUMMARY RESULTS                   ")
    print("==================================================")
    print(f" Provider & Model      : {provider} / {model_name}")
    print(f" Perfect Tasks Passed  : {perfect_passes} / {len(BENCHMARK_TASKS)} ({pass_rate}%)")
    print(f" Overall Accuracy      : {avg_score * 100}%")
    print(f" Full Report Saved To  : {report_path}")
    print("==================================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mechatronics Benchmark Engine")
    parser.add_argument("--provider", type=str, default="groq", choices=["groq", "openrouter", "openai", "mock"], help="API Provider")
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile", help="Model ID")
    parser.add_argument("--tolerance", type=float, default=0.05, help="Error margin (default 0.05)")
    args = parser.parse_args()

    run_mechatronics_eval(args.provider, args.model, args.tolerance)