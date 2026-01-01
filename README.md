# Tasker

A CLI tool that analyzes handwritten task notes from a note-taking device using Claude AI to generate actionable GTD-based execution plans.

## Overview

Tasker bridges the gap between handwritten task capture and digital execution planning. Notes written on a note-taking device (e.g., reMarkable, Supernote) are synced to a mounted drive or Google Drive, where Tasker automatically detects and analyzes them using Claude AI via LangChain to:

- **Daily Analysis**: Transform categorized to-do lists into realistic single-day execution plans with time estimates, energy levels, and prioritized action steps
- **Weekly Analysis**: Aggregate daily analyses to identify patterns, diagnose execution breakdowns, and generate corrective planning strategies

## Features

- Automatic detection of the most recent unanalyzed notes file
- Support for both text files (.txt) and images (.png, .jpg, .jpeg, .gif, .webp)
- Automatic text extraction from handwritten note images using Claude's vision API
- Dual storage support: local/USB directories and Google Drive
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

### Notes Source Configuration

Tasker supports two storage backends. Configure at least one:

#### Option 1: USB/Local Directory

For notes synced to a local directory (e.g., via USB from a reMarkable or Supernote):

```bash
# Path to the mounted note-taking device directory
USB_DIR=/path/to/your/notes/directory
```

#### Option 2: Google Drive

For notes synced to Google Drive, see [Google Drive Setup](#google-drive-setup) below.

#### Source Selection

By default, Tasker uses "auto" mode which prefers USB if available, falling back to Google Drive. You can override this:

```bash
# Options: auto, usb, gdrive
NOTES_SOURCE=auto
```

### Anthropic API Key

```bash
# Get your API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your-api-key-here
```

### Model Configuration

Edit `config.yaml` to customize Claude model parameters:

```yaml
model: claude-3-5-haiku-20241022
temperature: 0.7
max_tokens: 4096
top_p: 1.0
```

## Google Drive Setup

To use Google Drive as your notes source, follow these steps:

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "Tasker") and click "Create"

### 2. Enable the Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and press "Enable"

### 3. Create a Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service account"
3. Enter a name (e.g., "tasker-service-account") and click "Create"
4. Skip the optional steps and click "Done"

### 4. Generate Service Account Key

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select "JSON" and click "Create"
5. Save the downloaded JSON file securely (e.g., `~/.config/tasker/credentials.json`)

### 5. Set Up Your Google Drive Folder

1. Create a folder in Google Drive for your notes (e.g., "TaskerNotes")
2. Inside this folder, create two subfolders: `daily` and `weekly`
3. **Important**: Share the folder with your service account:
   - Right-click the folder → "Share"
   - Add the service account email (found in the JSON file as `client_email`, looks like `name@project-id.iam.gserviceaccount.com`)
   - Give it "Editor" access (needed to upload analysis files)

### 6. Get the Folder ID

1. Open your notes folder in Google Drive
2. The folder ID is in the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Copy this ID

### 7. Configure Environment Variables

Add to your `.env` file:

```bash
# Path to your service account credentials JSON file
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# Google Drive folder ID
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here

# Local directory to save analysis output (REQUIRED for service accounts)
# Service accounts don't have storage quota to upload files to Google Drive,
# so analysis files must be saved locally
ANALYSIS_OUTPUT_DIR=/path/to/analysis/output

# Optional: Force Google Drive as the source
NOTES_SOURCE=gdrive
```

### 8. Create the Output Directory

After configuring your `.env` file, create the output directory:

```bash
task setup:output-dir
```

This creates the `daily/` and `weekly/` subdirectories in your `ANALYSIS_OUTPUT_DIR`.

### Important: Service Account Limitations

Google Drive service accounts **cannot upload files** because they don't have storage quota. Tasker uses a hybrid approach:

- **Reads** notes from Google Drive (works with service account)
- **Saves** analysis files locally to `ANALYSIS_OUTPUT_DIR`

This is why `ANALYSIS_OUTPUT_DIR` is required when using Google Drive as your notes source.

### Google Drive Folder Structure

Your Google Drive folder should have this structure (notes only, no analysis files):

```
TaskerNotes/                          # Folder ID goes in GOOGLE_DRIVE_FOLDER_ID
├── daily/
│   ├── 20251225_074353.txt           # Raw daily notes (text)
│   ├── 20251225_074353.png           # Raw daily notes (image)
│   └── ...
└── weekly/
    └── ...
```

Analysis files are saved locally:

```
ANALYSIS_OUTPUT_DIR/
├── daily/
│   └── 20251225_074353.daily_analysis.txt  # Generated analysis
└── weekly/
    └── 20251223.weekly_analysis.txt        # Generated weekly analysis
```

## Notes Directory Structure

Whether using USB or Google Drive, the expected structure is:

```
Notes/
├── daily/
│   ├── 20251225_074353.txt              # Raw daily notes (text)
│   ├── 20251226_083000.png              # Raw daily notes (image)
│   ├── 20251225_074353.daily_analysis.txt  # Generated analysis
│   └── ...
└── weekly/
    ├── 20251223.weekly_analysis.txt     # Generated weekly analysis
    └── ...
```

### Supported File Formats

- **Text files**: `.txt`
- **Image files**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

Image files are automatically processed through Claude's vision API to extract handwritten text.

### Notes File Naming

Files should be named with a timestamp prefix: `YYYYMMDD_HHMMSS.ext`

### Task Notation

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
1. Find the most recent `.txt` or image file in `Notes/daily/` without an existing analysis
2. Extract text from images if needed (using Claude's vision API)
3. Generate an execution plan using the daily prompt
4. Save the analysis as `{filename}.daily_analysis.txt`

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
task setup            # Full first-time setup (venv + install + env)
task setup:env        # Create .env file from template
task setup:output-dir # Create analysis output directory (for Google Drive users)
task install          # Install dependencies with uv
task venv             # Create virtual environment
task sync             # Sync dependencies from lock file
task lock             # Update the lock file
task test             # Run tests
task aliases          # Add daily/weekly shell aliases
task aliases:remove   # Remove shell aliases
task clean            # Remove build artifacts
task clean:all        # Remove all generated files including venv
```

## Testing

The project includes a comprehensive test suite using pytest. Tests are organized by module for maintainability.

### Running Tests

```bash
# Run all tests
pytest

# Run all tests with verbose output
pytest -v

# Run tests for a specific module
pytest tests/test_config.py
pytest tests/test_files.py
pytest tests/test_gdrive.py

# Run tests with coverage report
pytest --cov=tasker --cov-report=term-missing

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

### Test Structure

```
tests/
├── conftest.py      # Shared fixtures (temp directories, mock data)
├── test_config.py   # Configuration and environment tests
├── test_prompts.py  # Prompt template tests
├── test_image.py    # Image extraction tests
├── test_gdrive.py   # Google Drive integration tests
├── test_files.py    # File I/O operation tests
├── test_analysis.py # Core analysis function tests
└── test_cli.py      # CLI entry point tests
```

### Writing Tests

Tests use `unittest.mock` (`Mock`, `MagicMock`, `patch`) to avoid:
- Actual API calls to Claude or Google Drive
- File system side effects
- Network dependencies

Example of mocking the Claude API:

```python
from unittest.mock import patch, MagicMock

def test_analyze_tasks():
    with patch("tasker.analysis.ChatAnthropic") as mock_llm:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Analysis result"
        mock_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_instance

        # Your test code here
```

## Project Structure

```
tasker/
├── .env.template      # Environment variables template
├── config.yaml        # Claude model configuration
├── pyproject.toml     # Project dependencies and metadata
├── Taskfile.yml       # Task runner configuration
├── README.md
├── tasker/            # Python package
│   ├── __init__.py    # Package exports
│   ├── config.py      # Configuration and environment handling
│   ├── prompts.py     # LangChain prompt templates
│   ├── image.py       # Image text extraction
│   ├── files.py       # File I/O operations (USB + Google Drive)
│   ├── gdrive.py      # Google Drive API integration
│   ├── analysis.py    # Core analysis functionality
│   └── cli.py         # Command-line interface
└── tests/             # Test suite
    ├── conftest.py    # Shared pytest fixtures
    ├── test_config.py
    ├── test_prompts.py
    ├── test_image.py
    ├── test_gdrive.py
    ├── test_files.py
    ├── test_analysis.py
    └── test_cli.py
```

## Programmatic Usage

The package can also be used as a library:

```python
from tasker import (
    analyze_tasks,
    get_daily_prompt,
    get_weekly_prompt,
    load_task_notes,
    extract_text_from_image,
    GoogleDriveClient,
    get_notes_source,
)

# Check which source is being used
print(f"Using: {get_notes_source()}")  # "usb" or "gdrive"

# Get prompt templates with dynamic variables
daily_prompt = get_daily_prompt()
print(daily_prompt.input_variables)  # ['current_date', 'task_notes']

weekly_prompt = get_weekly_prompt()
print(weekly_prompt.input_variables)  # ['week_start', 'week_end', 'task_notes']

# Use Google Drive client directly
client = GoogleDriveClient()
files = client.list_notes_files("daily")
```

## Troubleshooting

### Google Drive Issues

**"Google Drive credentials path not set"**
- Ensure `GOOGLE_CREDENTIALS_PATH` is set in your `.env` file
- Verify the path points to a valid JSON credentials file

**"Subfolder 'daily' not found in Google Drive folder"**
- Create `daily` and `weekly` subfolders in your Google Drive notes folder
- Make sure the folder is shared with your service account email

**"Permission denied" errors**
- Verify the service account has "Editor" access to the folder
- Re-share the folder with the service account email

**"No unanalyzed notes files found"**
- Check that your notes files follow the naming format: `YYYYMMDD_HHMMSS.txt` or `.png`
- Verify files are in the correct subfolder (`daily/` or `weekly/`)

### USB Directory Issues

**"USB directory not found"**
- Ensure your device is mounted and accessible
- Verify the `USB_DIR` path in your `.env` file is correct

## License

MIT
