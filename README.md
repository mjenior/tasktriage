# TaskTriage

TaskTriage - ethically sourced optimism for your productivity.

You know that feeling when you write a great handwritten to-do list and then... don't know what to do first, or worse don't actually do any of it? This CLI tool uses Claude AI to analyze your handwritten task notes and reveal what actually got done (and why) based on GTD principles. Think of it as a reality check for your optimistic planning habits.

<div align="center">
  <img src="./.images/logo.png" alt="TaskTriage Logo" width="50%">
</div>

## Overview

You might have this feeling too: You write a semi-disorganized list(s) of daily tasks by hand or in some digital format to keep you on track everyday. For extra safety, maybe those notes get synced to either a mounted drive or Google Drive, but that's kind of where it ends. You end up maybe just prioritizing wrong and then have a pile of old notebooks with important information on a shelf collecting dust. Well, TaskTriage is here to then swoop in, find your latest scribbles, and uses Claude AI (via LangChain) to do four things:

- **Daily Analysis**: Analyzes your end-of-day task list to assess what you actually completed, abandoned, or left incomplete. You get insights into execution patterns, priority alignment, energy management, and workload realism. No more wondering why those 47 things didn't get done.
- **Weekly Analysis**: Looks back at your week's worth of daily analyses to spot patterns, figure out where things went sideways, and generate strategies to fix your planning approach. It's like a retrospective, but with less corporate speak.
- **Monthly Analysis**: Synthesizes your entire month's worth of weekly analyses to identify long-term patterns, assess strategic accomplishments, and craft high-level guidance for next month's planning and execution strategy.
- **Annual Analysis**: Analyzes all 12 months of strategic insights to identify year-long accomplishments, skill development, and high-impact opportunities for the year ahead.
- **Project Context Summarization**: Automatically generates structured summaries of your project codebases to enrich task analyses with contextual knowledge about what you're actually working on.

## Features

- Handles text files (.txt), images (.png, .jpg, .jpeg, .gif, .webp), and PDFs (.pdf)
- Extracts text from your handwritten notes using Claude's vision API—yes, even your terrible handwriting (including multi-page PDFs)
- **Two-step workflow**: Sync first to copy and convert files, then Analyze when you're ready
- **Sync operation**: Copies raw notes from input directories and converts images/PDFs to editable `.raw_notes.txt` files using Claude's vision API
- **Smart re-analysis**: Detects when notes files are edited after their initial analysis and automatically includes them for re-analysis, replacing old analyses
- **Multi-source reading**: Works with any combination of local directories, USB devices, and Google Drive simultaneously
- Tweak Claude's model parameters via a simple YAML file
- GTD-based execution analysis with workload realism checks against healthy limits of 6-7 hours of focused work per day (because burnout is bad, actually)
- **Temporal hierarchy**: Daily analyses are on-demand; Weekly → Monthly → Annual analyses auto-trigger when conditions are met
- Auto-triggers weekly analyses when you have 5+ weekday analyses or when the work week has passed
- Auto-triggers monthly analyses when you have 4+ weekly analyses or when the calendar month has ended
- Auto-triggers annual analyses when you have 12 monthly analyses or when the calendar year has ended with at least 1 monthly analysis
- **Project Context Collection**: Reads directory paths from `task_context.md`, collects file contents from your project directories, and generates structured codebase summaries using Claude
- **Smart Change Detection**: Only re-summarizes project directories when file contents actually change (mtime-based tracking)
- Shell alias so you can just type `triage` instead of the full command
- **Web Interface**: A Streamlit UI for browsing, editing, creating, and triaging your notes visually

**Note:** Works especially well when paired with a note-taking device (reMarkable, Supernote, etc.). Since it works with images and PDFs, you can take a photo of your handwritten notes, scan documents, or export PDFs from your note-taking app and analyze those!

<div align="center">
  <img src="./.images/ui.png" alt="Streamlit App">
</div>

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
# Basic installation
pip install -e .
cp .env.template .env
# Edit .env with your settings

# Optional: Install semantic matching support (recommended)
pip install -e ".[semantic]"
```

The `semantic` extra installs `sentence-transformers` and `torch` for advanced context matching. See [Context Matching: Semantic vs Keyword](#context-matching-semantic-vs-keyword) for details.

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
EXTERNAL_INPUT_DIR=/path/to/your/usb/notes/directory
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

**TaskTriage automatically checks ALL configured input directories** when looking for notes files. If you have both `EXTERNAL_INPUT_DIR` and `LOCAL_INPUT_DIR` configured, it will:
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
1. `EXTERNAL_INPUT_DIR` (if available)
2. `LOCAL_INPUT_DIR` (if USB not available)
3. Google Drive (if neither local directory is available)

### Anthropic API Key

You'll need an API key from Anthropic. Get one at https://console.anthropic.com/ and drop it in:

```bash
ANTHROPIC_API_KEY=your-api-key-here
```

### Model Configuration

Want to tweak how Claude thinks? Edit `config.yaml`:

```yaml
model: claude-haiku-4-5-20241022
temperature: 0.7
max_tokens: 4096
top_p: 1.0
```

## Google Drive Setup

TaskTriage uses OAuth 2.0 to access your Google Drive, giving you full read/write access to your personal Google account without the limitations of service accounts.

### ⚠️ Critical Setup Requirements

Don't skip these or you'll get an OAuth error:

1. **Register the redirect URI** in Google Cloud Console:
   - Must be: `http://localhost:8501` (with port number)
   - Add this in "OAuth client ID" → "Authorized redirect URIs"

2. **Add yourself as a test user**:
   - In "OAuth consent screen" → "Test users"
   - Add your Google account email

3. **Wait for Google to cache the settings**:
   - Wait 3-5 minutes after configuring OAuth
   - Then restart Streamlit and try again

### 1. Create a Google Cloud Project

1. Head to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it something like "TaskTriage" and click "Create"

### 2. Enable the Google Drive API

1. In your project, navigate to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and click the "Enable" button

### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Fill in application details:
   - App name: "TaskTriage"
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. **Add Scopes**:
   - Click "Add or Remove Scopes"
   - Search for "Google Drive API"
   - Select: `https://www.googleapis.com/auth/drive`
   - Click "Update" then "Save and Continue"
6. **Add Test Users** (for development):
   - Add your Google account email as a test user
   - Click "Save and Continue"

### 4. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. Name: "TaskTriage Web Client"
5. **Under "Authorized redirect URIs"**:
   - Click "Add URI"
   - Enter: `http://localhost:8501`
   - **IMPORTANT**: This must match exactly (including the port number)
6. Click "Create"
7. **Copy and save**:
   - Copy the **Client ID** (looks like: `xxx.apps.googleusercontent.com`)
   - Copy the **Client Secret** (looks like: `GOCSPX-xxx`)
   - You'll need these in the next step

### 5. Configure TaskTriage

Add these to your `.env` file:

```bash
# OAuth 2.0 credentials from Google Cloud Console
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# Google Drive folder ID
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here

# Local directory to save analysis output (always required)
LOCAL_OUTPUT_DIR=/path/to/your/output/local/directory
```

### 6. Set Up Your Google Drive Folder

1. Create a folder in Google Drive for your notes (e.g., "TaskTriageNotes")
2. Inside that folder, create subfolders: `daily`, `weekly`, `monthly`, `annual`
3. Get the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. Add the folder ID to your `.env` file

### 7. First-Time Authentication

1. Launch TaskTriage UI: `task ui`
2. Open the "Configuration" expander
3. Under "Google Drive (OAuth 2.0)", you'll see "Not authenticated"
4. Enter your OAuth Client ID and Client Secret
5. Click "🔐 Sign in with Google"
6. Follow the OAuth flow in your browser
7. Grant permissions to TaskTriage
8. You'll be redirected back to Streamlit with "Authenticated with Google Drive"

### 8. Important Notes

- OAuth tokens are stored encrypted in `~/.tasktriage/oauth_tokens.json`
- Tokens automatically refresh when expired
- You can revoke access anytime at [Google Account Settings](https://myaccount.google.com/permissions)
- Full read/write access to Google Drive (no storage quota limitations)
- Can sync analysis files directly to Google Drive via the Sync button

### Troubleshooting OAuth Setup

#### Error: "You can't sign in to this app because it doesn't comply with Google's OAuth 2.0 policy"

**Solution**: You need to register the redirect URI in Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your TaskTriage project
3. Go to "APIs & Services" → "Credentials"
4. Find your "TaskTriage Web Client" OAuth credential
5. Click on it to edit
6. Under "Authorized redirect URIs", verify that `http://localhost:8501` is listed
7. If not, click "Add URI" and add: `http://localhost:8501`
8. Click "Save"
9. Restart your Streamlit app and try signing in again

**Note**: The redirect URI must include the exact port number (8501). If you're running Streamlit on a different port, update the URI accordingly (e.g., `http://localhost:8502`).

#### Error: "redirect_uri parameter does not match"

**Solution**: The redirect URI in the OAuth configuration doesn't match. Check:

1. In Google Cloud Console, confirm the exact redirect URI registered (should be `http://localhost:8501`)
2. Verify Streamlit is running on port 8501 (check the URL in your browser)
3. If running on a different port, either:
   - Change the port in Google Cloud Console to match, OR
   - Modify the `redirect_uri` in `streamlit_app.py` line 703

#### "Invalid OAuth state. Please try again."

This error has been fixed in the current version. If you encounter it:

1. Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear your browser cookies
3. Try signing in again

The OAuth flow should now work reliably on localhost without CSRF state validation issues.

#### "Not authenticated" but can't sign in

1. Ensure you're listed as a test user in the OAuth consent screen
2. Wait a few minutes after configuring OAuth (Google caches settings)
3. Try in an incognito/private browser window
4. Clear your browser cache and cookies

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
│   └── 25_12_2025.triaged.txt              # Generated analysis (DD_MM_YYYY format)
├── weekly/
│   └── week1_12_2025.triaged.txt           # Generated weekly analysis (weekN_MM_YYYY format)
├── monthly/
│   └── 12_2025.triaged.txt                 # Generated monthly analysis (MM_YYYY format)
└── annual/
    └── 2025.triaged.txt                    # Generated annual analysis (YYYY format)
```

## Notes Directory Structure

Whether you're using External/USB or Google Drive, TaskTriage expects this structure:

```
notes/
├── 20251225_074353.txt                  # Raw daily notes (text)
├── 20251226_083000.png                  # Raw daily notes (image)
├── 20251226_083000.raw_notes.txt        # Extracted text from PNG (auto-generated, editable)
├── 20251227_095000.pdf                  # Raw daily notes (PDF, single or multi-page)
├── 20251227_095000.raw_notes.txt        # Extracted text from PDF (auto-generated, editable)
├── daily/
│   ├── 25_12_2025.triaged.txt           # Generated analysis (DD_MM_YYYY.triaged.txt)
│   ├── 26_12_2025.triaged.txt           # Generated analysis
│   ├── 27_12_2025.triaged.txt           # Generated analysis
│   └── ...
├── weekly/
│   ├── week4_12_2025.triaged.txt        # Generated weekly analysis (weekN_MM_YYYY.triaged.txt)
│   └── ...
├── monthly/
│   ├── 12_2025.triaged.txt              # Generated monthly analysis (MM_YYYY.triaged.txt)
│   └── ...
└── annual/
    └── 2025.triaged.txt                 # Generated annual analysis (YYYY.triaged.txt)
```

### Supported File Formats

- **Text files**: `.txt`
- **Image files**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- **PDF files**: `.pdf` (single or multi-page documents)
- **Raw text files**: `.raw_notes.txt` (auto-generated from image/PDF analysis, editable and re-analyzable)

Image and PDF files get run through Claude's vision API to extract your handwritten text automatically:
- **Image files** are processed directly as images
- **PDF files** are converted to images page-by-page, each page is processed with the vision API, then all extracted text is concatenated with page separators

The extracted text is saved as a `.raw_notes.txt` file, making it easy to edit the text directly in the UI if needed. If you edit a `.raw_notes.txt` file after its initial analysis, TaskTriage will detect the change and automatically re-analyze it on the next run.

### Notes File Naming

Name your files with a timestamp prefix: `YYYYMMDD_HHMMSS.ext`

This lets TaskTriage figure out which file is most recent and which ones have already been analyzed.

### Task Notation

How to mark up your handwritten notes:
- **Completed tasks**: Add a checkmark (✓)
- **Removed/abandoned tasks**: Mark with an (✗)
- **Urgent tasks**: Add an asterisk (*)
- **Task ordering**: List tasks in any order—TaskTriage will automatically analyze and group them by theme (Communication, Planning, Implementation, Administrative, etc.) during analysis

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

# Context summarization flags
tasktriage --context              # Summarize projects before task analysis
tasktriage --context-only         # Only summarize projects, skip task analysis
tasktriage --force-context        # Force re-summarization even if unchanged
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
- **Sync Button** - The first step in the workflow:
  1. Copies raw notes (images, PDFs, text files) from input directories to output directory
  2. Converts images/PDFs to editable `.raw_notes.txt` files using Claude's vision API
  3. Syncs all files (analyses, raw notes) back to input directories and Google Drive
  - Provides real-time progress updates and comprehensive error reporting
- **Analyze Button** - Run the analysis pipeline on synced/converted files
  - Only processes files that have been synced (image/PDF files need their `.raw_notes.txt` created first)
  - Automatically triggers weekly/monthly/annual analyses when their conditions are met
- **Configuration** - Edit `.env` and `config.yaml` settings directly in the browser (API keys, notes source, model parameters)
- **Raw Notes List** - Browse `.txt` and image files from your root notes directory, sorted by date
  - **Open** - Load a selected note file for editing
  - **New** - Create a new empty `.txt` notes file with timestamp-based naming
- **Analysis Files List** - Browse all generated analysis files across daily/weekly/monthly/annual

**Right Panel (Editor)**
- Full-height text editor for viewing and editing selected files
- Image preview for handwritten note images
- Save/Revert buttons with unsaved changes indicator
- Notes source status display
- **Quick Markup Tools** - Easily add task markers (✓ completed, ✗ removed, * urgent, ↳ subtask), which are automatically interpreted at the right side of each line.

**Recommended Workflow:**
1. **Sync** - Import new files and convert images/PDFs to text
2. **Review/Edit** - Check the extracted `.raw_notes.txt` files and fix any OCR errors
3. **Analyze** - Generate daily analyses; weekly/monthly/annual analyses trigger automatically when conditions are met

### Output Directory and File Sync Workflow

TaskTriage uses a two-stage workflow for managing analysis files:

**Stage 1: Generation (Primary Output)**
All new analysis files and extracted raw notes are initially saved to `LOCAL_OUTPUT_DIR`. This is the "source of truth" for all generated files. This approach provides:
- A centralized location for all generated analyses
- A backup location for your analysis history
- Support for OAuth 2.0 authentication (full read/write access without service account limitations)

**Stage 2: Bidirectional Sync**
Once analyses are generated, you can use the **Sync button** in the web UI to perform true bidirectional synchronization between your output directory and all configured input directories:

**Outbound Sync** (Output → Input directories):
1. **To External/Local Directories**: Analysis files and raw notes are copied via standard file operations
2. **To Google Drive**: Files are uploaded to your configured Google Drive folder
3. **Real-time Progress**: The UI shows live progress updates and reports any errors

**Inbound Sync** (Input directories → Output):
1. **Consolidation**: Any new files found in your input directories are copied to the output directory
2. **Deduplication**: Files that already exist in the output directory are skipped
3. **Multi-source support**: If the same file exists in multiple input directories, it's only copied once

This bidirectional workflow ensures that:
- Your analyses are always backed up in `LOCAL_OUTPUT_DIR`
- Your note-taking device (USB/Supernote/reMarkable) stays synchronized with the latest analyses
- Google Drive users have full read/write access to upload and manage analyses on-demand
- New files added to any input location are automatically consolidated into your central output directory
- You have a true sync experience rather than one-directional file distribution

**When to Use Sync:**
- **Before analyzing new image/PDF files** - Sync converts them to editable `.raw_notes.txt` files
- **After running Analyze** - Distributes results to your devices and input directories
- Periodically to ensure all your locations (USB, local, Google Drive) stay in sync
- To consolidate notes from multiple input sources into your central output directory

### What Happens When You Run It

TaskTriage uses a two-step workflow with automatic cascading for higher-level analyses:

**STEP 1: Sync (run first)**

The Sync operation prepares your files for analysis:
1. Copies raw notes (images, PDFs, text files) from all input directories to the output directory
2. Converts images and PDFs to `.raw_notes.txt` files using Claude's vision API
   - **PDF Processing**: Multi-page PDFs are converted to images page-by-page, each page is processed, then all text is concatenated with page separators
3. Syncs all files back to input directories and Google Drive

**STEP 2: Analyze (when you're ready)**

Daily analyses only run when you explicitly press the Analyze button:
1. TaskTriage finds unanalyzed `.txt` files and `.raw_notes.txt` files (converted from images/PDFs)
   - Image/PDF files without a corresponding `.raw_notes.txt` are skipped (run Sync first!)
   - **Smart re-analysis**: Includes files that were edited after their last analysis
2. Processes them in parallel (up to 5 concurrent API calls)
3. Each file gets analyzed and saved as `daily/{date}.triaged.txt`
   - If re-analyzing an edited file, the new analysis **replaces** the old one (no duplicates)
4. Shows progress in real-time with success/failure indicators
5. Prints: `Daily Summary: X successful, Y failed`

**AUTOMATIC CASCADE: Weekly/Monthly/Annual Analyses**

After daily analyses complete, TaskTriage automatically checks for and triggers higher-level analyses:

**LEVEL 2: Weekly Analysis (auto-triggers when conditions are met)**

After all daily analyses complete, TaskTriage checks if any weeks need analysis. A weekly analysis is triggered automatically when:
- **5+ weekday analyses exist** for a work week (Monday-Friday), OR
- **The work week has passed** and at least 1 daily analysis exists for that week

When triggered:
1. Collects all daily analysis files from Monday-Friday of the qualifying week
2. Combines them with date labels
3. Generates a comprehensive weekly analysis looking at patterns and problems
4. Saves to `weekly/weekN_MM_YYYY.triaged.txt` (e.g., `week4_12_2025.triaged.txt`)
5. Prints: `Weekly Summary: X successful, Y failed`

**LEVEL 3: Monthly Analysis (auto-triggers when conditions are met)**

After all weekly analyses complete, TaskTriage checks if any months need analysis. A monthly analysis is triggered automatically when:
- **4+ weekly analyses exist** for a calendar month, OR
- **The calendar month has ended** and at least 1 weekly analysis exists for that month

When triggered:
1. Collects all weekly analysis files from the qualifying month
2. Combines them with week-range labels
3. Generates a comprehensive monthly analysis synthesizing strategic patterns across the entire month
4. Saves to `monthly/MM_YYYY.triaged.txt` (e.g., `12_2025.triaged.txt`)
5. Prints: `Monthly Summary: X successful, Y failed`

**LEVEL 4: Annual Analysis (auto-triggers when conditions are met)**

After all monthly analyses complete, TaskTriage checks if any years need analysis. An annual analysis is triggered automatically when:
- **12 monthly analyses exist** for a calendar year, OR
- **The calendar year has ended** and at least 1 monthly analysis exists for that year

When triggered:
1. Collects all monthly analysis files from the qualifying year
2. Combines them with month labels
3. Generates a comprehensive annual analysis synthesizing year-long accomplishments, learning, and strategic opportunities
4. Saves to `annual/YYYY.triaged.txt` (e.g., `2025.triaged.txt`)
5. Prints: `Annual Summary: X successful, Y failed`

**Summary**: Daily analyses require explicit triggering (Sync → Analyze), but weekly/monthly/annual analyses cascade automatically once their conditions are met!

## Task Notation Format

TaskTriage recognizes several special markers in your task lists that help identify task status and relationships. Use these notations to enhance your daily task lists:

### Task Status Markers (left side of task)

- **`✓` (checkmark)** - Task completed during the day
- **`✗` (or X)** - Task removed or abandoned during the day
- **No marker** - Standard task that was planned but not completed

### Subtask Marker

- **`↳` (rightwards arrow)** - Indicates a subtask directly related to the task above it. Subtasks are typically indented with spaces and represent work that supports or elaborates on the parent task.

Example:
```
✓ Jason 1:1
        ↳ CEO simulator
✗ meet w/ Matt C
        ↳ discuss Q1 plans
```

In this example:
- "Jason 1:1" was completed, and "CEO simulator" is the related subtask (also completed)
- "meet w/ Matt C" was abandoned, and "discuss Q1 plans" is the related subtask (also abandoned)

Subtasks are analyzed independently but with full context of their parent task relationship, allowing TaskTriage to understand the work structure and how parent-subtask pairs correlate with completion success.

### Priority Marker (right side of task)

- **`*` (asterisk)** - Marks urgent/high-priority tasks

Example:
```
✓ finish ECN bot fixes *
✗ ↳ meet w/ Matt C
```

This marks "finish ECN bot fixes" as critical/urgent.

## Project Context Summarization

TaskTriage can automatically summarize your project codebases to provide contextual knowledge about what you're working on. This enriches task analyses by helping Claude understand the technical landscape behind your tasks.

### How It Works

1. **Create `task_context.md`** in your TaskTriage repository root:

```markdown
# Project context paths (one per line)
# Comments start with #

# Auto-labeled by directory name
/home/user/repos/my-api
~/repos/frontend-app

# Or provide custom labels
backend: /home/user/repos/api-service
frontend: ~/repos/react-app
```

2. **Run context summarization**:

```bash
# Summarize all projects before normal analysis
tasktriage --context

# Only summarize projects, skip task analysis
tasktriage --context-only

# Force re-summarization even if unchanged
tasktriage --force-context
```

3. **Summaries are saved to `local_context/`**:

```
local_context/
├── my-api.context.md              # Human-readable summary
├── my-api.context.meta.json       # Change detection metadata
├── frontend-app.context.md
└── frontend-app.context.meta.json
```

### What Gets Summarized

For each project directory, TaskTriage:

- **Collects files** matching curated extensions (`.py`, `.js`, `.ts`, `.go`, `.md`, `.yaml`, `.json`, etc.) and known extensionless files (`Makefile`, `Dockerfile`, etc.)
- **Excludes** common directories (`.git`, `node_modules`, `venv`, `dist`, `build`, etc.)
- **Skips** large files (>100KB) and binary files
- **Prioritizes** important files (READMEs first, then config/build files, then source by depth)
- **Compiles** into a directory tree + file contents (up to 150K chars / ~37.5K tokens)
- **Summarizes** using Claude to produce structured analysis

### Summary Format

Each summary includes:

- **Purpose and Overview** - What the project does, who it's for, and the problem it solves
- **Technology Stack** - Languages, frameworks, runtime versions, and key libraries
- **Architecture Overview** - High-level components, how they interact, data flow
- **Key Patterns and Conventions** - Coding style, naming conventions, design patterns
- **Important Files and Entry Points** - Where to start reading, CLI/API entry points, config files
- **External Dependencies** - Services, APIs, databases, third-party integrations
- **Current State and Notable Concerns** - Technical debt, incomplete features, known issues

### Change Detection

TaskTriage tracks file modification times in `.context.meta.json` sidecar files and only re-summarizes when:

- No summary exists yet
- Files were added, removed, or modified
- You use `--force-context` to force re-summarization

This keeps costs low by avoiding redundant API calls when projects haven't changed.

### Context Matching: Semantic vs Keyword

TaskTriage offers two methods for matching task notes to relevant project contexts:

**Semantic Matching (Recommended)** uses machine learning embeddings to understand the meaning behind your tasks, not just keyword matches. It can identify relevant projects even when you use different terminology or describe work conceptually.

**Keyword Matching (Fallback)** uses weighted keyword scoring based on exact text matches: project labels (10 pts), primary keywords (3 pts), technologies (2.5 pts), task terms (2 pts), and related concepts (1 pt).

#### Enabling Semantic Matching

Install optional dependencies:

```bash
# Install with semantic matching support
pip install -e ".[semantic]"

# Or manually install
pip install sentence-transformers torch
```

The first time semantic matching runs, it downloads the `all-MiniLM-L6-v2` model (~80MB). This model:
- Generates 384-dimensional embeddings
- Runs fast on CPU (no GPU required)
- Provides high-quality semantic understanding

#### Matching Behavior

TaskTriage automatically uses the best available method:

- **With embeddings installed**: Uses semantic matching by default (more accurate)
- **Without embeddings**: Falls back to keyword matching (still effective)
- **Programmatic control**: Pass `inject_context_method` parameter:
  - `"auto"` (default): Try semantic, fall back to keyword
  - `"semantic"`: Use only semantic matching
  - `"keyword"`: Use only keyword matching

Example programmatic usage:

```python
from tasktriage import analyze_tasks

# Force semantic matching only
result = analyze_tasks(
    "daily",
    task_notes,
    inject_context_method="semantic"
)

# Force keyword matching only
result = analyze_tasks(
    "daily",
    task_notes,
    inject_context_method="keyword"
)
```

#### When Context Gets Injected

Context injection happens automatically for **daily analyses only** (not weekly/monthly/annual). The system:

1. Generates an embedding for your task notes (or extracts keywords)
2. Compares against all project summaries in `local_context/`
3. Selects top 2 most relevant projects (similarity ≥ 0.3 for semantic, score ≥ 3.0 for keyword)
4. Appends project summaries to your task notes before analysis

This adds ~43% more tokens per analysis (~1.44 cents per analysis with typical projects).

### Configuration

**File collection rules** (in `context.py`):

- **Included extensions**: `.py`, `.js`, `.ts`, `.go`, `.rs`, `.rb`, `.java`, `.md`, `.yaml`, `.json`, `.toml`, `.html`, `.css`, and many more
- **Known extensionless files**: `Makefile`, `Dockerfile`, `.gitignore`, `.env.example`, etc.
- **Excluded directories**: `.git`, `__pycache__`, `node_modules`, `venv`, `dist`, `build`, etc.
- **File size limit**: 100KB per file
- **Character budget**: 150,000 characters (~37.5K tokens) per project

**Labels** are sanitized for filesystem safety (path separators, traversal sequences, and unsafe characters are replaced with hyphens).

**Note**: Both `task_context.md` and `local_context/` are gitignored by default since they contain project-specific paths and generated summaries.

### Use Cases

- **Enrich task context**: When tasks reference specific projects, summaries provide technical context
- **Onboarding documentation**: Quickly understand unfamiliar codebases
- **Cross-project awareness**: Maintain awareness of multiple active projects
- **Planning accuracy**: Better task scoping when you understand project architecture

## Daily Analysis Output

The daily analysis gives you:

- **Completion Summary**: Clear breakdown of what was completed (✓), abandoned (✗), and left incomplete, with analysis of why each outcome occurred
- **Execution Patterns**: 3-5 concrete observations about which types of tasks succeed vs. fail, when your energy is highest, and what gets deferred
- **Task Categorization by Trend**: Automatic grouping of your tasks into thematic categories (Communication, Planning, Implementation, Administrative, Research/Learning, Meetings/Collaboration, Health/Wellness, Personal Projects, etc.) with completion rates and energy patterns per theme—reveals which categories of work consistently succeed vs. struggle
- **Priority Alignment Assessment**: Honest evaluation of whether urgent tasks were truly urgent, theme-based prioritization analysis, and what your completion patterns reveal about actual priorities vs. stated priorities
- **Workload Realism Evaluation**: Assessment of whether your planned workload was achievable, how accurate your time estimates were, and whether you stayed within healthy limits (6-7 hours focused work)
- **Task Design Quality**: Analysis of how task clarity, scope, and actionability influenced execution—identifying which tasks were well-designed vs. poorly-designed
- **Tomorrow's Priority Queue**: Ranked list of incomplete tasks for the next day, organized by priority tier (High/Medium/Lower) with rationales for each task's placement—informed by today's execution patterns
- **Key Takeaways**: 3-5 specific, actionable recommendations for improving future planning based on today's execution patterns, including theme-specific focus areas

## Weekly Analysis Output

The weekly analysis shows you:

- **Key Behavioral Findings**: Thematic success patterns (e.g., "Communication tasks completed 90%, Implementation tasks completed 40%") and how well daily priority queues predicted actual execution
- **Completion & follow-through analysis**: Where do you keep deferring stuff, organized by task theme?
- **Mis-prioritization detection**: What you said was important vs. what you actually did; theme-based priority failures (which themes were marked urgent but failed?)
- **Scope & estimation accuracy**: How wrong were your time estimates per theme? (It's okay, we're all bad at this)
- **Energy alignment analysis**: Are you scheduling high-energy tasks by theme when you're exhausted?
- **Corrected priority model** based on your actual behavior, organized by thematic task categories
- **Next-week planning strategy** with realistic capacity assumptions, theme-specific guidance, and recommended daily allocation across themes (e.g., "40% Communication, 30% Implementation, 20% Planning, 10% Administrative")

## Monthly Analysis Output

The monthly analysis synthesizes your entire month to show you:

- **Monthly achievements summary**: Major accomplishments organized by category (Work, Personal, System)
- **Strategic patterns and trends**: 3-5 month-level patterns including thematic completion trends (which task themes consistently succeeded vs. struggled?), execution rhythms, capacity trends, and priority accuracy
- **System evolution assessment**: Which weekly recommendations actually got implemented? Which ones worked? Did theme-specific improvements stick?
- **Persistent challenges**: Problems that survived multiple weekly corrections—organized by theme to reveal systemic issues in particular categories of work
- **Monthly performance metrics**: Completion rates (overall and per-theme), workload balance, priority alignment, energy management, planning quality, and theme-specific improvements
- **Strategic guidance for next month**: Month-level priorities, theme-based capacity allocation, theme-specific focus areas, and recommended daily distribution across themes
- **Long-term system refinements**: 3-6 fundamental changes to try in your planning system, informed by theme-specific insights

Monthly analyses are **strategic level**, not tactical. They reveal patterns invisible at the weekly level and help you understand which categories of work consistently succeed or struggle, plus your actual productivity rhythms over time.

## Annual Analysis Output

The annual analysis synthesizes your entire year to show you:

- **Year in accomplishments**: Your major wins and achievements across the full calendar year, organized by category and impact
- **Learning & skill development**: Areas where you've grown professionally and personally, with task execution mastery tracked by theme (e.g., "Communication efficiency improved 40% from Q1 to Q4")
- **Highest-impact opportunities**: 2-4 specific improvements ranked by ROI that would generate the most leverage in the year ahead, informed by theme-specific performance data and persistent challenges
- **Year-ahead strategic direction**: Recommendations for next year's focus areas, theme-based capacity allocation, seasonal patterns, and systemic changes based on your year's thematic performance

Annual analyses are **strategic and retrospective**. They help you see the big picture—what you actually accomplished beyond the day-to-day grind, which categories of work have the strongest ROI, and what's worth focusing on next year. This is where you look back at the full story of your year, track improvements in specific task themes, and plan next year's resource allocation.

## Directory Structure

TaskTriage organizes raw notes at the top level and analyses in subdirectories:

```
Notes/
├── 20251225_074353.txt                        # Your daily task notes (text)
├── 20251225_074353.raw_notes.txt              # Extracted text (auto-generated, editable)
├── 20251226_094500.png                        # Your daily task notes (image)
├── 20251226_094500.raw_notes.txt              # Extracted text from PNG (auto-generated)
├── 20251227_120000.pdf                        # Your daily task notes (PDF)
├── 20251227_120000.raw_notes.txt              # Extracted text from PDF (auto-generated)
├── daily/
│   ├── 25_12_2025.triaged.txt                 # Analysis output (DD_MM_YYYY.triaged.txt)
│   ├── 26_12_2025.triaged.txt                 # Analysis output
│   └── 27_12_2025.triaged.txt                 # Analysis output
├── weekly/
│   ├── week4_12_2025.triaged.txt              # Week 4 of Dec 2025 (weekN_MM_YYYY.triaged.txt)
│   └── week1_01_2026.triaged.txt              # Week 1 of Jan 2026
├── monthly/
│   ├── 12_2025.triaged.txt                    # December 2025 synthesis (MM_YYYY.triaged.txt)
│   └── 11_2025.triaged.txt                    # November 2025 synthesis
└── annual/
    └── 2025.triaged.txt                       # Full year 2025 synthesis (YYYY.triaged.txt)
```

Filename formats:
- **Daily notes**: `YYYYMMDD_HHMMSS.{txt|png|jpg|pdf|...}` (e.g., `20251225_074353.txt` or `20251225_074353.pdf`)
- **Raw text from images/PDFs**: `YYYYMMDD_HHMMSS.raw_notes.txt` (auto-generated when analyzing image or PDF files)
- **Daily analyses**: `DD_MM_YYYY.triaged.txt` (e.g., `25_12_2025.triaged.txt`)
- **Weekly analyses**: `weekN_MM_YYYY.triaged.txt` (e.g., `week4_12_2025.triaged.txt` for week 4 of December 2025)
- **Monthly analyses**: `MM_YYYY.triaged.txt` (e.g., `12_2025.triaged.txt` for December 2025)
- **Annual analyses**: `YYYY.triaged.txt` (e.g., `2025.triaged.txt` for full year 2025)

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
│   ├── files.py       # File I/O operations (External + Google Drive)
│   ├── gdrive.py      # Google Drive API integration
│   ├── context.py     # Project context collection and summarization
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
    get_context_summary_prompt,
    load_all_unanalyzed_task_notes,
    collect_weekly_analyses_for_week,
    collect_monthly_analyses_for_month,
    collect_annual_analyses_for_year,
    extract_text_from_image,
    extract_text_from_pdf,
    GoogleDriveClient,
    get_active_source,
    # Context summarization
    parse_context_file,
    collect_files,
    compile_content,
    needs_resummarization,
    summarize_context,
    summarize_all_contexts,
    CONTEXT_FILE_PATH,
    LOCAL_CONTEXT_DIR,
)

# Check which source is being used for output
print(f"Using: {get_active_source()}")  # "usb", "local", or "gdrive"

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

# Context summarization
from pathlib import Path

# Parse task_context.md to get project directories
entries = parse_context_file()  # Returns [(label, Path), ...]
for label, project_path in entries:
    print(f"Found project: {label} at {project_path}")

# Collect files from a project directory
project_files = collect_files(Path("/home/user/repos/my-api"))
# Returns [(relative_path, content), ...] sorted by path

# Compile files into LLM-ready format with token budget
compiled, omitted = compile_content(project_files, max_chars=150_000)
# Returns (compiled_content, list_of_omitted_paths)

# Check if a project needs re-summarization (mtime-based change detection)
needs_update = needs_resummarization("my-api", Path("/home/user/repos/my-api"))
print(f"Needs update: {needs_update}")

# Summarize a single project
summary_path, was_summarized = summarize_context(
    "my-api",
    Path("/home/user/repos/my-api"),
    force=False  # Set to True to force re-summarization
)
print(f"Summary: {summary_path}, Updated: {was_summarized}")

# Summarize all projects from task_context.md
results = summarize_all_contexts(force=False)
for label, summary_path, was_summarized in results:
    if summary_path:
        print(f"{label}: {'Updated' if was_summarized else 'Up to date'}")
    else:
        print(f"{label}: Failed")

# Use the Google Drive client directly with OAuth credentials
from tasktriage import get_oauth_credentials
credentials = get_oauth_credentials()  # Returns stored OAuth 2.0 credentials
client = GoogleDriveClient(credentials=credentials)
files = client.list_notes_files("daily")
```

## Troubleshooting

### Google Drive Issues

**"OAuth credentials required"**
- Make sure `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` are set in your `.env` file
- Authenticate via the web UI by clicking "Sign in with Google" in the Configuration section

**"Subfolder 'daily' not found in Google Drive folder"**
- You need to create `daily` and `weekly` subfolders in your Google Drive notes folder
- Make sure `GOOGLE_DRIVE_FOLDER_ID` points to the correct folder

**"Permission denied" errors**
- Make sure you've authenticated with Google Drive via the web UI
- Try revoking access at [Google Account Settings](https://myaccount.google.com/permissions) and re-authenticating

**"No unanalyzed notes files found"**
- Your notes files need to follow the naming format: `YYYYMMDD_HHMMSS.txt` or `.png`
- Make sure they're in the root notes directory (not in a subfolder)
- TaskTriage is looking for files that don't have a matching `.triaged.txt` file in the `daily/` subdirectory

### External/Local Directory Issues

**"No input directories configured or available"**
- Make sure at least one of `EXTERNAL_INPUT_DIR` or `LOCAL_INPUT_DIR` is set in your `.env` file
- Verify the paths are correct and the directories actually exist

**"USB directory not found"**
- Is your USB device actually plugged in and mounted?
- Check that the `EXTERNAL_INPUT_DIR` path in your `.env` file is correct and points to the right location
- Raw notes should be in the root directory; `daily/`, `weekly/`, `monthly/`, and `annual/` subdirectories are created automatically for analysis files

**"Local directory not found"**
- Verify the `LOCAL_INPUT_DIR` path exists
- Raw notes should be in the root directory; analysis subdirectories (`daily/`, `weekly/`, `monthly/`, `annual/`) are created automatically

### Re-Analysis and Editing Notes

**How do I fix mistakes in my analyzed notes?**
- Simply edit the `.txt` or `.raw_notes.txt` file in the UI or your text editor
- Save your changes
- Run the analysis again—TaskTriage automatically detects the file was modified after its analysis and will re-analyze it
- The new analysis **replaces** the old one (same filename), so you won't have duplicate analysis files

**What files trigger re-analysis?**
- `.txt` files that were modified after their `.triaged.txt` was created
- `.raw_notes.txt` files (extracted from images or PDFs) that were edited after their analysis
- The original image (`.png`, `.jpg`, etc.) or PDF (`.pdf`) file itself if it was replaced with a newer version

**When does re-analysis NOT happen?**
- If the notes file is older than its analysis file (no changes detected)
- For files without any existing analysis (these are treated as new files, not re-analysis)

## License

MIT
