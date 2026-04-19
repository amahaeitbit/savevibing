# SafeVibing

SafeVibing is a web-based repository review tool for AI-generated and fast-moving codebases. It helps founders, team leads, and senior engineers understand what a repository does, where the business logic lives, what is risky, and what VibeCoder should fix next.

## What It Does

SafeVibing reviews a local repository path or a public GitHub repository URL and produces a clean browser report with:

- audience-aware tabs for founders and technical leads
- repository-level summary, risks, and remediation priorities
- per-file technical reviews with code smells and complexity notes
- founder/business analysis separated from coding analysis
- secure-by-design, safe-defaults, and security-risk metrics
- repo-wide and per-file VibeCoder remediation prompts
- exported HTML review output for sharing

## Who It Is For

- founders who need a high-level trust and business narrative
- team leads and senior engineers who need technical depth
- hackathon teams who need a fast demo artifact
- AI-assisted coding teams who want a review layer before shipping

## Quick Start

### Requirements

- Python 3.10 or newer
- Git
- Internet access if you want to review public GitHub repositories

### Setup

```bash
git clone https://github.com/amahaeitbit/savevibing
cd savevibing
python3 -m venv .venv
source .venv/bin/activate
```

### Run The Web App

```bash
python main.py --serve --host 127.0.0.1 --port 8000 --no-browser
```

Then open:

```text
http://127.0.0.1:8000
```

If `8000` is busy, use another port:

```bash
python main.py --serve --host 127.0.0.1 --port 8001 --no-browser
```

### Run Tests

```bash
python -m unittest -q
```

## How The Review Works

1. Choose a local path or public GitHub repository.
2. Select the audience:
   founder, team lead or senior engineer, engineering team, or balanced.
3. Set review depth, focus mode, file cap, and optional include or exclude patterns.
4. Run the review in the browser.
5. Read the audience-specific tabs and copy the VibeCoder remediation prompts.

## Main Report Sections

- `Summary`: overall repo status, findings, metrics, and review posture
- `Founder`: business narrative, market position, risks, and founder questions
- `Technical`: what matters now, priority files, and repository focus queue
- `Risks`: security and governance risk analysis
- `Fixes`: repo-wide and per-file VibeCoder prompts
- `Files`: detailed per-file reviews for technical audiences

## Metrics Included

- security risk score
- secure-by-design score
- safe defaults score
- maintainability index
- cyclomatic complexity
- cognitive complexity
- duplication risk
- testability score
- explainability completeness

## Demo Assets

The repository includes exported demo assets in `review/safevibing_review`:

- `safevibing_review.html`
- `demo-video-2026-04-19.mov`

These are useful for hackathon demos, async sharing, and GitHub-based review.

## Notes

- Public GitHub repository review uses `git clone` under the hood.
- Local reviews inspect supported code files and skip virtualenv, git, cache, and build directories.
- The HTML report can be exported and committed as a deliverable artifact.
