import argparse
import json
import os
import re
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()

try:
    import openai
except ImportError:
    print("Please install openai: pip install openai")
    sys.exit(1)

console = Console()

# Task 1: The Rotor Inertia Trap Prompt
TASK_1_PROMPT = """You are a mechatronics engineer sizing a BLDC motor and gearbox combination for a robotic link.
Given System Parameters:
- Load Inertia (J_L): 0.012 kg*m^2
- Motor Rotor Inertia (J_m): 0.000025 kg*m^2
- Selected Gearbox Reduction Ratio (N): 40.0:1
- Gearbox Mechanical Efficiency: 85.0%
- Required Load Acceleration (alpha): 100.0 rad/s^2
- Acceleration Phase Duration: 0.1 s
- Constant Speed Phase Load Torque: 2.0 N*m
- Constant Speed Phase Duration: 0.5 s
- Deceleration Phase Duration: 0.1 s
- Rest/Dwell Phase Duration: 1.3 s
- Nominal Motor Continuous Torque Rating (at 25.0°C): 0.25 N*m
- Operating Ambient Temperature: 25.0°C
- Maximum Allowable Winding Temperature: 130.0°C

Task: Compute the following values step-by-step:
1. Required Peak Motor Shaft Torque (N*m).
2. Required Continuous RMS Motor Shaft Torque (N*m).
3. Ambient Temperature Derating Factor k_thermal.
4. Derated Motor Continuous Torque Limit (N*m).
5. Ideal Gear Ratio N_opt for maximum inertia matching.
6. Determination: Will the motor thermally overheat during continuous operation? (Yes/No)

Provide your final calculated values inside a Markdown code block structured as JSON key-value pairs using keys: "peak_torque", "rms_torque", "derating_factor", "derated_continuous_limit", "optimal_gear_ratio", "thermal_overload"."""

TASK_1_GROUND_TRUTH = {
    "peak_torque": 0.1941,
    "rms_torque": 0.0551,
    "derating_factor": 1.0,
    "derated_continuous_limit": 0.25,
    "optimal_gear_ratio": 21.91,
    "thermal_overload": False
}

def clean_latex(text: str) -> str:
    """Strips raw LaTeX tags to prevent messy terminal outputs."""
    cleaned = text.replace(r'\[', '').replace(r'\]', '').replace(r'\(', '').replace(r'\)', '')
    cleaned = cleaned.replace(r'\cdot', '*').replace(r'\approx', '≈').replace(r'\text', '')
    cleaned = re.sub(r'\\([{}])', r'\1', cleaned)
    return cleaned

def extract_json(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match_brace = re.search(r"(\{.*?\})", text, re.DOTALL)
    if match_brace:
        try:
            return json.loads(match_brace.group(1))
        except Exception:
            pass
    return {}

def run_single_demo(provider: str, model_name: str):
    console.clear()
    console.print(Panel.fit("[bold yellow]⚡ MechaEval-Torque Live Model Verification[/bold yellow]", border_style="yellow"))
    
    # 1. Dispatch API Call
    if provider == "groq":
        key = os.getenv("GROQ_API_KEY")
        if not key:
            console.print("[bold red]ERROR: GROQ_API_KEY environment variable not set.[/bold red]")
            return
        client = openai.OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
    elif provider == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            console.print("[bold red]ERROR: OPENAI_API_KEY environment variable not set.[/bold red]")
            return
        client = openai.OpenAI(api_key=key)
    elif provider == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            console.print("[bold red]ERROR: OPENROUTER_API_KEY environment variable not set.[/bold red]")
            return
        client = openai.OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")

    console.print(f"[bold cyan]Querying Target Model:[/bold cyan] [white]{provider} / {model_name}[/white]")
    console.print("[dim]Generating step-by-step mechatronics physics response...[/dim]\n")

    start_time = time.time()
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": TASK_1_PROMPT}],
        temperature=0.0
    )
    latency = round(time.time() - start_time, 2)
    raw_text = response.choices[0].message.content

    # 2. Render LLM Explanation Cleanly
    cleaned_text = clean_latex(raw_text)
    console.print(Panel(Markdown(cleaned_text), title=f"[bold green]Model Explanation ({latency}s)[/bold green]", border_style="green"))

    # 3. Parse and Compare JSON against Physics Ground Truth
    predicted = extract_json(raw_text)
    
    table = Table(title="📊 Physics Verification: Predicted vs. Ground Truth", header_style="bold magenta")
    table.add_column("Parameter", style="cyan")
    table.add_column("Predicted by Model", style="white")
    table.add_column("Ground Truth", style="green")
    table.add_column("Status", style="bold")

    keys = [
        ("Peak Torque (N*m)", "peak_torque", TASK_1_GROUND_TRUTH["peak_torque"]),
        ("RMS Torque (N*m)", "rms_torque", TASK_1_GROUND_TRUTH["rms_torque"]),
        ("Optimal Gear Ratio", "optimal_gear_ratio", TASK_1_GROUND_TRUTH["optimal_gear_ratio"]),
        ("Thermal Overload", "thermal_overload", TASK_1_GROUND_TRUTH["thermal_overload"])
    ]

    all_passed = True
    for label, key_name, gt_val in keys:
        pred_val = predicted.get(key_name, "N/A")
        passed = False
        
        if isinstance(gt_val, bool):
            if isinstance(pred_val, str):
                pred_val = pred_val.strip().lower() in ["true", "yes", "1"]
            passed = (pred_val == gt_val)
        elif isinstance(pred_val, (int, float)):
            rel_err = abs(pred_val - gt_val) / abs(gt_val)
            passed = rel_err <= 0.05
            
        status = "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]"
        if not passed:
            all_passed = False
        table.add_row(label, str(pred_val), str(gt_val), status)

    console.print(table)
    
    if not all_passed:
        console.print(Panel("[bold red]❌ PHYSICAL FAILURE DETECTED[/bold red]\nThe model omitted reflected rotor inertia (J_m * N^2) or calculated linear torque averages instead of RMS, leading to an incorrect actuator specification.", border_style="red"))
    else:
        console.print(Panel("[bold green]✅ ALL PHYSICS METRICS PASSED[/bold green]", border_style="green"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Single Task Demo for Loom Video")
    parser.add_argument("--provider", type=str, default="groq", choices=["groq", "openai", "openrouter"])
    parser.add_argument("--model", type=str, default="llama-3.3-70b-versatile")
    args = parser.parse_args()

    run_demo = run_single_demo(args.provider, args.model)