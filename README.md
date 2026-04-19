# SafeVibing

SafeVibing is a local web app for reviewing local or public GitHub repositories with a senior-engineering lens. It surfaces security issues, code smells, complexity pressure, business-logic hints, safe-defaults posture, and VibeCoder remediation prompts.

## Requirements

- Python 3.10 or newer
- Git
- Internet access if you want to review public GitHub repositories

## Setup

```bash
git clone https://github.com/amahaeitbit/savevibing
cd savevibing
python3 -m venv .venv
source .venv/bin/activate
```

## Run The Web App

```bash
python main.py --serve --host 127.0.0.1 --port 8000 --no-browser
```

Open this in your browser:

```text
http://127.0.0.1:8000
```

If port `8000` is busy, use another port:

```bash
python main.py --serve --host 127.0.0.1 --port 8001 --no-browser
```

## Run Tests

```bash
python -m unittest -q
```

## Use It

The browser UI supports:

- local repository path reviews
- public GitHub repository URL reviews
- review depth, focus, and file cap controls
- per-file senior-engineer summaries
- secure-by-design and safe-defaults metrics
- repo-wide and per-file VibeCoder remediation prompts

## Notes

- Public GitHub repo review uses `git clone` under the hood.
- Local reviews only inspect supported code files and ignore virtualenv, git, cache, and build directories.
