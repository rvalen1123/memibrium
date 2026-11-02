# docs/archive — policy and log

Last confirmed against: aaa5660 (2026-11-02)

## Policy

A file is moved here (with `git mv`, so history follows it) only when one of these holds:

1. A newer document, or the code on `main`, explicitly replaces it (the newer file names it, or the file's own text says it is superseded or withdrawn).
2. It is an exact duplicate of another tracked file.

A file that is merely old, or whose numbers are known to be stale, is **not** archived; it stays where it is and is marked `historical` in the relevant index (`docs/README.md` or `docs/eval/README.md`). Evaluation records under `docs/eval/**` are moved to `docs/eval/archive/` rather than here, and only under rule 1 or 2, because the preregistration chain depends on their paths.

When you move a file: grep for inbound links (`grep -rn "<name>" --include=*.md --include=*.py .`), fix them, and add a row to the log below.

## Log

| Date | File | Moved to | Reason |
|---|---|---|---|
| 2026-11-02 | — | — | MED-242 docs pass: every document was reviewed newest-first against `main` at `aaa5660`. No file met rule 1 or rule 2, so nothing was archived. `skills/crystallization-memory/SKILL.md` is a self-declared redirect stub but is referenced by the Dockerfile (`COPY skills/`) and by installs, so it stays and is marked `historical`. `docs/benchmarks.md` carries its own inline corrections and is marked `historical`. |
