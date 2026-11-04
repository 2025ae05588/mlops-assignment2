"""Run the assignment notebook's task code directly from Terminal."""
import argparse
import ast
import importlib.metadata
import json
import os
from pathlib import Path
import sys


def show(value):
    """Display notebook tables as readable terminal text."""
    print(value.to_string(index=True) if hasattr(value, "to_string") else str(value))
    print()



def retry_failed(folder, cells, namespace):
    """Retry only failed pairs; preserve every attempt and log a recovery evaluation."""
    import pandas as pd
    import shutil
    import uuid
    out = folder / "eduassist_output"
    manifest = json.loads((out / "manifest.json").read_text())
    current = pd.read_csv(out / "all_requests.csv")
    if len(current) != 15 or current.duplicated(["prompt_version", "question_id"]).any():
        raise RuntimeError("Retry requires a completed 15-row attempt matrix.")
    failed = current[current.status != "success"]
    if failed.empty:
        print("No failed requests to retry. Existing results left unchanged.")
        return False
    # Load configuration, prompts and API helpers, without registering new versions.
    setup = next(source for _, source in cells if "def evaluate_version(" in source)
    for index, source in cells:
        if source == setup:
            break
        exec(compile(source, f"notebook:cell{index}", "exec"), namespace)
        namespace["display"] = show
    exec(setup.split('BATCH = ')[0], namespace)
    ns = namespace
    if manifest["pricing"] != ns["PRICING"]:
        raise RuntimeError("Pricing/model settings changed; start a new batch instead of combining settings.")
    questions = ns["QUESTIONS"]
    expected = {(v, q["id"]) for v in ns["PROMPTS"] for q in questions}
    if set(zip(current.prompt_version, current.question_id)) != expected:
        raise RuntimeError("Question/version matrix changed; start a new batch.")
    question_map = {q["id"]: q["question"] for q in questions}
    if any(row.question != question_map[row.question_id] for row in current.itertuples()):
        raise RuntimeError("Question text changed; start a new batch.")
    ns["REGISTERED"] = {}
    for label, version in manifest["registry_versions"].items():
        prompt = ns["genai"].load_prompt(f"prompts:/{ns['PROMPT_NAME']}/{version}")
        if prompt.template != ns["PROMPTS"][label]:
            raise RuntimeError("Registered prompt changed; start a new batch.")
        ns["REGISTERED"][label] = prompt
    source_batch = manifest.get("source_batch", manifest["batch"])
    ns["BATCH"] = source_batch + "_retry_" + uuid.uuid4().hex[:6]
    snapshot = out / "previous_evaluations" / ns["BATCH"]
    snapshot.mkdir(parents=True)
    for name in ["all_requests.csv", "latency_tokens_cost.csv", "prompt_evaluation_results.csv", "manifest.json", "task1_latency_summary.csv", "task1_interpretation.txt", "latency_summary.csv"]:
        if (out / name).exists():
            shutil.copy2(out / name, snapshot / name)
    audit_path = out / "request_attempts.csv"
    batch_path = out / "request_attempts_batch.txt"
    if audit_path.exists() and batch_path.exists() and batch_path.read_text() == source_batch:
        audit = pd.read_csv(audit_path)
    else:
        audit = current.copy()
        audit["attempt_number"] = 1
        audit["source_batch"] = source_batch
        audit["evaluation_batch"] = manifest["batch"]
        audit.to_csv(audit_path, index=False)
        batch_path.write_text(source_batch)
    # Reuse exactly the existing request timer/parser. Its scratch file must not overwrite the matrix.
    evaluator = setup[setup.index("def evaluate_version("):]
    evaluator = evaluator[:evaluator.rfind('print("Three exact prompts')]
    evaluator = evaluator.replace('OUTPUT / "all_requests.csv"', 'OUTPUT / "latest_retry_attempt.csv"')
    exec(evaluator, ns)
    ns["_LAST_END"] = None
    print(f"Retrying {len(failed)} failed requests once each; previous attempts are retained.", flush=True)
    for index, old in failed.iterrows():
        ns["QUESTIONS"] = [q for q in questions if q["id"] == old.question_id]
        ns["ROWS"] = []
        failure = None
        try:
            ns["evaluate_version"](old.prompt_version)
        except Exception as exc:
            failure = exc
        if ns["ROWS"]:
            row = ns["ROWS"][-1]
            prior = audit[(audit.prompt_version == old.prompt_version) & (audit.question_id == old.question_id)]
            attempt = dict(row, attempt_number=int(prior.attempt_number.max()) + 1,
                           source_batch=source_batch, evaluation_batch=ns["BATCH"])
            audit = pd.concat([audit, pd.DataFrame([attempt])], ignore_index=True)
            audit.to_csv(audit_path, index=False)
            for key, value in row.items():
                current.at[index, key] = value
            current.to_csv(out / "all_requests.csv", index=False)
        if failure is not None:
            print("Stopping retries:", str(failure))
            break
    ns["QUESTIONS"] = questions
    ns["ROWS"] = current.to_dict("records")
    ns["baseline"] = current[current.prompt_version == "v1"].copy()
    ns["structured"] = current[current.prompt_version == "v2"].copy()
    ns["json_answers"] = current[current.prompt_version == "v3"].copy()
    # Recalculate tables from the latest attempt per pair, not failure+success averages.
    baseline_code = next(source for _, source in cells if 'baseline = evaluate_version("v1")' in source)
    exec(baseline_code.split("\n", 1)[1], ns)
    cost_code = next(source for _, source in cells if "BASELINE_MONTHLY =" in source)
    exec(cost_code, ns)
    comparison_code = next(source for _, source in cells if 'structured = evaluate_version("v2")' in source)
    comparison_code = comparison_code.split("requests = pd.concat", 1)[1]
    comparison_code = "requests = pd.concat" + comparison_code
    comparison_code = comparison_code.replace('        mlflow.log_metrics(metrics)',
        '        mlflow.set_tags({"evaluation_type": "recovery_latest_attempt", "source_batch": "' + source_batch + '"})\n'
        '        mlflow.log_artifact(str(OUTPUT / "request_attempts.csv"))\n'
        '        mlflow.log_metrics(metrics)')
    exec(comparison_code, ns)
    ns["manifest"].update(source_batch=source_batch, evaluation_type="recovery_latest_attempt",
                          recorded_attempts=len(audit), attempt_history="request_attempts.csv")
    (out / "manifest.json").write_text(json.dumps(ns["manifest"], indent=2))
    print("Recovery metrics use each pair's latest attempt. Original failed attempts remain in request_attempts.csv.")
    print("Report both the original failures and recovery; this is not a fresh 15-request batch.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="Existing private .env; defaults to .env beside this script")
    parser.add_argument("--check", action="store_true", help="Check setup without making API calls or creating results")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only failed requests from the last saved batch, keeping attempt history")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    env_file = (args.env_file.expanduser().resolve() if args.env_file else folder / ".env")
    notebook = json.loads((folder / "EduAssist_Assignment_Portable.ipynb").read_text())
    cells = [(i, "".join(c["source"])) for i, c in enumerate(notebook["cells"], 1) if c["cell_type"] == "code"]
    if not (3, 10) <= sys.version_info[:2] < (3, 14):
        parser.exit(1, "Use Python 3.10–3.13.\n")
    for _, source in cells:
        ast.parse(source)
    missing = []
    for spec in (folder / "requirements.txt").read_text().splitlines():
        if not spec.strip():
            continue
        package, version = spec.split("==")
        try:
            if importlib.metadata.version(package) != version:
                missing.append(spec)
        except importlib.metadata.PackageNotFoundError:
            missing.append(spec)
    if missing:
        parser.exit(1, "Install the pinned dependencies first: python -m pip install -r requirements.txt\n")
    from dotenv import dotenv_values
    if not env_file.is_file():
        parser.exit(1, "Environment file not found. Prepare .env or pass --env-file /path/to/.env\n")
    key = (dotenv_values(env_file, interpolate=False).get("GEMINI_API_KEY") or "").strip()
    if not key or key in {"your_actual_key", "replace_with_your_gemini_api_key", "your_key"}:
        parser.exit(1, "Set a real GEMINI_API_KEY in the private environment file.\n")
    print("Setup valid; credential loaded without displaying it.")
    if args.check:
        if args.retry_failed:
            import pandas as pd
            out = folder / "eduassist_output"
            saved = pd.read_csv(out / "all_requests.csv")
            if len(saved) != 15 or saved.duplicated(["prompt_version", "question_id"]).any():
                parser.exit(1, "Retry requires a saved 15-row matrix.\n")
            failed = saved[saved.status != "success"]
            print("Requests selected for retry:", len(failed))
            show(failed[["question_id", "prompt_version", "error_type", "http_status"]])
        print("No API calls made. Output folder after execution:", folder / "eduassist_output")
        return
    os.environ["EDUASSIST_ENV_FILE"] = str(env_file)
    os.chdir(folder)
    namespace = {"__name__": "__main__", "__file__": str(folder / "run_assignment.py")}
    if args.retry_failed:
        if not retry_failed(folder, cells, namespace):
            return
    else:
        print("Running 15 real Gemini requests. Results:", folder / "eduassist_output", flush=True)
        for index, source in cells:
            print(f"\n--- Assignment code cell {index} ---", flush=True)
            exec(compile(source, f"EduAssist_Assignment_Portable.ipynb:cell{index}", "exec"), namespace)
            namespace["display"] = show
    failed = namespace["requests"][namespace["requests"].status != "success"]
    if not failed.empty:
        print("\nResults saved, but these requests did not succeed:")
        columns = [c for c in ["question_id", "prompt_version", "error_type", "http_status"] if c in failed.columns]
        show(failed[columns])
        print("Production candidate:", namespace["winner"] or "None")
        print("Review eduassist_output/all_requests.csv before final submission.")
        sys.exit(2)
    if not namespace["winner"]:
        print("\nResults saved, but no version passed the production schema gate.")
        sys.exit(2)
    print("\nCompleted. CSVs and MLflow database:", folder / "eduassist_output")
    print("This terminal run does not update saved notebook outputs; execute the notebook separately if an executed notebook is required.")


if __name__ == "__main__":
    main()
