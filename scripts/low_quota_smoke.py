"""Low-quota staged smoke tests for PaperOrchestra.

Run from repository root. No calls are made in preflight mode.
Set PAPER_ORCHESTRA_MAX_API_CALLS and PAPER_ORCHESTRA_REQUIRE_OFFLINE before
calling any agent. The two agent stages are deliberately separate processes.
"""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["preflight", "outline", "literature"])
    parser.add_argument("--raw", default="test_pgj/raw_materials")
    parser.add_argument("--template", default="templates/cvpr2025")
    parser.add_argument("--work", default="test_pgj_smoke")
    parser.add_argument("--model", default="gemini-4-hydrogen")
    parser.add_argument("--references", help="Path to a manually verified JSON reference list")
    args = parser.parse_args()

    raw, template, work = Path(args.raw), Path(args.template), Path(args.work)
    needed = [raw / "idea_sparse.md", raw / "experimental_log.md",
              template / "template.tex", template / "guidelines.md"]
    missing = [str(p) for p in needed if not p.is_file() or not p.stat().st_size]
    if missing:
        parser.error("Missing or empty input(s): " + ", ".join(missing))
    if args.stage == "preflight":
        print("PASS: all four non-empty inputs exist. No API calls made.")
        return

    if os.getenv("PAPER_ORCHESTRA_REQUIRE_OFFLINE") != "1":
        parser.error("Set PAPER_ORCHESTRA_REQUIRE_OFFLINE=1 to prevent paid grounding.")
    try:
        budget = int(os.getenv("PAPER_ORCHESTRA_MAX_API_CALLS", "0"))
    except ValueError:
        parser.error("PAPER_ORCHESTRA_MAX_API_CALLS must be an integer")
    if not (1 <= budget <= 3):
        parser.error("For smoke tests set PAPER_ORCHESTRA_MAX_API_CALLS between 1 and 3")
    work.mkdir(parents=True, exist_ok=True)
    outline_path = work / "outline.json"

    if args.stage == "outline":
        from methods.agents.outline_agent import OutlineAgent
        OutlineAgent(model_name=args.model, cutoff_date="2026-11").run(
            idea_file=str(needed[0]), experimental_log_file=str(needed[1]),
            latex_template_file=str(needed[2]),
            conference_guidelines_file=str(needed[3]),
            output_filepath=str(outline_path))
        print("PASS: outline stage returned.")
        return

    if not outline_path.is_file():
        parser.error(f"Outline missing: {outline_path}; run outline stage first.")
    if not args.references:
        parser.error("--references is required for offline literature stage.")
    ref_path = Path(args.references).resolve()
    with ref_path.open(encoding="utf-8") as handle:
        refs = json.load(handle)
    if not isinstance(refs, list) or not refs or not all(
        isinstance(p, dict) and p.get("verified") is True for p in refs
    ):
        parser.error("Reference list must be nonempty and each record verified=true.")
    os.environ["PAPER_ORCHESTRA_VERIFIED_REFERENCES"] = str(ref_path)
    from methods.agents.literature_review_agent import HybridLiteratureAgent
    HybridLiteratureAgent(
        idea_path=str(needed[0]), experimental_log_path=str(needed[1]),
        latex_template_path=str(needed[2]),
        conference_guidelines_path=str(needed[3]),
        output_dir=str(work / "literature_agent_output"),
        model_name=args.model, max_workers=1,
    ).run(outline_path=str(outline_path), cutoff_date="2026-11")
    print("PASS: offline literature stage returned.")


if __name__ == "__main__":
    main()
