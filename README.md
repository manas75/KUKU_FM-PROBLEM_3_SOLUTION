# NameLock - name & terminology consistency check for translated/adapted microdrama scripts (Problem 3)
Who it's for: a localisation QA reviewer checking AI-translated episodes (same show, many languages) before release.
Input: folder of .txt scripts per language/show ("SPEAKER: dialogue" lines + scene headings). Optional glossary.json (canonical term -> banned variants; "distinct" = names that are different characters).
Run (no key needed): python namelock.py inputs --glossary glossary.json --planted planted.json --tag run
Output: raw_outputs/<tag>.md (readable list) and <tag>_issues.csv (for the reviewer). The tool flags, a human decides; it never edits scripts.
No model is required. A model can be added later to judge ambiguous cases (see doc); the optional model step is swappable via LLM_PROVIDER, LLM_MODEL, LLM_BASE_URL.
Inputs here are SYNTHETIC episodes written by the author with planted errors (planted.json) to measure recall; replace with real translated scripts.
