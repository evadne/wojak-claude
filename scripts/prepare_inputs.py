"""Preserve source bytes and prepare a literal, caption-free reference crop."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    target = ROOT / "inputs"
    target.mkdir(exist_ok=True)
    source = target / "source-screenshot.jpg"
    shutil.copyfile(args.source, source)
    # Coordinates are in the original 900 x 1280 screenshot, from its top left.
    subprocess.run([
        "/usr/bin/sips", "-s", "format", "png", "-c", "632", "402",
        "--cropOffset", "426", "484", str(source),
        "--out", str(target / "reference.png"),
    ], check=True, capture_output=True, text=True)
    sources = {
        "source-screenshot.jpg": {"source": "User-supplied screenshot"},
        "reference.png": {
            "source": "source-screenshot.jpg",
            "crop_xywh": [484, 426, 402, 632],
            "operation": "Literal pixel crop via macOS sips; PNG encoding; no generated edits",
        },
    }
    for suffix in ["front", "side"]:
        name = "model-" + suffix + ".jpg"
        url = "https://wojak-bench.dev.pion.dev/img/wb002-" + suffix + ".jpg"
        request = urllib.request.Request(url, headers={"User-Agent": "Wojak visual investigation"})
        with urllib.request.urlopen(request, timeout=30) as response:
            (target / name).write_bytes(response.read())
        sources[name] = {"source": url}
    for name, metadata in sources.items():
        metadata["sha256"] = hashlib.sha256((target / name).read_bytes()).hexdigest()
    (target / "provenance.json").write_text(json.dumps(sources, indent=2) + "\n")
    print("Prepared", ", ".join(sources))


if __name__ == "__main__":
    main()
