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

The second round completed all four calls and executed every script unchanged. Each condition produced one neck-contact case and one strip-contact case lacking a receiving socket. This particular generic checking prompt therefore produced no seated receiving socket in either trial. The small result does not establish that general checking instructions cannot help.

## Separate axis: receptacle geometry

The geometric requirement of a socket is stronger than a dark mark with the expected outline: there must be empty volume that a prong can occupy. This axis was added after inspection of the visual reconstructions, rather than silently changing their original scoring criteria.

An independent Blender checker computes exact Boolean intersections between the retained prongs and plastic strip bodies. It is calibrated on a solid block, a shallow recess and a correctly hollow receptacle, with known collision volumes of 84, 60 and zero per test prong. The two retained visual replicas that passed the attachment criterion both have prong/plastic collisions; roughly 73.1% and 68.8% of each prong's volume intersects plastic in their respective scenes. Source inspection confirms solid housings and positive surface marks rather than receiving cavities. These are our retained generated meshes, not the original author's unavailable print mesh.

The original visual prompt permitted overlapping solids and excluded mechanical mating. The new check measures an additional property; it does not retroactively turn a previous attachment success into failure to follow that prompt.

## Third round: explicit text-only receptacles

Two fresh sessions construct the same fully specified block, two blind rectangular cavities and matching prongs without an image. Both scripts build actual cavities directly in closed mesh topology. Both execute unchanged and pass the independent collision, volume, bounds and object-count checks. This demonstrates available construction capability under a literal functional requirement, while leaving spontaneous retention of that property from a drawing unresolved.

The intervention is deliberately strong: exact dimensions and negative volume are supplied. It is a capability control, not a matched causal estimate against the image task. Clear final placement alone does not establish a complete insertion path or manufacturing suitability.

## Programme continuation

The next comparison should hold the drawing and reconstruction task fixed while adding a functional-geometry requirement alone, without specifying the intended plug placement. Assess attachment and empty receiving volume separately. Register that prompt and its criteria before collection, retain every result and use independent mesh checks alongside visual assessment.

Further priorities are to test whether rendered feedback catches errors that code-only checking misses, and to use unfamiliar assemblies with independently specified distinguishing features. The same model's approval of its own work must remain an observation to test, rather than ground truth. No additional cohorts are currently running; the local state records the completed rounds and the next design task.

## Retention and continuation

Protocols are committed before collecting their responses. Historical protocols and raw answers are preserved, including assumptions later corrected in the current assessment. All attempts, failures, scripts, views and Blender scenes remain local and tracked by the existing Git repository. The integrity checker validates study-specific provenance, run completeness and retained-source hashes; normal Git commits retain the work.

`STUDY-STATE.json` records the current phase, relevant protocol and next action. Check it and existing run directories before starting more calls. Continue from retained results rather than repeating completed work.
