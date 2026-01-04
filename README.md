# TaskTriage

TaskTriage - ethically sourced optimism for your productivity.

You know that feeling when you write a great handwritten to-do list and then... don't know what to do first, or worse don't actually do any of it? This CLI tool uses Claude AI to turn your handwritten task notes into realistic, actionable execution plans based on GTD principles. Think of it as a reality check for your optimistic planning habits.

<div align="center">
  <img src="./logo.png" alt="TaskTriage Logo" width="75%">
</div>

## Overview

Here's the deal: you write your tasks on a note-taking device (reMarkable, Supernote, etc.). Those notes get synced to either a mounted drive or Google Drive. TaskTriage then swoops in, finds your latest scribbles, and uses Claude AI (via LangChain) to do four things:

- **Daily Analysis**: Takes your categorized to-do list and transforms it into an actual realistic plan for a single day. You get time estimates, energy levels, and prioritized action steps. No more pretending you can do 47 things in one afternoon.
- **Weekly Analysis**: Looks back at your week's worth of daily plans to spot patterns, figure out where things went sideways, and generate strategies to fix your planning approach. It's like a retrospective, but with less corporate speak.
- **Monthly Analysis**: Synthesizes your entire month's worth of weekly analyses to identify long-term patterns, assess strategic accomplishments, and craft high-level guidance for next month's planning and execution strategy.
- **Annual Analysis**: Analyzes all 12 months of strategic insights to identify year-long accomplishments, skill development, and high-impact opportunities for the year ahead.

## Features

- Automatically finds ALL unanalyzed notes files and processes them in parallel (because who wants to manually track that?)
- Handles both text files (.txt) and images (.png, .jpg, .jpeg, .gif, .webp)
- Extracts text from your handwritten notes using Claude's vision API—yes, even your terrible handwriting
- **Automatic raw text preservation**: When analyzing PNG notes, automatically saves the extracted text as `.raw_notes.txt` files for easy editing in the UI
- **Smart re-analysis**: Detects when notes files are edited after their initial analysis and automatically includes them for re-analysis, replacing old analyses
- Works with local/USB directories or Google Drive (your choice)
- Tweak Claude's model parameters via a simple YAML file
- GTD-based prioritization with built-in workload guardrails that cap you at 6-7 hours of focused work per day (because burnout is bad, actually)
- **Temporal hierarchy**: Daily → Weekly → Monthly → Annual, with automatic analysis triggering at each level
- Auto-triggers weekly analyses when you have 5+ weekday analyses or when the work week has passed
- Auto-triggers monthly analyses when you have 4+ weekly analyses or when the calendar month has ended
- Auto-triggers annual analyses when you have 12 monthly analyses or when the calendar year has ended with at least 1 monthly analysis
- Shell alias so you can just type `triage` instead of the full command
- **Web Interface**: A professional Streamlit UI for browsing, editing, creating, and triaging your notes visually

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

# Add shell alias (optional but highly recommended)
task alias
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

TaskTriage can read notes from multiple input sources simultaneously. Configure at least one:

#### Option 1: USB/Mounted Device Directory

If you're syncing notes to a USB drive or mounted device from your reMarkable or Supernote:

```bash
# Path to the mounted note-taking device directory
USB_INPUT_DIR=/path/to/your/usb/notes/directory
```

#### Option 2: Local Hard Drive Directory

Add an additional local directory to check for notes files:

```bash
# Path to local hard drive notes directory (optional)
LOCAL_INPUT_DIR=/path/to/your/local/notes/directory
```

#### Option 3: Google Drive

If your notes live in Google Drive, check out the [Google Drive Setup](#google-drive-setup) section below. Fair warning: it's a bit involved.

#### How Multi-Source Reading Works

**TaskTriage automatically checks ALL configured input directories** when looking for notes files. If you have both `USB_INPUT_DIR` and `LOCAL_INPUT_DIR` configured, it will:
- Search both directories for unanalyzed notes
- Deduplicate files by timestamp (if the same timestamp appears in multiple locations, only the first one found is processed)
- Collect unique notes from all sources for analysis

This means you can have notes in multiple locations and TaskTriage will find them all.

#### Source Selection for New Files

By default, TaskTriage is set to "auto" mode for OUTPUT (creating new files in the UI):

```bash
# Options: auto, usb, gdrive
NOTES_SOURCE=auto
```

In auto mode, new files created in the UI are saved to:
1. `USB_INPUT_DIR` (if available)
2. `LOCAL_INPUT_DIR` (if USB not available)
3. Google Drive (if neither local directory is available)

#### Backward Compatibility

The old `USB_DIR` variable is still supported for backward compatibility. If you have existing configurations using `USB_DIR`, they will continue to work (it's treated as `USB_INPUT_DIR`).

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
2. Inside that folder, create subfolders: `daily`, `weekly`, `monthly`, and `annual`
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

This creates the `daily/`, `weekly/`, `monthly/`, and `annual/` subdirectories inside your `LOCAL_OUTPUT_DIR`.

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
├── weekly/
│   └── ...
└── monthly/
    └── ...
```

Analysis files get saved locally instead:

```
LOCAL_OUTPUT_DIR/
├── daily/
│   └── 20251225_074353.daily_analysis.txt  # Generated analysis
├── weekly/
│   └── 20251223.weekly_analysis.txt        # Generated weekly analysis
├── monthly/
│   └── 202512.monthly_analysis.txt         # Generated monthly analysis
└── annual/
    └── 2025.annual_analysis.txt            # Generated annual analysis
```

## Notes Directory Structure

Whether you're using USB or Google Drive, TaskTriage expects this structure:

```
notes/
├── daily/
│   ├── 20251225_074353.txt              # Raw daily notes (text)
│   ├── 20251226_083000.png              # Raw daily notes (image)
│   ├── 20251226_083000.raw_notes.txt    # Extracted text from PNG (auto-generated, editable)
│   ├── 20251225_074353.daily_analysis.txt  # Generated analysis
│   ├── 20251226_083000.daily_analysis.txt  # Generated analysis
│   └── ...
├── weekly/
│   ├── 20251223.weekly_analysis.txt     # Generated weekly analysis
│   └── ...
├── monthly/
│   ├── 202512.monthly_analysis.txt      # Generated monthly analysis
│   └── ...
└── annual/
    └── 2025.annual_analysis.txt         # Generated annual analysis
```

### Supported File Formats

- **Text files**: `.txt`
- **Image files**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- **Raw text files**: `.raw_notes.txt` (auto-generated from image analysis, preserves completion markers)

Image files get run through Claude's vision API to extract your handwritten text automatically. The extracted text is saved as a `.raw_notes.txt` file in parallel with the analysis, making it easy to edit the text directly in the UI if needed. If you edit a `.raw_notes.txt` file after its initial analysis, TaskTriage will detect the change and automatically re-analyze it on the next run.

### Notes File Naming

Name your files with a timestamp prefix: `YYYYMMDD_HHMMSS.ext`

This lets TaskTriage figure out which file is most recent and which ones have already been analyzed.

### Task Notation

How to mark up your handwritten notes:
- **Task categories**: Draw a single underline above a group of bullets
- **Completed tasks**: Add a checkmark (✓)
- **Removed/abandoned tasks**: Mark with an (✗)
- **Urgent tasks**: Add a star (☆)

### Example Files

Not sure what your task notes should look like? Check out the example files in the `tests/examples/` directory:

- **`20251225_074353.txt`**: Example text file showing proper task formatting with categories (agents team, Admin, Home), task items, and completion markers
- **`20251225_074353_Page_1.png`**: Example PNG image of handwritten notes demonstrating how TaskTriage processes scanned/photographed task lists

These files demonstrate:
- Correct filename format with timestamp prefix (`YYYYMMDD_HHMMSS`)
- Task organization with category headers
- Multi-page support (using `_Page_N` suffix for image files)
- How TaskTriage handles both text and image inputs

You can use these as templates when creating your own task note files. The example files are also used in the test suite to ensure TaskTriage correctly processes real-world note formats.

## Usage

To run TaskTriage:

```bash
# Using the full command
tasktriage

# or using the alias (if you set it up)
triage

# Specify file type preference (defaults to png)
tasktriage --files txt
tasktriage --files png
```

### Web Interface

TaskTriage includes a web interface built with Streamlit. Launch it with:

```bash
# Using Task
task ui

# Or directly with uv
uv run streamlit run streamlit_app.py
```

The UI opens in your browser at `http://localhost:8501` and provides:

**Left Panel (Controls)**
- **Triage Button** - Run the full analysis pipeline with real-time progress updates
- **Configuration** - Edit `.env` and `config.yaml` settings directly in the browser (API keys, notes source, model parameters)
- **Raw Notes List** - Browse `.txt` and image files from your `daily/` directory, sorted by date
  - **Open** - Load a selected note file for editing
  - **New** - Create a new empty `.txt` notes file with timestamp-based naming
- **Analysis Files List** - Browse all generated analysis files across daily/weekly/monthly/annual

**Right Panel (Editor)**
- Full-height text editor for viewing and editing selected files
- Image preview for handwritten note images
- Save/Revert buttons with unsaved changes indicator
- Notes source status display
- **Quick Markup Tools** - Easily add task markers (✓ completed, ✗ removed, ☆ urgent), which are automatically interpretted at the right side of each line.

The web interface runs the same analysis pipeline as the CLI, with parallel processing and automatic triggering of weekly/monthly/annual analyses when conditions are met.

### What Happens When You Run It

TaskTriage follows a strict temporal hierarchy, ensuring each level completes before the next begins:

**LEVEL 1: Daily Analysis (runs automatically)**

1. TaskTriage finds ALL unanalyzed `.txt` or image files in `Notes/daily/`
   - Includes files that have never been analyzed
   - **Smart re-analysis**: Also includes files that were edited after their last analysis (detects changes by comparing file modification times)
2. Processes them in parallel (up to 5 concurrent API calls)
3. For images, Claude's vision API extracts the text from your handwriting
   - **Automatic preservation**: The extracted text is also saved as a `.raw_notes.txt` file for easy editing in the UI
4. Each file gets analyzed and saved as `{filename}.daily_analysis.txt`
   - If re-analyzing an edited file, the new analysis **replaces** the old one (no duplicates)
5. Shows progress in real-time with success/failure indicators
6. Prints: `Daily Summary: X successful, Y failed`

**LEVEL 2: Weekly Analysis (auto-triggers when conditions are met)**

After all daily analyses complete, TaskTriage checks if any weeks need analysis. A weekly analysis is triggered automatically when:
- **5+ weekday analyses exist** for a work week (Monday-Friday), OR
- **The work week has passed** and at least 1 daily analysis exists for that week

When triggered:
1. Collects all daily analysis files from Monday-Friday of the qualifying week
2. Combines them with date labels
3. Generates a comprehensive weekly analysis looking at patterns and problems
4. Saves to `Notes/weekly/{week_start}.weekly_analysis.txt`
5. Prints: `Weekly Summary: X successful, Y failed`

**LEVEL 3: Monthly Analysis (auto-triggers when conditions are met)**

After all weekly analyses complete, TaskTriage checks if any months need analysis. A monthly analysis is triggered automatically when:
- **4+ weekly analyses exist** for a calendar month, OR
- **The calendar month has ended** and at least 1 weekly analysis exists for that month

When triggered:
1. Collects all weekly analysis files from the qualifying month
2. Combines them with week-range labels
3. Generates a comprehensive monthly analysis synthesizing strategic patterns across the entire month
4. Saves to `Notes/monthly/{month_label}.monthly_analysis.txt`
5. Prints: `Monthly Summary: X successful, Y failed`

**LEVEL 4: Annual Analysis (auto-triggers when conditions are met)**

After all monthly analyses complete, TaskTriage checks if any years need analysis. An annual analysis is triggered automatically when:
- **12 monthly analyses exist** for a calendar year, OR
- **The calendar year has ended** and at least 1 monthly analysis exists for that year

When triggered:
1. Collects all monthly analysis files from the qualifying year
2. Combines them with month labels
3. Generates a comprehensive annual analysis synthesizing year-long accomplishments, learning, and strategic opportunities
4. Saves to `Notes/annual/{year}.annual_analysis.txt`
5. Prints: `Annual Summary: X successful, Y failed`

You don't have to trigger any of these manually—TaskTriage handles the entire hierarchy automatically!

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

## Monthly Analysis Output

The monthly analysis synthesizes your entire month to show you:

- **Monthly achievements summary**: Major accomplishments organized by category (Work, Personal, System)
- **Strategic patterns and trends**: 3-5 month-level patterns like execution rhythms, category performance, capacity trends
- **System evolution assessment**: Which weekly recommendations actually got implemented? Which ones worked?
- **Persistent challenges**: Problems that survived multiple weekly corrections—these are the real issues
- **Monthly performance metrics**: Completion rates, workload balance, priority alignment, energy management, planning quality
- **Strategic guidance for next month**: Month-level priorities, capacity planning, category focus, recommended pacing
- **Long-term system refinements**: 3-6 fundamental changes to try in your planning system

Monthly analyses are **strategic level**, not tactical. They reveal patterns invisible at the weekly level and help you understand your actual productivity rhythms over time.

## Annual Analysis Output

The annual analysis synthesizes your entire year to show you:

- **Year in accomplishments**: Your major wins and achievements across the full calendar year, organized by category and impact
- **Learning & skill development**: Areas where you've grown professionally and personally throughout the year, plus knowledge gaps revealed
- **Highest-impact opportunities**: 2-4 specific improvements that would generate the most leverage in the year ahead, ranked by ROI
- **Year-ahead strategic direction**: Recommendations for next year's focus areas, capacity planning, and systemic changes based on what you learned

Annual analyses are **strategic and retrospective**. They help you see the big picture—what you actually accomplished beyond the day-to-day grind, and what's worth focusing on next year. This is where you look back at the full story of your year, not just individual months.

## Directory Structure

TaskTriage organizes your analyses in a clear hierarchy:

```
Notes/
├── daily/
│   ├── 20251225_074353.txt                    # Your daily task notes (text)
│   ├── 20251225_074353.daily_analysis.txt     # Analysis output
│   ├── 20251226_094500.png                    # Your daily task notes (image)
│   ├── 20251226_094500.raw_notes.txt          # Extracted text from PNG (auto-generated)
│   └── 20251226_094500.daily_analysis.txt     # Analysis output
├── weekly/
│   ├── 20251223.weekly_analysis.txt           # Week of Dec 23-27
│   └── 20251230.weekly_analysis.txt           # Week of Dec 30-Jan 3
├── monthly/
│   ├── 202512.monthly_analysis.txt            # December 2025 synthesis
│   └── 202511.monthly_analysis.txt            # November 2025 synthesis
└── annual/
    └── 2025.annual_analysis.txt               # Full year 2025 synthesis
```

Filename formats:
- **Daily notes**: `YYYYMMDD_HHMMSS.{txt|png|jpg|...}` (e.g., `20251225_074353.txt`)
- **Raw text from images**: `YYYYMMDD_HHMMSS.raw_notes.txt` (auto-generated when analyzing PNG files)
- **Daily analyses**: `YYYYMMDD_HHMMSS.daily_analysis.txt`
- **Weekly analyses**: `YYYYMMDD.weekly_analysis.txt` (date is Monday of that week)
- **Monthly analyses**: `YYYYMM.monthly_analysis.txt` (e.g., `202512.monthly_analysis.txt` for December 2025)
- **Annual analyses**: `YYYY.annual_analysis.txt` (e.g., `2025.annual_analysis.txt` for full year 2025)

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
task ui               # Launch the Streamlit web interface
task alias            # Add triage shell alias
task alias:remove     # Remove shell alias
task clean            # Remove build artifacts
task clean:all        # Nuclear option: remove everything including venv
task bump             # Show version bump options
task bump:patch       # Bump patch version (e.g. 0.1.1 → 0.1.2)
task bump:minor       # Bump minor version (e.g. 0.1.1 → 0.2.0)
task bump:major       # Bump major version (e.g. 0.1.1 → 1.0.0)
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
├── .bumpversion.toml  # Version bump configuration
├── config.yaml        # Claude model configuration
├── pyproject.toml     # Project dependencies and metadata
├── Taskfile.yml       # Task runner configuration
├── streamlit_app.py   # Web interface (Streamlit UI)
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
    get_monthly_prompt,
    get_annual_prompt,
    load_task_notes,
    load_all_unanalyzed_task_notes,
    collect_weekly_analyses_for_week,
    collect_monthly_analyses_for_month,
    collect_annual_analyses_for_year,
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

monthly_prompt = get_monthly_prompt()
print(monthly_prompt.input_variables)  # ['month_start', 'month_end', 'task_notes']

annual_prompt = get_annual_prompt()
print(annual_prompt.input_variables)  # ['year', 'task_notes']

# Load all unanalyzed daily notes
unanalyzed = load_all_unanalyzed_task_notes("daily", "png")
for content, path, date in unanalyzed:
    print(f"Found: {path.name}")

# Collect analyses for a specific period
from datetime import datetime
month_start = datetime(2025, 12, 1)
month_end = datetime(2025, 12, 31)
monthly_content, output_path, ms, me = collect_monthly_analyses_for_month(month_start, month_end)

# Collect annual analyses for a specific year
annual_content, output_path, year = collect_annual_analyses_for_year(2025)

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

### USB/Local Directory Issues

**"No input directories configured or available"**
- Make sure at least one of `USB_INPUT_DIR` or `LOCAL_INPUT_DIR` is set in your `.env` file
- Verify the paths are correct and the directories actually exist

**"USB directory not found"**
- Is your USB device actually plugged in and mounted?
- Check that the `USB_INPUT_DIR` path in your `.env` file is correct and points to the right location
- The directory must contain `daily/`, `weekly/`, `monthly/`, and `annual/` subdirectories

**"Local directory not found"**
- Verify the `LOCAL_INPUT_DIR` path exists
- Make sure it has the required subdirectory structure (`daily/`, etc.)

### Re-Analysis and Editing Notes

**How do I fix mistakes in my analyzed notes?**
- Simply edit the `.txt` or `.raw_notes.txt` file in the UI or your text editor
- Save your changes
- Run the analysis again—TaskTriage automatically detects the file was modified after its analysis and will re-analyze it
- The new analysis **replaces** the old one (same filename), so you won't have duplicate analysis files

**What files trigger re-analysis?**
- `.txt` files that were modified after their `.daily_analysis.txt` was created
- `.raw_notes.txt` files (extracted from PNGs) that were edited after their analysis
- The original `.png` file itself if it was replaced with a newer version

**When does re-analysis NOT happen?**
- If the notes file is older than its analysis file (no changes detected)
- For files without any existing analysis (these are treated as new files, not re-analysis)

## License

MIT
