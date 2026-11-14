# Contextual source evidence

These source snapshots are retained for interpreting the study. They were fetched after the first experimental round and are not model inputs. The model sessions receive only the caption-free drawing crop or the published sculpture renders identified in each request.

- `2026-11-14/benchmark-home.html` is the publisher's public benchmark page. It identifies WB-002 as a power-strip head whose cable is plugged back into its own outlet. It calls the shown object the third version and reports that the first two received feedback about the face. It does not disclose the full original prompt, code, revision trace or complete checking process.
- `2026-11-14/author-post-mirror.html` is a third-party mirror of the author's post. The user-supplied screenshot in `inputs/source-screenshot.jpg` also retains the post's failure caption. The original post URL is recorded in `sources.json`; the mirror is not represented as an independent primary source.
- `.txt` files are readable text extractions of the saved HTML. `sources.json` records URLs, retrieval times, source types and byte hashes. A later snapshot cannot prove that every detail of a page was identical at the earlier experimental time.

The publisher's statement helps establish the intended subject. The visual cues still need to be assessed from the drawing itself. Neither an author's caption nor model agreement independently demonstrates which visual cues a model used or omitted.
