from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(dataset: str = "data/hotpot_100.json", out_dir: str = "outputs/benchmark_run", reflexion_attempts: int = 3) -> None:
    examples = load_dataset(dataset)
    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)
    
    from rich.progress import track
    
    print(f"Running benchmark on {len(examples)} examples...")
    react_records = []
    for ex in track(examples, description="[cyan]Running ReAct[/cyan]"):
        react_records.append(react.run(ex))
        
    reflexion_records = []
    for ex in track(examples, description="[magenta]Running Reflexion[/magenta]"):
        reflexion_records.append(reflexion.run(ex))
    
    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    
    report = build_report(all_records, dataset_name=Path(dataset).name, mode="groq")
    json_path, md_path = save_report(report, out_path)
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()
