# Wojak visual relationship investigation

Targeted probes of Claude Fable 5.2's interpretation and reconstruction of a drawing in which a power strip's own plug occupies one of its sockets. The published sculpture appears to put the cable end into the head beside the strip. The experiment distinguishes perception of the reference, perception of the sculpture, and detection of the difference.

This is a study of one example. It does not reproduce the original benchmark's unpublished prompt or agent workflow, and cannot establish a proprietary architectural cause or a model-wide failure rate.

## Inputs and provenance

`inputs/provenance.json` records the supplied screenshot, its literal caption-free drawing crop, and two renders published by the [benchmark](https://wojak-bench.dev.pion.dev/). The original post's text and model attribution are excluded from every model input. Image hashes are recorded again per request.

```sh
/usr/bin/python3 scripts/prepare_inputs.py /path/to/screenshot.jpg
```

Input preparation uses macOS `sips` for a literal crop, not a generative edit. The crop coordinates are specific to the supplied 900 × 1280 screenshot. Review the crop before using it.

## Protocol and execution

The prompts, repetitions, settings and scoring criteria are committed in `protocol/perception.json` before collecting experimental answers. Each call uses a fresh, non-persistent Claude Code session, the exact model ID, high effort, a fixed system prompt, safe mode and no tools or MCP servers. The subscription login is used; credentials are never saved here.

```sh
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 scripts/probe.py protocol/perception.json --dry-run
/usr/bin/python3 scripts/probe.py protocol/perception.json --label perception
```

Each result directory retains the effective protocol, committed code revision, image hashes, verbatim prompts, CLI command, raw output stream, standard error, complete CLI result and extracted answer. Authentication errors, timeouts and unexpected model IDs invalidate a call; they are not counted as model mistakes. CLI cost figures are list-price equivalents and are not a statement of additional charges to a subscription.

The first study has three conditions with three sessions each: reference alone, sculpture alone, and comparison. Assessment is manual and must retain qualifications and contradictory evidence. The open descriptions do not name the expected objects or failure. The comparison explicitly asks about connections and therefore provides an attentional cue.

## Initial status

The local Claude Code login needed renewal. A text-only availability check subsequently returned `PROBE_OK` from `claude-fable-5-2` via the first-party provider. No interpretation result is implied by that check.
