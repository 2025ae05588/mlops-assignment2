# MLOps Assignment 2: run instructions

This is the working submission folder. The notebook has no saved outputs; run it with your own Gemini key to generate your results.

## Run from Terminal (local CPU)

`run_assignment.py` executes the task code from the included notebook, using the same questions, prompts, Gemini calls and MLflow setup. Keep both files together. Gemini inference is remote; no GPU is needed locally.

On this Mac, open Terminal and run:

```sh
cd "/Users/admin/Documents/ChatGPT/mlops-assignment2/Assignment_Submission"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Use Python 3.10–3.13. If your default `python3` is a different version, use an installed compatible interpreter such as `python3.13` when creating the environment.

A `.env` file with a placeholder is included beside the runner. Open it as plain text and replace `replace_with_your_gemini_api_key` with your Gemini API key. On macOS use Command+Shift+. to reveal it in Finder, or run `open -e .env` from this folder.

Check setup, then run the actual experiment:

```sh
python run_assignment.py --check
python -u run_assignment.py
```

The runner reads `.env` beside it automatically. To use another existing file instead, pass `--env-file /absolute/path/to/.env`. Before final submission, restore the placeholder in `.env` and verify the real key is absent. `ENV.example` is an optional clean reference template.

The real run makes 15 requests and prints tables in Terminal. Allow several minutes because there is a 15-second pause between calls. `--check` only checks local setup; it does not verify remote model access or quota. Errors and partial results should be reviewed before considering the run complete.

Outputs always go into `eduassist_output` beside the runner, even if launched from another directory. Repeated executions overwrite the CSV snapshots and add new MLflow runs/registry versions. Keep screenshots and report data from the same run.

### Open MLflow in a second Terminal

After the experiment finishes, open another Terminal window:

```sh
cd "/Users/admin/Documents/ChatGPT/mlops-assignment2/Assignment_Submission"
source .venv/bin/activate
python -m mlflow server --backend-store-uri "sqlite:///$(pwd)/eduassist_output/mlflow.db" --host 127.0.0.1 --port 5051 --workers 1
```

Open http://127.0.0.1:5051 in your browser. No Colab proxy or special host settings are needed. Press Control+C in the server terminal when finished. If port 5051 is occupied, choose another unused port, such as 5052.

The runner does not generate PDFs, HTML, screenshots, or saved notebook outputs. The assignment still requires an executed notebook; choose the notebook workflow below if you want saved cell outputs as part of the run. Avoid executing both workflows unnecessarily, as each complete run makes another 15 requests.

## Local Jupyter

Use Python 3.10–3.13. The earlier experiment was verified with Python 3.13.5.

1. Keep these files together in this writable submission folder.
2. Edit the included `.env` and replace its placeholder with your Gemini API key.
3. Install and open Jupyter:

```sh
python -m pip install -r requirements.txt
python -m pip install jupyterlab
python -m jupyterlab
```

4. Edit the included `.env` with your key before opening Jupyter. If you previously set `EDUASSIST_ENV_FILE` to another location, unset it before launching Jupyter to use the file beside the notebook. Open `EduAssist_Assignment_Portable.ipynb` and select Run All. Restart the kernel if requested after dependency installation.
5. Review the answers and tables. The notebook makes 15 requests: five per prompt version. Results are saved in `eduassist_output`.

## Google Colab

Open the notebook, connect to a CPU runtime, and upload your prepared `.env` into `/content` using the Files panel. Select Run All. Download results using the Files panel: open `eduassist_output`, then use each file's menu to download it. Files are generated automatically, but browser downloads do not start automatically. Save/download the executed notebook before disconnecting. The user has also completed a Colab run.

## Required results

The notebook and terminal runner generate:

- `eduassist_output/latency_tokens_cost.csv`: the five Task 1 requests and token/cost results.
- `eduassist_output/prompt_evaluation_results.csv`: comparison of all three prompts.

Locally these are already saved on disk; no download is needed. In Colab download both before the runtime ends. Other generated files support your analysis and MLflow tracking.

## Take the MLflow screenshots

MLflow registration, evaluation and alias assignment happen in Task 3. Starting the UI and taking screenshots are separate manual steps. For local Jupyter, use the terminal command below. For Colab, ask for UI access instructions after the experiment completes. Capture all five views from your completed run and save them in the supplied `screenshots` folder:

1. `experiment.jpg`: experiment with the three runs.
2. `metrics.jpg`: the required metrics for the three versions.
3. `prompt_registry.jpg`: all three prompt versions.
4. `prompt_diff.jpg`: prompt differences/comparison.
5. `production_alias.jpg`: selected version with the production alias.

For a terminal launch, run this from the generated `eduassist_output` folder:

```sh
python -m mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5051
```

## Final submission: complete later

The final report will be prepared separately after the experiment. The notebook contains no PDF/HTML generation, screenshot capture, or UI-launch code. After reviewing your results, prepare a 500–700-word report PDF with the required promotion justification of at least 150 words. This discussion must cover quality, JSON validity, latency, tokens and cost. Ask for a final submission check when ready.

Before submitting, check that the ZIP contains the executed notebook, its HTML/PDF export, requirements.txt, both required CSVs, all five MLflow screenshots, final report PDF and README. Use evidence from the same run. The submitted `.env` must contain only the placeholder, never your real API key.

## Configuration and libraries

`GEMINI_API_KEY` is required. Optional variable: `GEMINI_REQUEST_INTERVAL_SECONDS` (default 15). The notebook loads `.env` using python-dotenv and reads the key from the environment. A valid key, model access, quota and internet access are required.

Pinned libraries: MLflow, pandas, SQLAlchemy, python-dotenv, certifi and ipykernel. The notebook records the model, API version, pricing date and currency. A fresh run may give different responses and latencies.

## Working folder

Maintain this folder as the single current submission. Update its existing files directly; do not generate ZIPs or duplicate submission folders during editing. Add the result CSVs, executed notebook/export, five screenshots and final report here after the actual run. Create the final ZIP only when the submission is complete.

When requesting the final submission check, review all required files and prepare the final report using the same run. Remember to capture the five MLflow views listed above. The included `.env` is the local input file. Edit it with your key before running; restore its placeholder before final submission. For Colab, upload the prepared `.env` into the runtime. Never submit a real key.

Request timeout: `GEMINI_REQUEST_TIMEOUT_SECONDS` defaults to 120 seconds per request. Timed-out requests are recorded as failures without automatic retries. The runner reports failed question/version pairs and exits with status 2 if any request fails, while retaining the CSVs and MLflow evidence. A timeout does not imply the provider generated no output or incurred no usage. Re-running starts a new full batch; preserve earlier evidence first if needed.

## Retry failed requests without repeating successful ones

After a completed run reports failures, wait a few minutes if Gemini returned HTTP 503, then run:

```sh
python run_assignment.py --retry-failed --check
python -u run_assignment.py --retry-failed
```

This retries each failed question/version pair once. It reuses existing registered prompts and successful responses, preserves previous evaluation files under `eduassist_output/previous_evaluations`, and records all original attempts and retries in `request_attempts.csv`. Each attempt has its own measured latency. It recalculates the required CSVs from the latest attempt per pair and creates three new MLflow evaluation runs tagged `evaluation_type=recovery_latest_attempt`. Capture screenshots from these three recovery runs together.

Recovery results combine retained original successes with newly attempted failures; they are not a fresh batch of 15 simultaneous requests. Report the original failure counts and recovery separately. Unknown token usage for timed-out attempts cannot be assumed to be zero provider usage. Include `request_attempts.csv` when sharing results for the report. If a retry still fails, it is retained as a failure; another explicit retry command can be run later. Full runs do not automatically retry.

## Clone and run on the Prayogshala VM

Use a VM with Python 3.10–3.13 and outbound HTTPS access to Gemini. A CPU machine is sufficient; Gemini inference runs on Google's servers. This project has been run locally and in Colab; this specific VM has not been tested.

Repository: https://github.com/2025ae05588/mlops-assignment2 (private). Sign in to GitHub on the VM using its supported Git credential method first. For HTTPS Git, use an authorized GitHub token through the credential prompt rather than your account password; never put a token directly in a clone URL. If GitHub CLI is available, `gh auth login` followed by `gh auth setup-git` configures access.

```sh
git clone https://github.com/2025ae05588/mlops-assignment2.git
cd mlops-assignment2/Assignment_Submission
```

Then run:

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp -n ENV.example .env
nano .env
```

Replace the placeholder with your Gemini key and save. The private `.env` is ignored by Git and is not published. Check setup and execute:

```sh
python run_assignment.py --check
python -u run_assignment.py
```

For an executed notebook with saved outputs, use local Jupyter on the VM instead of the Python runner:

```sh
python -m pip install jupyterlab
python -m jupyterlab --no-browser --ip 127.0.0.1 --port 8888
```

Open the notebook through the VM's supported browser/port forwarding mechanism. Use Run All, then save it. Both workflows generate files under `Assignment_Submission/eduassist_output`; each full execution makes 15 API requests. Do not execute both workflows unnecessarily.

Start MLflow from a second VM terminal, in the same `Assignment_Submission` directory:

```sh
source .venv/bin/activate
python -m mlflow server --backend-store-uri "sqlite:///$(pwd)/eduassist_output/mlflow.db" --host 127.0.0.1 --port 5051 --workers 1
```

Use the VM's port forwarding for 5051. With SSH access, a local tunnel can forward both services:

```sh
ssh -L 8888:127.0.0.1:8888 -L 5051:127.0.0.1:5051 YOUR_VM_USER@YOUR_VM_HOST
```

Then open the token-bearing Jupyter URL printed by its terminal at localhost:8888, and MLflow at http://127.0.0.1:5051 on your own computer. VM usernames, hosts and permitted forwarding options depend on Prayogshala's access configuration.

Saved CSVs in Git are a snapshot. The SQLite database is local runtime data; create a fresh VM run to populate its MLflow UI. Never commit a real key or the virtual environment. Use `git pull` from the cloned repository to receive later code changes; preserve your own uncommitted result files before updating.
