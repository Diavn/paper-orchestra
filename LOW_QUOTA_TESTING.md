# Low-quota test protocol (20 November 2026)

This experimental branch does **not** change `main`. It is intended for
PaperOrchestra on GitHub Codespaces with `gemini-4-hydrogen`.

## Safety conditions

- Stop any previous running `paper_writing_cli.py` process.
- Check the Google AI Studio **project's** free-tier status, usage and rate limits.
  A model's free-tier eligibility does not guarantee remaining quota.
- This workflow caps **attempted Gemini requests per Python process**, not
  tokens, monetary cost, concurrent external services, or all tools.
- Never commit real API keys or unpublished personal research data.
- Do not use the unmodified full pipeline yet: it can make multiple calls,
  including in reflection, and the free tier may reject the requests.

## 1. Switch to the branch

In Codespaces, first preserve local edits and untracked files (especially
`test_pgj/`). Check `git status`. If a working tree has modifications
overlapping the branch, commit/stash them safely before switching.

```bash
git fetch origin fix/low-quota-20261120
git switch --track origin/fix/low-quota-20261120
```

If the local branch already exists, use `git switch fix/low-quota-20261120`
instead. Do not discard local changes.

## 2. Zero-API preflight

```bash
python scripts/low_quota_smoke.py preflight
python -m py_compile utils/gemini_utils.py methods/agents/literature_review_agent.py methods/paper_writer.py scripts/low_quota_smoke.py
```

## 3. Outline-only smoke test (up to 1 attempted Gemini API call)

Only after checking API quotas:

```bash
export PAPER_ORCHESTRA_REQUIRE_OFFLINE=1
export PAPER_ORCHESTRA_MAX_API_CALLS=1
python scripts/low_quota_smoke.py outline
```

Output: `test_pgj_smoke/outline.json`. If Google responds HTTP 429, the code
stops rather than retrying the same failed request.

## 4. Curated-literature-only smoke test

Prepare a local JSON file of independently verified scholarly records.
The script rejects empty lists or records without `verified: true`.
Each record must have the fields below; values are placeholders only:

```json
[
  {
    "verified": true,
    "citation_key": "VerifiedAuthor2026",
    "title": "REPLACE WITH VERIFIED TITLE",
    "authors": ["REPLACE WITH VERIFIED AUTHOR"],
    "venue": "REPLACE WITH VERIFIED JOURNAL",
    "year": 2026,
    "abstract": "REPLACE WITH VERIFIED ABSTRACT OR CLEAR SUMMARY",
    "citation_count": 0,
    "found_in_section": "Introduction",
    "reason": "Verified source relevant to the research question",
    "journal": "REPLACE WITH VERIFIED JOURNAL"
  }
]
```

Do **not** treat the placeholders as references. Verify each source using
publisher pages, DOI records, or the actual full text first. Do not guess
citation counts. On free-tier testing, only use material allowed to be
processed by the API.

Save as `test_pgj/verified_references.json`, then:

```bash
export PAPER_ORCHESTRA_REQUIRE_OFFLINE=1
export PAPER_ORCHESTRA_MAX_API_CALLS=1
python scripts/low_quota_smoke.py literature --references test_pgj/verified_references.json
```

This bypasses Google Search candidate discovery and Semantic Scholar
enrichment. The literature synthesis still needs **one** model request.
The writer will not independently validate bibliographic claims.

## Implementation details

- `utils/gemini_utils.py`: process-wide attempted-request counter with a
  lock, immediate stop on HTTP 429, 400, 401, 403 or 404 in the text API path;
  avoids printing full API error payloads.
- `methods/agents/literature_review_agent.py`: use
  `self.model_name` rather than the old hard-coded model; support optional
  curated reference JSON via `PAPER_ORCHESTRA_VERIFIED_REFERENCES`.
- `methods/paper_writer.py`: reduce whole-pipeline reruns to one when the
  low-quota environment variables are active.

## Unverified

Static source inspection alone does not establish successful imports,
runtime behavior, output quality, PDF compilation, or cost containment.
Run preflight first, then one agent at a time. Do not call the full pipeline
until both stages have been observed to succeed and quotas are sufficient.
