"""Run reviewable, fresh Claude CLI sessions with image content blocks."""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import random
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schedule_jobs(conditions, repeats, seed=None):
    jobs = [(condition, repeat) for condition in conditions for repeat in range(1, repeats + 1)]
    if seed is not None:
        random.Random(seed).shuffle(jobs)
    return jobs


def final_result(stdout, returncode, expected_model):
    """Reject infrastructure failures, truncated streams and silent model changes."""
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    results = [event for event in events if event.get("type") == "result"]
    if not results:
        return {"status": "infrastructure_error", "reason": "No final CLI result"}
    result = results[-1]
    if returncode != 0 or result.get("is_error") or result.get("subtype") != "success":
        return {"status": "infrastructure_error", "reason": result.get("result", result.get("subtype")), "cli_result": result}
    models = result.get("modelUsage", {})
    if not models or any(model != expected_model for model in models):
        return {"status": "invalid_model", "reason": "Unexpected modelUsage", "cli_result": result}
    answer = result.get("result", "")
    try:
        parsed = json.loads(answer)
    except (json.JSONDecodeError, TypeError):
        parsed = None
    return {"status": "completed", "answer": answer, "parsed_answer": parsed, "cli_result": result}


def run_one(protocol, condition, repeat, run_dir):
    ident = condition["id"] + "-" + str(repeat)
    out = run_dir / ident
    out.mkdir()
    images = [ROOT / "inputs" / name for name in condition["images"]]
    command = [
        "claude", "--safe-mode", "-p", "--model", protocol["model"],
        "--effort", protocol["effort"], "--tools", "", "--strict-mcp-config",
        "--mcp-config", '{"mcpServers":{}}', "--no-session-persistence",
        "--output-format", "stream-json", "--input-format", "stream-json",
        "--verbose", "--max-budget-usd", str(protocol["max_budget_usd_per_call"]),
        "--system-prompt", protocol["system_prompt"],
    ]
    request = {
        "condition": condition["id"], "repeat": repeat,
        "prompt": condition["prompt"], "system_prompt": protocol["system_prompt"],
        "images": [{"path": str(path.relative_to(ROOT)), "sha256": digest(path)} for path in images],
        "command": command, "started_at": datetime.now(timezone.utc).isoformat(),
    }
    (out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
    content = [{"type": "text", "text": condition["prompt"]}]
    for number, path in enumerate(images, 1):
        content.extend([
            {"type": "text", "text": "Image " + str(number)},
            {"type": "image", "source": {
                "type": "base64", "media_type": mimetypes.guess_type(path.name)[0],
                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            }},
        ])
    packet = {"type": "user", "message": {"role": "user", "content": content}}
    start = time.monotonic()
    print("Starting", ident, flush=True)
    try:
        timed_out = False
        # Write raw streams during inference so interruption does not erase evidence.
        with (out / "stdout.jsonl").open("w") as stdout, (out / "stderr.txt").open("w") as stderr:
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
                                  text=True, cwd=ROOT) as process:
                try:
                    process.communicate(json.dumps(packet) + "\n", timeout=protocol["timeout_seconds"])
                except subprocess.TimeoutExpired:
                    timed_out = True
                    process.kill()
                    process.communicate()
                exit_code = process.returncode
        if timed_out:
            result = {"status": "infrastructure_error", "reason": "CLI timeout"}
        else:
            result = final_result((out / "stdout.jsonl").read_text(), exit_code, protocol["model"])
        result["exit_code"] = exit_code
    except OSError as exc:
        result = {"status": "infrastructure_error", "reason": str(exc)}
    result.update({"id": ident, "elapsed_seconds": round(time.monotonic() - start, 3)})
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if result.get("answer") is not None:
        (out / "answer.txt").write_text(result["answer"] + "\n")
    print("Finished", ident, result["status"], flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--condition", action="append", help="Run only this condition (repeatable)")
    parser.add_argument("--repeats", type=int, help="Override repetitions; recorded in run metadata")
    parser.add_argument("--timeout-seconds", type=int, help="Override the process deadline; recorded in run metadata")
    parser.add_argument("--label", default="run")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    path = args.protocol.resolve()
    protocol = json.loads(path.read_text())
    if args.repeats is not None:
        protocol["repeats"] = args.repeats
    if args.timeout_seconds is not None:
        if args.timeout_seconds < 1:
            parser.error("Timeout must be positive")
        protocol["timeout_seconds"] = args.timeout_seconds
    conditions = [c for c in protocol["conditions"] if not args.condition or c["id"] in args.condition]
    if not conditions or protocol["repeats"] < 1:
        parser.error("Select at least one condition and one repetition")
    if args.condition and set(args.condition) - {c["id"] for c in conditions}:
        parser.error("Unknown condition")
    jobs = schedule_jobs(conditions, protocol["repeats"], protocol.get("schedule_seed"))
    for condition, _ in jobs:
        for name in condition["images"]:
            if not (ROOT / "inputs" / name).is_file():
                parser.error("Missing image: " + name)
    print(json.dumps({"calls": len(jobs), "model": protocol["model"], "effort": protocol["effort"],
                      "maximum_cli_budget_usd": len(jobs) * protocol["max_budget_usd_per_call"]}))
    if args.dry_run:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = ROOT / "results" / (stamp + "-" + args.label)
    run_dir.mkdir(parents=True)
    metadata = {
        "protocol_path": str(path.relative_to(ROOT)), "protocol_sha256": digest(path),
        "effective_protocol": protocol,
        "cli_version": subprocess.run(["claude", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
        "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "selected_conditions": [c["id"] for c in conditions],
        "dispatch_order": [c["id"] + "-" + str(n) for c, n in jobs],
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    results = []
    with ThreadPoolExecutor(max_workers=protocol["concurrency"]) as pool:
        futures = [pool.submit(run_one, protocol, c, n, run_dir) for c, n in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    summary = {
        "calls": len(results), "completed": sum(r["status"] == "completed" for r in results),
        "cli_reported_cost_usd": round(sum(r.get("cli_result", {}).get("total_cost_usd", 0) for r in results), 6),
        "calls_with_unreported_cost": sum("total_cost_usd" not in r.get("cli_result", {}) for r in results),
        "runs": [{"id": r["id"], "status": r["status"]} for r in sorted(results, key=lambda r: r["id"])],
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(str(run_dir))
    print(json.dumps(summary, indent=2))
    if summary["completed"] != len(jobs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
