# Wojak visual relationship investigation

Targeted probes of Claude Fable 5.2's interpretation and reconstruction of a drawing in which a power strip's own plug occupies one of its sockets. The published sculpture appears to put the cable end into the head beside the strip. The experiment distinguishes perception of the reference, perception of the sculpture, and detection of the difference.

This is a study of one example. It does not reproduce the original benchmark's unpublished prompt or agent workflow, and cannot establish a proprietary architectural cause or a model-wide failure rate.

The current research question and hypotheses are retained in [the study design](docs/study-design.md). [STUDY-STATE.json](STUDY-STATE.json) records the active phase and continuation point. All study material belongs in this existing Git repository; normal commits are the retention mechanism.

**Current findings:** explicit attachment instructions produced the depicted connection in two replicas, but those models still place prongs inside solid plastic. A general fidelity-check prompt did not produce a seated receiving socket in either of two new trials. Two text-only controls with explicit cavity dimensions do construct actual clear receptacles. These are distinct observations about visual relationships, volumetric geometry and available construction capability. Model-reported uncertainty does not establish insufficient grounding in the drawing.

## Inputs and provenance

`inputs/provenance.json` records the supplied screenshot, its literal caption-free drawing crop, and two renders published by the [benchmark](https://wojak-bench.dev.pion.dev/). The original post's text and model attribution are excluded from every model input. Image hashes are recorded again per request.

[Contextual source snapshots](evidence/README.md) retain the publisher's intended subject, reported revision history and author-post context separately from model inputs, with retrieval times and hashes. The original prompt and modelling trace remain unavailable.

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

The runner now writes raw streams to disk during inference, retaining progress even if the host is interrupted. To check the retained study without making model calls:

```sh
/usr/bin/python3 scripts/verify_study.py
git fsck --full
```

During an active collection or before all completed scripts have been rendered, use `scripts/verify_study.py --allow-active` to report the remaining work separately from integrity errors.

The first study has three conditions with three sessions each: reference alone, sculpture alone, and comparison. Assessment is manual and must retain qualifications and contradictory evidence. The open descriptions do not name the expected objects or failure. The comparison explicitly asks about connections and therefore provides an attentional cue.

## Perception observations

The main series completed nine calls with the requested model and no infrastructure failures. The image-ingestion pilot is retained separately. Manual assessment of every complete answer is in [perception-assessment.json](results/perception-assessment.json); raw answers are under [the main run](results/20261114T170133545682Z-perception).

| Condition | Observation in these three sessions |
| --- | --- |
| Reference alone | All infer the self-plugging joke; all qualify the precise connection as ambiguous. |
| Sculpture alone | All describe the cable end entering the head beside the strip; none unconditionally asserts literal socket insertion. |
| Both together | All treat the attachment as similar; none independently identifies the author's intended connection error. All notice the relocation of tears to mouth drips. |

These are observations about the model's responses. The sculpture-only responses identify the relevant attachment, while the comparison responses regard the drawing as compatible with it. Their agreement is not an independent judgement of reference fidelity: the same model may omit the same distinguishing cues in description, construction and comparison. The observations cannot establish source ambiguity or identify the cause of the original generation failure.

## Reconstruction follow-up

[The follow-up protocol](protocol/reconstruction.json) compares two open reconstruction sessions with two sessions supplying an explicit plug-in-own-socket constraint. It was committed after reading the image-ingestion pilot and before collecting reconstruction answers. The generator returns Blender Python without tools or rendered feedback; source and fixed front/oblique renders will be assessed together. This tests a restricted open-loop workflow rather than the original unknown modelling workflow.

The second open call exceeded the original 300-second process deadline while still reporting thinking progress. A [recovery policy](protocol/timeout-recovery-policy.json) was committed before the explicit-condition outcomes were known: one fresh replacement per timed-out call, with the same inputs and settings and a 600-second process deadline. Both attempts are retained; timeouts are not geometric failures and their unreported costs are not counted as zero.

All four completed scripts executed in Blender 5.2.1 and were inspected in both views without geometry repairs. Two initial calls timed out; their fresh replacements both completed. The last replacement took 409 seconds, confirming that the original process deadline could exclude a valid response.

| Condition | Completed scenes | Depicted attachment | Inspect an oblique render |
| --- | --- | --- | --- |
| Open reconstruction | 2 | Both enter the neck/shoulder beside the strip | [Original call](results/20261114T170306703685Z-reconstruction/reconstruct_open-1/geometry/oblique.png), [replacement](results/20261114T171043643045Z-open-timeout-replacement/reconstruct_open-1/geometry/oblique.png) |
| Explicit socket constraint | 2 | Both seat the plug on the lowest front socket | [Original call](results/20261114T170306703685Z-reconstruction/reconstruct_explicit-2/geometry/oblique.png), [replacement](results/20261114T171224010444Z-explicit-timeout-replacement-1/reconstruct_explicit-1/geometry/oblique.png) |

The [complete reconstruction assessment](results/reconstruction-assessment.json) records source evidence, view inspection and exclusions. Socket success means the depicted attachment, not mechanical mating or electrical function. The assessor knew the conditions.

The implementation difference is concrete. The open scripts place the plug using independent coordinates near the neck; one explicitly maps estimated image pixels to world X/Z. The constrained scripts derive both the plug and receiving socket from the same local frame. Their descriptions say they moved the plug from the head to satisfy the extra instruction. This establishes the generated placements and the models' accounts of them. It does not establish that the reference required additional information: overlooked or poorly integrated visual clues remain a possible explanation.

## Interpretation and limits

The pilot separates recognising the familiar self-plugging joke, observing a particular attachment, and constructing an assembly. The sculpture-only descriptions correctly locate the cable end beside the strip. The comparisons do not identify that location as a change from the drawing. The open generations then choose neck/shoulder insertion, while the explicit instruction changes the choice and its implementation. A shared omission across these tasks could produce that pattern; model-reported uncertainty is not evidence that the source itself is insufficient.

The drawing supplies concrete grounding cues: a distinct plug body at the cable's end, a cord originating at the strip, the socket-bearing face, and contours and overlaps at the returning plug. Their omission or incorrect weighting must be investigated before attributing failure to source ambiguity. The experiment has not independently adjudicated whether those cues suffice to recover the intended attachment. The initial protocols' references to an ambiguous drawing are assumptions, not established findings; the protocols and raw responses remain unchanged.

Fidelity also requires selecting the right features. A caricature can preserve a person's identity through exaggerated distinguishing features, while a detailed generic face can lose that identity. Here the analogous requirement is to preserve the particular attachment relationship, not merely a recognisable head, strip and cable loop. Freedom to choose unseen depth or simplify a surface does not by itself justify changing that relationship. A useful assessment should identify which distinguishing features and relationships are retained, omitted or invented, and test whether the model's comparison shares the generator's omissions.

The evidence supports studying visual cue use, fidelity choices and explicit relation enforcement. It does not isolate a vision encoder defect, establish an absence of spatial understanding, or show that the original benchmark harness used the same process. Because the explicit condition supplies an interpretation, makes the relation salient and specifies a constraint, its apparent benefit cannot distinguish their contributions. A stronger next study would independently establish the relevant visual cues and attachment relationships, then test their retention under changes in style, detail and viewpoint.

The first round contains nine main perception answers, four completed reconstruction answers, one separately retained image-ingestion pilot, and two retained process timeouts. [Accounting](results/accounting.json) now covers all rounds and distinguishes reported list-price equivalents from the unknown costs of aborted calls. The initial text availability checks are outside the experimental dataset.

## General fidelity control

[The second-round protocol](protocol/fidelity-check.json) adds only a general requirement to identify distinguishing features, trace connections and check their preservation. It supplies no object-specific attachment answer. Two fresh baseline calls ran alongside two fresh general-check calls, using the original baseline prompt unchanged and a seeded shuffled dispatch order. Both conditions used a 600-second deadline; all four completed and executed without geometry repairs.

Each condition produced one neck-contact case and one strip-contact case without a receiving socket. Neither general-check trial produced a seated receiving socket. [The full assessment](results/fidelity-check-assessment.json) preserves those distinctions and the evidence from both views. This is an observation about this wording and small cohort, not evidence that checking prompts cannot help.

## Receptacle geometry and functional control

The [independent mesh audit](results/receptacle-audit.json) measures the retained metal prongs intersecting the plastic strip body. All six prongs in the two earlier attachment-success replicas collide with solid plastic: about 73.1% of prong volume in one scene and 68.8% in the other. Source inspection shows positive surface marks over solid housings, not receiving voids. The checker passes known solid, shallow-recess and genuinely hollow calibration cases.

The [text-only control](protocol/receptacle-generation.json) specifies a block, actual blind cavities and matching prongs without an image. Both responses construct real cavities directly in a closed manifold mesh. Both pass the [registered volume, bounds and collision checks](results/receptacle-control-audit.json), with zero prong/plastic overlap. [The assessment](results/receptacle-assessment.json) separates what this establishes from the original visual task.

For inspection, compare the [solid geometry beneath a replica's plug](results/20261114T170306703685Z-reconstruction/reconstruct_explicit-2/geometry/under-plug.png) with the [actual openings in a text control](results/20261114T181143378123Z-receptacle-construction/construct_receptacle-1/geometry/open-receptacles.png). These derived views hide the named occluding parts only; their metadata records the visibility changes, and the retained scene files remain unchanged.

The prior sculpture prompt allowed overlapping solids and did not require mechanical mating. This audit adds an independent functional criterion; it preserves the earlier attachment scores. It demonstrates available cavity-construction capability under an explicit specification, while leaving the failure to retain that property from an image to investigate. The original author's print mesh remains unavailable.

There are now 22 retained experimental attempts: 20 completed answers and two earlier process timeouts, with ten executed scene bundles. The next planned comparison adds a functional-geometry requirement to the image reconstruction task without supplying the plug placement. No new cohort should be started without first checking the state and committing its protocol.

## Availability

The local Claude Code login needed renewal. A text-only availability check subsequently returned `PROBE_OK` from `claude-fable-5-2` via the first-party provider. No interpretation result is implied by that check.
