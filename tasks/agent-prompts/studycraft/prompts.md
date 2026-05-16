StudyCraft agent — curated example prompts

1. Fixing detector edge cases

- "Investigate and fix `src/studycraft/detector.py` so it correctly detects Roman numerals
  in chapter headings. Draft a unit test that reproduces the failing case."

2. Small refactor + test

- "Refactor `src/studycraft/loader.py` helper `normalize_path()` to be Windows-safe,
  write two unit tests, and provide the patch. Do not modify `engine.py`."

3. Audio generation troubleshooting

- "Help debug audio generation failures when using KittenTTS. Locate likely failure
  points in `src/studycraft/tts_engines.py` and propose a minimal fix + test."

4. Export formatting tweak

- "Adjust `src/studycraft/export.py` so Markdown exports include theme metadata frontmatter.
  Add a small test and example output."

5. Release prep

- "Draft a CHANGELOG entry and bump version in `pyproject.toml` to 0.9.4; produce the
  exact patch but do not create the git tag or push."

6. Web UI SSE check

- "Add a unit test for the SSE endpoint in `src/studycraft/web.py` that validates
  JSON payload shape without starting an external server."
