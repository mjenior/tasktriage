# TaskTriage

TaskTriage - ethically source optimism for your productivity.

You know that feeling when you write a beautiful handwritten to-do list and then... don't actually do any of it? This CLI tool uses Claude AI to turn your handwritten task notes into realistic, actionable execution plans based on GTD principles. Think of it as a reality check for your optimistic planning habits.

## Overview

Here's the deal: you write your tasks on a fancy note-taking device (reMarkable, Supernote). Those notes get synced to either a mounted drive or Google Drive. TaskTriage then swoops in, finds your latest scribbles, and uses Claude AI (via LangChain) to do two things:

- **Daily Analysis**: Takes your categorized to-do list and transforms it into an actual realistic plan for a single day. You get time estimates, energy levels, and prioritized action steps. No more pretending you can do 47 things in one afternoon.
- **Weekly Analysis**: Looks back at your week's worth of daily plans to spot patterns, figure out where things went sideways, and generate strategies to fix your planning approach. It's like a retrospective, but with less corporate speak.

## Features

- Automatically finds the most recent notes file you haven't analyzed yet (because who wants to manually track that?)
- Handles both text files (.txt) and images (.png, .jpg, .jpeg, .gif, .webp)
- Extracts text from your handwritten notes using Claude's vision API—yes, even your terrible handwriting
- Works with local/USB directories or Google Drive (your choice)
- Tweak Claude's model parameters via a simple YAML file
- GTD-based prioritization with built-in workload guardrails that cap you at 6-7 hours of focused work per day (because burnout is bad, actually)
- Weekly rollup analysis that shows you where your planning keeps falling apart
- Shell aliases so you can just type `daily` or `weekly` instead of the full command

## Requirements

You'll need:
- Python 3.10 or newer
- [uv](https://github.com/astral-sh/uv) (recommended) or plain old pip
- [Task](https://taskfile.dev/) (optional but makes your life easier)
- An Anthropic API key (this is where Claude lives)

## Installation

### Using Task and uv (the easy way)

```bash
# Full first-time setup (creates venv, installs deps, copies .env template)
task setup

# Edit .env with your API key and notes directory
nano .env  # or your preferred editor

# Activate the virtual environment
source .venv/bin/activate

# Add shell aliases (optional but highly recommended)
task aliases
source ~/.bashrc  # or ~/.zshrc if you're a zsh person
```

### Using pip (the manual way)

If you really want to do it yourself:

```bash
pip install -e .
cp .env.template .env
# Edit .env with your settings
```

## Configuration

### Environment Variables

First things first: copy the `.env.template` file to `.env` and fill in your details.

```bash
cp .env.template .env
```

### Notes Source Configuration

TaskTriage can read your notes from two places. Pick at least one:

#### Option 1: USB/Local Directory

If you're syncing notes to a local directory (like via USB from your reMarkable or Supernote):

```bash
# Path to the mounted note-taking device directory
USB_DIR=/path/to/your/notes/directory
```

#### Option 2: Google Drive

If your notes live in Google Drive, check out the [Google Drive Setup](#google-drive-setup) section below. Fair warning: it's a bit involved.

#### Source Selection

By default, TaskTriage is set to "auto" mode—it looks for USB first, then falls back to Google Drive if USB isn't available. You can force a specific source if you want:

```bash
# Options: auto, usb, gdrive
NOTES_SOURCE=auto
```

### Anthropic API Key

You'll need an API key from Anthropic. Get one at https://console.anthropic.com/ and drop it in:

```bash
ANTHROPIC_API_KEY=your-api-key-here
```

### Model Configuration

Want to tweak how Claude thinks? Edit `config.yaml`:

```yaml
model: claude-3-5-haiku-20241022
temperature: 0.7
max_tokens: 4096
top_p: 1.0
```

## Google Drive Setup

Alright, buckle up. Setting up Google Drive is... not simple. Google's service account setup is designed for enterprise deployments, not cute little task analysis tools. But it works, so here we go.

### 1. Create a Google Cloud Project

1. Head to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it something like "TaskTriage" and click "Create"

### 2. Enable the Google Drive API

1. In your shiny new project, navigate to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and mash that "Enable" button

### 3. Create a Service Account

This is basically a robot user that will access your Drive for you.

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service account"
3. Give it a name like "tasktriage-service-account" and click "Create"
4. Skip the optional permission steps (you don't need them) and click "Done"

### 4. Generate Service Account Key

Now you need to download credentials for your robot:

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select "JSON" format and click "Create"
5. Save the downloaded JSON file somewhere safe, like `~/.config/tasktriage/credentials.json`

Don't lose this file. You can't re-download it.

### 5. Set Up Your Google Drive Folder

1. Create a folder in Google Drive for your notes (call it whatever you want, maybe "TaskTriageNotes")
2. Inside that folder, create two subfolders: `daily` and `weekly`
3. **Here's the critical part**: Share the parent folder with your service account
   - Right-click the folder → "Share"
   - Add the service account email (it's in the JSON file you downloaded, labeled `client_email`—looks like `name@project-id.iam.gserviceaccount.com`)
   - Give it "Editor" access

If you skip step 3, nothing will work and you'll spend an hour debugging permissions. Ask me how I know.

### 6. Get the Folder ID

1. Open your notes folder in Google Drive
2. Look at the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Copy the folder ID from the URL

### 7. Configure Environment Variables

Add these to your `.env` file:

```bash
# Path to your service account credentials JSON file
GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# Google Drive folder ID
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here

# Local directory to save analysis output (REQUIRED for service accounts)
# Service accounts don't have storage quota to upload files to Google Drive,
# so analysis files must be saved locally
LOCAL_OUTPUT_DIR=/path/to/analysis/output

# Optional: Force Google Drive as the source
NOTES_SOURCE=gdrive
```

### 8. Create the Output Directory

After you've configured your `.env` file, run this to create the output directory structure:

```bash
task setup:output-dir
```

This creates the `daily/` and `weekly/` subdirectories inside your `LOCAL_OUTPUT_DIR`.

### Important: Service Account Limitations

Here's the annoying part: Google Drive service accounts **can't upload files** because they don't have storage quota. I know, it's weird. So TaskTriage uses a hybrid approach:

- **Reads** notes from Google Drive (works fine with service accounts)
- **Saves** analysis files locally to `LOCAL_OUTPUT_DIR` (because uploading doesn't work)

This is why `LOCAL_OUTPUT_DIR` is required when using Google Drive. Your analyzed tasks don't go back to the cloud—they stay on your machine.

### Google Drive Folder Structure

Your Google Drive folder should look like this (notes only, no analysis files):

```
TaskTriageNotes/                          # This folder ID goes in GOOGLE_DRIVE_FOLDER_ID
├── daily/
│   ├── 20251225_074353.txt           # Raw daily notes (text)
│   ├── 20251225_074353.png           # Raw daily notes (image)
│   └── ...
└── weekly/
    └── ...
```

Analysis files get saved locally instead:

```
LOCAL_OUTPUT_DIR/
├── daily/
│   └── 20251225_074353.daily_analysis.txt  # Generated analysis
└── weekly/
    └── 20251223.weekly_analysis.txt        # Generated weekly analysis
```

## Notes Directory Structure

Whether you're using USB or Google Drive, TaskTriage expects this structure:

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

Image files get run through Claude's vision API to extract your handwritten text automatically.

### Notes File Naming

Name your files with a timestamp prefix: `YYYYMMDD_HHMMSS.ext`

This lets TaskTriage figure out which file is most recent and which ones have already been analyzed.

### Task Notation

How to mark up your handwritten notes:
- **Task categories**: Draw a single underline above a group of bullets
- **Completed tasks**: Add a checkmark (✓)
- **Removed/abandoned tasks**: Mark with an X
- **Urgent tasks**: Add an asterisk (*)

## Usage

### Daily Analysis

To analyze your most recent unanalyzed daily notes:

```bash
task-triage --type daily
# or using the tasktriage command
tasktriage --type daily
# or just use the alias (if you set it up)
daily
```

What happens:
1. TaskTriage finds the most recent `.txt` or image file in `Notes/daily/` that doesn't have an analysis yet
2. If it's an image, Claude's vision API extracts the text from your handwriting
3. The daily analysis prompt kicks in and generates a realistic execution plan
4. The analysis gets saved as `{filename}.daily_analysis.txt`

### Weekly Analysis

To generate a weekly review from your previous week's daily work:

```bash
task-triage --type weekly
# or using the tasktriage command
tasktriage --type weekly
# or just use the alias
weekly
```

What happens:
1. Grabs all `*.daily_analysis.txt` files from the previous Monday through Sunday
2. Combines them with date labels
3. Generates a comprehensive weekly analysis looking at patterns and problems
4. Saves to `Notes/weekly/{week_start}.weekly_analysis.txt`

## Daily Analysis Output

The daily analysis gives you:

- **Prioritized task list** in order: starred work → starred home → unstarred work → unstarred home (because that's probably what you actually care about)
- **Action steps**: Each task gets broken into 2-3 concrete, sequential steps so you know where to start
- **Time estimates** and **energy levels** (Low/Medium/High) for each task
- **Task splitting** for oversized items—splits them into [Today Portion] and [Later Portion] so you're not lying to yourself
- **Workload guardrails** that keep your total focused work at 6-7 hours (not the 14 you originally planned)
- **Critical assessment** that calls out when your task descriptions are vague or your planning patterns are problematic

## Weekly Analysis Output

The weekly analysis shows you:

- **Completion & follow-through analysis**: Where do you keep deferring stuff?
- **Mis-prioritization detection**: What you said was important vs. what you actually did
- **Scope & estimation accuracy**: How wrong were your time estimates? (It's okay, we're all bad at this)
- **Energy alignment analysis**: Are you scheduling high-energy tasks when you're exhausted?
- **Corrected priority model** based on your actual behavior, not your aspirational self
- **Next-week planning strategy** with realistic capacity assumptions and guidance on how to structure your days

## Task Commands

If you're using Task for automation, here are the available commands:

```bash
task setup            # Full first-time setup (venv + install + env)
task setup:env        # Create .env file from template
task setup:output-dir # Create analysis output directory (Google Drive users need this)
task install          # Install dependencies with uv
task venv             # Create virtual environment
task sync             # Sync dependencies from lock file
task lock             # Update the lock file
task test             # Run tests
task aliases          # Add daily/weekly shell aliases
task aliases:remove   # Remove shell aliases
task clean            # Remove build artifacts
task clean:all        # Nuclear option: remove everything including venv
```

## Testing

The project has a test suite using pytest. Tests are split up by module so you can find what you're looking for.

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output to see what's actually happening
pytest -v

# Run tests for a specific module
pytest tests/test_config.py
pytest tests/test_files.py
pytest tests/test_gdrive.py

# Get a coverage report to see what you missed
pytest --cov=tasktriage --cov-report=term-missing

# Skip the slow integration tests
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
- Actually calling Claude or Google Drive APIs (and burning through your API credits)
- Messing with the file system
- Network dependencies that make tests flaky

Example of mocking the Claude API:

```python
from unittest.mock import patch, MagicMock

def test_analyze_tasks():
    with patch("tasktriage.analysis.ChatAnthropic") as mock_llm:
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Analysis result"
        mock_instance.invoke.return_value = mock_response
        mock_llm.return_value = mock_instance

        # Your test code here
```

## Project Structure

Here's how the code is organized:

```
tasktriage/
├── .env.template      # Environment variables template
├── config.yaml        # Claude model configuration
├── pyproject.toml     # Project dependencies and metadata
├── Taskfile.yml       # Task runner configuration
├── README.md
├── tasktriage/        # Python package
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

You can also use TaskTriage as a library in your own Python code:

```python
from tasktriage import (
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

# Use the Google Drive client directly
client = GoogleDriveClient()
files = client.list_notes_files("daily")
```

## Troubleshooting

### Google Drive Issues

**"Google Drive credentials path not set"**
- Make sure `GOOGLE_CREDENTIALS_PATH` is set in your `.env` file
- Double-check that the path actually points to your credentials JSON file

**"Subfolder 'daily' not found in Google Drive folder"**
- You need to create `daily` and `weekly` subfolders in your Google Drive notes folder
- Also confirm the parent folder is shared with your service account (easy to forget this step)

**"Permission denied" errors**
- Check that your service account has "Editor" access to the folder
- Try removing and re-sharing the folder with the service account email
- Remember: the service account email is in your credentials JSON file as `client_email`

**"No unanalyzed notes files found"**
- Your notes files need to follow the naming format: `YYYYMMDD_HHMMSS.txt` or `.png`
- Make sure they're in the correct subfolder (`daily/` or `weekly/`)
- TaskTriage is looking for files that don't have a matching `.daily_analysis.txt` or `.weekly_analysis.txt` file

### USB Directory Issues

**"USB directory not found"**
- Is your device actually plugged in and mounted?
- Check that the `USB_DIR` path in your `.env` file is correct and points to the right location

## License

MIT
