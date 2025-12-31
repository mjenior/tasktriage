# Tasker

A CLI tool that analyzes handwritten task notes from a note-taking device using Claude AI to generate actionable GTD-based execution plans.

## Overview

Tasker bridges the gap between handwritten task capture and digital execution planning. Notes written on a note-taking device (e.g., reMarkable, Supernote) are synced to a mounted drive, where Tasker automatically detects and analyzes them using Claude AI via LangChain to:

- **Daily Analysis**: Transform categorized to-do lists into realistic single-day execution plans with time estimates, energy levels, and prioritized action steps
- **Weekly Analysis**: Aggregate daily analyses to identify patterns, diagnose execution breakdowns, and generate corrective planning strategies

## Features

- Automatic detection of the most recent unanalyzed notes file
- Configurable Claude model parameters via YAML
- GTD-based prioritization with workload guardrails (6-7 hours/day)
- Weekly rollup analysis of daily execution patterns
- Shell aliases for quick access

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [Task](https://taskfile.dev/) (optional, for task automation)
- Anthropic API key

## Installation

### Using Task and uv (recommended)

```bash
# Full first-time setup (creates venv, installs deps, copies .env template)
task setup

# Edit .env with your API key and notes directory
nano .env  # or your preferred editor

# Activate the virtual environment
source .venv/bin/activate

# Add shell aliases (optional)
task aliases
source ~/.bashrc  # or ~/.zshrc
```

### Using pip

```bash
pip install -e .
cp .env.template .env
# Edit .env with your settings
```

## Configuration

### Environment Variables

Copy the `.env.template` file to `.env` and configure your settings:

```bash
cp .env.template .env
```

Edit `.env` with your values:

```bash
# Anthropic API Key (required)
# Get your API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your-api-key-here

# Notes directory path (required)
# Path to the mounted note-taking device directory containing daily/ and weekly/ subdirectories
NOTES_DIR=/path/to/your/notes/directory
```

### Model Configuration

Edit `config.yaml` to customize Claude model parameters:

```yaml
model: claude-haiku-4-5-20241022
temperature: 0.7
max_tokens: 4096
top_p: 1.0
```

### Notes Directory

Tasker reads notes from a mounted note-taking device at the path specified by `NOTES_DIR` in your `.env` file. Ensure your device is connected and mounted before running analysis.

The expected directory structure is:

```
Notes/
├── daily/
│   ├── 20251225_074353.txt              # Raw daily notes
│   ├── 20251225_074353.daily_analysis.txt  # Generated analysis
│   └── ...
└── weekly/
    ├── 20251223.weekly_analysis.txt     # Generated weekly analysis
    └── ...
```

### Notes File Format

Daily notes files should be named with a timestamp prefix: `YYYYMMDD_HHMMSS.txt`

Task notation in notes:
- Task categories: marked with a single underline above group of bullets
- Completed tasks: marked with a checkmark (✓)
- Removed/abandoned tasks: marked with an X
- Urgent tasks: marked with a star (☆)

## Usage

### Daily Analysis

Analyze the most recent unanalyzed daily notes file:

```bash
analyze-tasks --type daily
# or using the tasker command
tasker --type daily
# or with shell alias
daily
```

This will:
1. Find the most recent `.txt` file in `Notes/daily/` without an existing analysis
2. Generate an execution plan using the daily prompt
3. Save the analysis as `{filename}.daily_analysis.txt`

### Weekly Analysis

Generate a weekly review from the previous week's daily analyses:

```bash
analyze-tasks --type weekly
# or using the tasker command
tasker --type weekly
# or with shell alias
weekly
```

This will:
1. Collect all `*.daily_analysis.txt` files from the previous Monday-Sunday
2. Combine them with date labels
3. Generate a comprehensive weekly analysis
4. Save to `Notes/weekly/{week_start}.weekly_analysis.txt`

## Daily Analysis Output

The daily analysis includes:

- **Prioritized task list** ordered by: starred work → starred home → unstarred work → unstarred home
- **Action steps** broken into 2-3 concrete, sequential steps per task
- **Time estimates** and **energy levels** (Low/Medium/High) for each task
- **Task splitting** for oversized items ([Today Portion] / [Later Portion])
- **Workload guardrails** keeping total focused work to 6-7 hours
- **Critical assessment** evaluating task clarity and planning patterns

## Weekly Analysis Output

The weekly analysis includes:

- **Completion & follow-through analysis** identifying deferral patterns
- **Mis-prioritization detection** comparing intent vs. actual execution
- **Scope & estimation accuracy** review
- **Energy alignment analysis** for optimal task scheduling
- **Corrected priority model** based on observed behavior
- **Next-week planning strategy** with capacity assumptions and day-typing guidance

## Task Commands

```bash
task setup          # Full first-time setup (venv + install + env)
task setup:env      # Create .env file from template
task install        # Install dependencies with uv
task venv           # Create virtual environment
task sync           # Sync dependencies from lock file
task lock           # Update the lock file
task test           # Run tests
task aliases        # Add daily/weekly shell aliases
task aliases:remove # Remove shell aliases
task clean          # Remove build artifacts
task clean:all      # Remove all generated files including venv
```

## Project Structure

```
tasker/
├── .env.template      # Environment variables template
├── config.yaml        # Claude model configuration
├── pyproject.toml     # Project dependencies and metadata
├── Taskfile.yml       # Task runner configuration
├── README.md
└── tasker/            # Python package
    ├── __init__.py    # Package exports
    ├── tasker.py      # Main CLI application
    └── prompts.py     # LangChain prompt templates
```

## Programmatic Usage

The package can also be used as a library:

```python
from tasker import analyze_tasks, get_daily_prompt, get_weekly_prompt

# Get prompt templates with dynamic variables
daily_prompt = get_daily_prompt()
print(daily_prompt.input_variables)  # ['current_date', 'task_notes']

weekly_prompt = get_weekly_prompt()
print(weekly_prompt.input_variables)  # ['week_start', 'week_end', 'task_notes']
```

## License

MIT
