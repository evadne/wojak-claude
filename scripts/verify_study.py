"""Check the study's retained evidence and provenance without making model calls."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def audit(root, allow_active=False):
    errors = []
    pending = []
    counts = Counter()

    def require(test, message):
        if not test:
            errors.append(message)

    def load(path):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            errors.append(str(path.relative_to(root)) + ": " + str(exc))
            return {}

    def verify_hash(path, expected):
        if not path.is_file():
            errors.append("Missing file: " + str(path.relative_to(root)))
        else:
            require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                    "Hash mismatch: " + str(path.relative_to(root)))

    for name, source in load(root / "inputs/provenance.json").items():
        verify_hash(root / "inputs" / name, source["sha256"])
    for source_list in (root / "evidence").glob("*/sources.json"):
        for source in load(source_list):
            verify_hash(root / source["file"], source["sha256"])
            if "text_file" in source:
                verify_hash(root / source["text_file"], source["text_sha256"])
    commits = set()
    for metadata_path in sorted((root / "results").glob("*/metadata.json")):
        run = metadata_path.parent
        metadata = load(metadata_path)
        protocol = metadata.get("effective_protocol", {})
        if not protocol:
            continue
        counts["runs"] += 1
        commits.add(metadata["git_commit"])
        verify_hash(root / metadata["protocol_path"], metadata["protocol_sha256"])
        conditions = {c["id"]: c for c in protocol["conditions"]}
        selected = metadata["selected_conditions"]
        expected = {c + "-" + str(n) for c in selected for n in range(1, protocol["repeats"] + 1)}
        results = []
        for ident in sorted(expected):
            call = run / ident
            prefix = str(call.relative_to(root))
            request_path = call / "request.json"
            result_path = call / "result.json"
            if not request_path.is_file() or not result_path.is_file():
                (pending if allow_active else errors).append("Unfinished call: " + prefix)
                counts["unfinished_calls"] += 1
                continue
            request = load(request_path)
            result = load(result_path)
            if not request or not result:
                continue
            condition = conditions[request["condition"]]
            require(request["prompt"] == condition["prompt"], "Prompt mismatch: " + prefix)
            require(request["system_prompt"] == protocol["system_prompt"], "System prompt mismatch: " + prefix)
            require([i["path"] for i in request["images"]] == ["inputs/" + n for n in condition["images"]],
                    "Image order mismatch: " + prefix)
            for asset in request["images"]:
                verify_hash(root / asset["path"], asset["sha256"])
            for filename in ["stdout.jsonl", "stderr.txt"]:
                require((call / filename).is_file(), "Missing stream: " + prefix + "/" + filename)
            results.append(result)
            counts["attempts"] += 1
            if result["status"] != "completed":
                counts["infrastructure_incomplete"] += 1
                continue
            counts["completed"] += 1
            require((call / "answer.txt").is_file(), "Missing extracted answer: " + prefix)
            if (call / "answer.txt").is_file():
                require((call / "answer.txt").read_text() == result["answer"] + "\n", "Answer mismatch: " + prefix)
            events = []
            if (call / "stdout.jsonl").is_file():
                for line in (call / "stdout.jsonl").read_text().splitlines():
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        errors.append("Malformed completed stream: " + prefix)
            initial = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
            final = next((e for e in reversed(events) if e.get("type") == "result"), {})
            require(initial.get("model") == protocol["model"], "Wrong initial model: " + prefix)
            require(not initial.get("tools") and not initial.get("mcp_servers"), "Unexpected tools: " + prefix)
            require(final == result["cli_result"], "Raw/final result mismatch: " + prefix)
            require(set(final.get("modelUsage", {})) == {protocol["model"]}, "Wrong final model: " + prefix)
            require(all(v.get("provider") == "firstParty" for v in final.get("modelUsage", {}).values()),
                    "Unexpected provider: " + prefix)
            answer = result.get("parsed_answer")
            if not isinstance(answer, dict) or "script" not in answer:
                continue
            geometry = call / "geometry"
            source = geometry / "generated.py"
            if not (geometry / "render-metadata.json").is_file():
                failure = geometry / "execution-result.json"
                if failure.is_file() and load(failure).get("status") in {"failed", "source_review_failed"}:
                    counts["render_failures"] += 1
                    require(source.is_file() and (geometry / "render.log").is_file(), "Incomplete execution failure: " + prefix)
                else:
                    (pending if allow_active else errors).append("Unfinished geometry inspection: " + prefix)
                if source.is_file():
                    require(source.read_text() == answer["script"], "Changed generated source: " + prefix)
                continue
            render = load(geometry / "render-metadata.json")
            verify_hash(source, render.get("generated_source_sha256"))
            if source.is_file():
                require(source.read_text() == answer["script"], "Changed generated source: " + prefix)
            for name in ["front.png", "oblique.png"]:
                path = geometry / name
                require(path.is_file() and path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Missing/invalid view: " + prefix + "/" + name)
            scene = geometry / "scene.blend"
            require(scene.is_file() and scene.stat().st_size > 12, "Missing Blender scene: " + prefix)
            counts["retained_scenes"] += 1
        summary_path = run / "summary.json"
        if summary_path.is_file():
            summary = load(summary_path)
            require(summary.get("calls") == len(expected) == len(results), "Call count mismatch: " + run.name)
            require(summary.get("completed") == sum(r["status"] == "completed" for r in results), "Completion count mismatch: " + run.name)
        else:
            (pending if allow_active else errors).append("Unfinished run summary: " + run.name)
    for commit in commits:
        found = subprocess.run(["git", "cat-file", "-e", commit + "^{commit}"], cwd=root, capture_output=True)
        require(found.returncode == 0, "Missing historical code commit: " + commit)
    protocols = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / "protocol").glob("*.json")}
    history_hashes = {}

    def historical_script_hashes(relative):
        if relative not in history_hashes:
            history = subprocess.run(["git", "log", "--format=%H", "--", relative], cwd=root, capture_output=True, text=True, check=True)
            hashes = set()
            for commit in history.stdout.splitlines():
                content = subprocess.run(["git", "show", commit + ":" + relative], cwd=root, capture_output=True, check=True).stdout
                hashes.add(hashlib.sha256(content).hexdigest())
            history_hashes[relative] = hashes
        return history_hashes[relative]

    for report_path in (root / "results").glob("*audit.json"):
        report = load(report_path)
        if "calibration" not in report:
            continue
        require(report.get("protocol_sha256") in protocols, "Missing audit protocol: " + report_path.name)
        require(report.get("script_sha256") in historical_script_hashes("scripts/audit_receptacles.py"), "Missing audit code version: " + report_path.name)
        require(all(c.get("passed") for c in report["calibration"]), "Audit calibration failed: " + report_path.name)
        for case in report["cases"]:
            verify_hash(root / case["scene"], case["scene_sha256"])
            require(case.get("source_geometry_changed") is False, "Audit modified retained geometry: " + case["id"])
        counts["calibrated_audit_reports"] += 1
    for metadata_path in (root / "results").glob("*/*/geometry/*.json"):
        metadata = load(metadata_path)
        if "hidden_objects" not in metadata:
            continue
        verify_hash(root / metadata["scene"], metadata["scene_sha256"])
        require(metadata.get("script_sha256") in historical_script_hashes("scripts/render_inspection.py"), "Missing inspection code version: " + str(metadata_path))
        require(metadata.get("geometry_changed") is False and metadata.get("retained_scene_saved") is False,
                "Inspection changed retained scene: " + str(metadata_path))
        image = metadata_path.with_suffix(".png")
        require(image.is_file() and image.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Missing inspection view: " + str(image))
        counts["derived_inspection_views"] += 1
    return {"valid": not errors, "counts": dict(counts), "pending": pending, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-active", action="store_true", help="List unfinished calls/renders without treating them as lost evidence")
    args = parser.parse_args()
    report = audit(ROOT, args.allow_active)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
