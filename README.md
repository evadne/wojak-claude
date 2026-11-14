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

## Perception observations

The main series completed nine calls with the requested model and no infrastructure failures. The image-ingestion pilot is retained separately. Manual assessment of every complete answer is in [perception-assessment.json](results/perception-assessment.json); raw answers are under [the main run](results/20261114T170133545682Z-perception).

| Condition | Observation in these three sessions |
| --- | --- |
| Reference alone | All infer the self-plugging joke; all qualify the precise connection as ambiguous. |
| Sculpture alone | All describe the cable end entering the head beside the strip; none unconditionally asserts literal socket insertion. |
| Both together | All treat the attachment as similar; none independently identifies the author's intended connection error. All notice the relocation of tears to mouth drips. |

This complicates a simple perception-failure account. The sculpture-only responses can identify the relevant attachment, while the comparison responses regard the drawing as compatible with it. The reference's intended meaning and its literal visible geometry must be scored separately. The observations cannot identify the cause of the original generation failure.

## Reconstruction follow-up

[The follow-up protocol](protocol/reconstruction.json) compares two open reconstruction sessions with two sessions supplying an explicit plug-in-own-socket constraint. It was committed after reading the image-ingestion pilot and before collecting reconstruction answers. The generator returns Blender Python without tools or rendered feedback; source and fixed front/oblique renders will be assessed together. This tests a restricted open-loop workflow rather than the original unknown modelling workflow.

The second open call exceeded the original 300-second process deadline while still reporting thinking progress. A [recovery policy](protocol/timeout-recovery-policy.json) was committed before the explicit-condition outcomes were known: one fresh replacement per timed-out call, with the same inputs and settings and a 600-second process deadline. Both attempts are retained; timeouts are not geometric failures and their unreported costs are not counted as zero.

## Availability

The local Claude Code login needed renewal. A text-only availability check subsequently returned `PROBE_OK` from `claude-fable-5-2` via the first-party provider. No interpretation result is implied by that check.
