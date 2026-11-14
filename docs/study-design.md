# Study design and current interpretation

The question is how a model selects and preserves the features that make a particular image recognisable when reconstructing it in three dimensions. A plausible head, power strip and cable loop can retain broad resemblance while changing the depicted attachment. The caricature analogy motivates this distinction: preserving generic category membership is different from preserving the features and relationships that distinguish this subject.

The primary target in this example is the strip's own plug seated in its receiving socket. This target follows the author's stated intended subject and our inspection of the reference. Relevant visual cues include the distinct plug body, the cable originating at the strip, the socket-bearing face, and the contours and overlaps where the plug returns. The study must examine the use of those cues. A model's statement of uncertainty does not establish that the reference lacks sufficient information.

## What the first round established

The model recognised the familiar self-plugging joke in all three reference descriptions. All three sculpture descriptions placed the cable end in the head beside the strip. All three comparisons treated that attachment as similar while noticing tears being relocated to the mouth. The same model can share an omission across generation and comparison, so agreement is not independent evidence of fidelity.

Two completed open reconstructions placed the plug in the neck/shoulder. Two completed reconstructions with an explicit socket instruction seated it on the strip's front face. The former used independent plug coordinates; the latter shared a coordinate frame between plug and receiving socket. All four scripts ran without geometry repairs. These observations do not identify the model's internal mechanism or the cause of the original author's run.

## Hypotheses still open

- The model may omit or incorrectly weight distinguishing visual cues while retaining the overall subject and silhouette.
- The cues may be recognised without becoming constraints in the geometric construction.
- An instruction to preserve and check distinguishing features may improve fidelity without supplying the specific target relationship.
- The model's descriptions and comparisons may repeat the generator's omission and therefore fail as independent checks.
- Occlusion and inferred depth may affect reconstruction, but source insufficiency has not been independently established.

These possibilities can coexist. The evidence does not establish a vision encoder defect or a broad absence of spatial understanding.

## Second round: a general fidelity check

The new cohort repeats the original open reconstruction prompt alongside a condition adding only general instructions to identify distinguishing features, trace connections and check their preservation. It does not name a plug, socket, strip, head, expected error or expected repair. The image, system prompt, output schema, exact model, effort and tool access are otherwise the same.

There are two fresh sessions per condition, dispatched in a seeded shuffled order with two concurrent processes. The seed controls scheduling, not model sampling. A 600-second deadline applies to both conditions from the outset. A single fresh replacement per infrastructure failure is permitted under the protocol and must be retained separately; completed answers must not be rerun based on quality.

The primary observation is the depicted receiving point of the returning connector: a receiving socket on the strip, contact with the strip without a supported socket, contact with the head/neck, or disconnected/unclear. Source and fixed front/oblique renders are assessed together. Distinct plug shape, cable contact, preserved eye-origin tear streams and invented features are recorded separately. Mechanical fit, electricity, watertightness and printability are outside scope.

The assessor knows the conditions. This small cohort can reveal examples and counterexamples; it cannot establish a reliable treatment effect. More checking instructions also change prompt length and attention, so it does not isolate verbosity itself. No rendered feedback is provided to the generating session: this is a planning/code-check intervention, not a test of visual self-correction after rendering.

## Retention and continuation

Protocols are committed before collecting their responses. Historical protocols and raw answers are preserved, including assumptions later corrected in the current assessment. All attempts, failures, scripts, views and Blender scenes remain local and tracked by the existing Git repository. The integrity checker validates study-specific provenance, run completeness and retained-source hashes; normal Git commits retain the work.

`STUDY-STATE.json` records the current phase, relevant protocol and next action. Check it and existing run directories before starting more calls. Continue from retained results rather than repeating completed work.
