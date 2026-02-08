"""
Context collection and summarization for TaskTriage.

Reads project directory paths from task_context.md, collects file contents,
submits them to Claude for summarization, and saves structured summaries
to local_context/. Change detection ensures directories are only
re-summarized when their contents change.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from langchain_anthropic import ChatAnthropic

from .config import (
    CONTEXT_FILE_PATH,
    LOCAL_CONTEXT_DIR,
    fetch_api_key,
    load_model_config,
    DEFAULT_MODEL,
)
from .prompts import get_context_summary_prompt, METADATA_EXTRACTION_PROMPT

# Extensions to include when collecting files
INCLUDED_EXTENSIONS = {
    # Source code
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".rb", ".java",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".zsh", ".fish",
    ".sql", ".r", ".R", ".jl", ".lua", ".pl", ".pm",
    # Config and data
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf",
    # Documentation
    ".md", ".rst", ".txt",
    # Web
    ".html", ".css", ".scss", ".sass", ".less",
    # Build and tooling
    ".lock", ".gradle", ".cmake",
}

# Known extensionless files to include
KNOWN_EXTENSIONLESS = {
    "Makefile", "Dockerfile", "Containerfile", "Procfile", "Gemfile",
    "Rakefile", "Vagrantfile", "Justfile",
    ".gitignore", ".gitattributes", ".dockerignore", ".editorconfig",
    ".eslintrc", ".prettierrc", ".babelrc",
    ".env.example", ".env.template",
}

# Directories to always exclude
EXCLUDED_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "env",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".eggs", ".next", ".nuxt",
    "target", "vendor", ".bundle", "coverage", ".coverage",
    "htmlcov", ".hypothesis", ".nox",
}

# Maximum file size in bytes (100KB)
MAX_FILE_SIZE = 100_000

# Default character budget for compiled content
DEFAULT_MAX_CHARS = 150_000


def _sanitize_label(label: str) -> str:
    """Sanitize a label for safe use as a filename component.

    Replaces path separators, path traversal sequences, and other
    filesystem-unsafe characters with hyphens. Strips leading/trailing
    whitespace and hyphens.
    """
    import re
    # Replace path separators and other unsafe chars with hyphens
    label = re.sub(r'[/\\:*?"<>|]', "-", label)
    # Collapse consecutive hyphens and dots that could cause traversal
    label = re.sub(r'\.\.+', ".", label)
    # Strip leading dots (hidden files / traversal) and whitespace
    label = label.strip().lstrip(".")
    # Collapse whitespace to hyphens
    label = re.sub(r'\s+', "-", label)
    # Collapse consecutive hyphens
    label = re.sub(r'-{2,}', "-", label)
    # Strip trailing hyphens
    label = label.strip("-")
    # Fallback if label is empty after sanitization
    if not label:
        label = "unnamed"
    return label


def parse_context_file(context_file_path: Path | None = None) -> list[tuple[str, Path]]:
    """Parse task_context.md to extract labeled directory paths.

    Format: One path per line. Lines starting with # are comments.
    Blank lines ignored. Optional labels via 'label: /path' syntax.
    Tilde expansion supported.

    Args:
        context_file_path: Path to context file. Defaults to CONTEXT_FILE_PATH.

    Returns:
        List of (label, path) tuples for valid directories.
    """
    if context_file_path is None:
        context_file_path = CONTEXT_FILE_PATH

    if not context_file_path.exists():
        return []

    entries = []
    content = context_file_path.read_text()

    for line in content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Parse optional label
        if ": " in line and not line.startswith("/") and not line.startswith("~"):
            label, path_str = line.split(": ", 1)
            label = label.strip()
            path_str = path_str.strip()
        else:
            path_str = line
            label = None

        # Expand tilde and resolve path
        path = Path(os.path.expanduser(path_str)).resolve()

        # Auto-derive label from directory basename if not provided
        if label is None:
            label = path.name

        # Sanitize label for filesystem safety
        label = _sanitize_label(label)

        # Only include existing directories
        if path.is_dir():
            entries.append((label, path))

    return entries


def _should_include_file(file_path: Path) -> bool:
    """Check if a file should be included based on extension and name."""
    if file_path.name in KNOWN_EXTENSIONLESS:
        return True
    return file_path.suffix.lower() in INCLUDED_EXTENSIONS


def _is_excluded_dir(dir_name: str) -> bool:
    """Check if a directory name should be excluded."""
    return dir_name in EXCLUDED_DIRS or dir_name.endswith(".egg-info")


def collect_files(directory: Path) -> list[tuple[Path, str]]:
    """Collect readable files from a directory matching inclusion criteria.

    Args:
        directory: Root directory to collect files from.

    Returns:
        List of (relative_path, content) tuples, sorted by path.
    """
    files = []

    for root, dirs, filenames in os.walk(directory):
        # Filter excluded directories in-place to prevent descending
        dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]

        for filename in filenames:
            file_path = Path(root) / filename

            if not _should_include_file(file_path):
                continue

            # Skip files over size limit
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            # Read as UTF-8, skip binary files
            try:
                content = file_path.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue

            rel_path = file_path.relative_to(directory)
            files.append((rel_path, content))

    # Sort by path for deterministic output
    files.sort(key=lambda x: x[0])
    return files


def _file_priority(rel_path: Path) -> tuple[int, int, str]:
    """Assign priority for file ordering in compiled content.

    Lower values = higher priority.
    Priority groups:
        0 - README files
        1 - Config/build files at root
        2 - Top-level source files
        3+ - Deeper files by depth
    """
    name_lower = rel_path.name.lower()
    depth = len(rel_path.parts) - 1  # 0 for top-level files

    if name_lower.startswith("readme"):
        return (0, depth, str(rel_path))

    config_names = {
        "pyproject.toml", "setup.py", "setup.cfg", "package.json",
        "cargo.toml", "go.mod", "gemfile", "makefile", "dockerfile",
        ".gitignore", "config.yaml", "config.yml", "config.json",
        "tsconfig.json", "requirements.txt", "poetry.lock",
    }
    if name_lower in config_names and depth == 0:
        return (1, depth, str(rel_path))

    if depth == 0:
        return (2, depth, str(rel_path))

    return (3 + depth, depth, str(rel_path))


def _build_tree(files: list[tuple[Path, str]]) -> str:
    """Build a directory tree listing from collected files."""
    dirs_seen = set()
    lines = []

    for rel_path, _ in files:
        # Add parent directories
        for i in range(len(rel_path.parts) - 1):
            dir_path = Path(*rel_path.parts[:i + 1])
            if dir_path not in dirs_seen:
                indent = "  " * i
                lines.append(f"{indent}{dir_path.name}/")
                dirs_seen.add(dir_path)

        # Add file
        indent = "  " * (len(rel_path.parts) - 1)
        lines.append(f"{indent}{rel_path.name}")

    return "\n".join(lines)


def compile_content(
    files: list[tuple[Path, str]],
    max_chars: int = DEFAULT_MAX_CHARS,
) -> tuple[str, list[Path]]:
    """Compile file contents into a single document for LLM consumption.

    Produces a directory tree followed by file contents in fenced code blocks.
    Files are prioritized: READMEs first, then config, then by depth.
    Stops adding files when character budget is exceeded.

    Args:
        files: List of (relative_path, content) tuples from collect_files.
        max_chars: Maximum character budget for the compiled output.

    Returns:
        Tuple of (compiled_content, list_of_omitted_paths).
    """
    if not files:
        return "", []

    # Build tree from all files (cheap, always include)
    tree = _build_tree(files)

    # Sort files by priority
    prioritized = sorted(files, key=lambda x: _file_priority(x[0]))

    sections = []
    sections.append("## Directory Structure\n")
    sections.append(f"```\n{tree}\n```\n")

    sections.append("\n## File Contents\n")

    current_chars = sum(len(s) for s in sections)
    included = []
    omitted = []

    for rel_path, content in prioritized:
        # Format this file's section
        file_section = f"\n### {rel_path}\n\n```\n{content}\n```\n"
        section_chars = len(file_section)

        if current_chars + section_chars > max_chars:
            omitted.append(rel_path)
        else:
            sections.append(file_section)
            current_chars += section_chars
            included.append(rel_path)

    # Append omitted files list if any
    if omitted:
        omitted_section = "\n### Omitted Files (exceeded token budget)\n\n"
        omitted_section += "\n".join(f"- {p}" for p in omitted)
        omitted_section += "\n"
        sections.append(omitted_section)

    return "".join(sections), omitted


def _get_meta_path(label: str, context_dir: Path | None = None) -> Path:
    """Get the path for a context metadata file."""
    if context_dir is None:
        context_dir = LOCAL_CONTEXT_DIR
    return context_dir / f"{label}.context.meta.json"


def _get_summary_path(label: str, context_dir: Path | None = None) -> Path:
    """Get the path for a context summary file."""
    if context_dir is None:
        context_dir = LOCAL_CONTEXT_DIR
    return context_dir / f"{label}.context.md"


def _build_file_mtimes(directory: Path, files: list[tuple[Path, str]]) -> dict[str, float]:
    """Build a dict of relative paths to their mtime values."""
    mtimes = {}
    for rel_path, _ in files:
        full_path = directory / rel_path
        try:
            mtimes[str(rel_path)] = full_path.stat().st_mtime
        except OSError:
            pass
    return mtimes


def _discover_file_mtimes(directory: Path) -> dict[str, float]:
    """Walk a directory and collect mtimes for eligible files without reading contents.

    This is a lightweight alternative to collect_files() + _build_file_mtimes()
    used for change detection, avoiding the cost of reading all file contents.
    Includes a quick UTF-8 probe (first 512 bytes) to match collect_files()
    behavior of skipping binary files.
    """
    mtimes = {}

    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if not _is_excluded_dir(d)]

        for filename in filenames:
            file_path = Path(root) / filename

            if not _should_include_file(file_path):
                continue

            try:
                stat = file_path.stat()
                if stat.st_size > MAX_FILE_SIZE:
                    continue
                # Quick binary check: probe first 512 bytes as UTF-8
                # to match collect_files() which skips non-UTF-8 files
                with open(file_path, "rb") as f:
                    chunk = f.read(512)
                chunk.decode("utf-8", errors="strict")
                rel_path = file_path.relative_to(directory)
                mtimes[str(rel_path)] = stat.st_mtime
            except (OSError, UnicodeDecodeError):
                continue

    return mtimes


def needs_resummarization(
    label: str,
    source_path: Path,
    context_dir: Path | None = None,
) -> bool:
    """Check if a project directory needs re-summarization.

    Checks:
    - No summary/manifest exists -> needs summarization
    - Any tracked file's mtime changed -> needs re-summarization
    - New files appeared matching collection criteria -> needs re-summarization
    - Previously tracked files deleted -> needs re-summarization

    Args:
        label: The project label.
        source_path: Path to the project directory.
        context_dir: Override for the context output directory.

    Returns:
        True if summarization is needed.
    """
    meta_path = _get_meta_path(label, context_dir)
    summary_path = _get_summary_path(label, context_dir)

    # No summary or manifest exists
    if not summary_path.exists() or not meta_path.exists():
        return True

    # Load existing manifest
    try:
        meta = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return True

    old_mtimes = meta.get("file_mtimes", {})

    # Lightweight discovery: only stat files, don't read contents
    current_mtimes = _discover_file_mtimes(source_path)

    # Check for new or deleted files
    if set(current_mtimes.keys()) != set(old_mtimes.keys()):
        return True

    # Check for modified files
    for path_str, mtime in current_mtimes.items():
        if old_mtimes.get(path_str) != mtime:
            return True

    return False


def _save_manifest(
    label: str,
    source_path: Path,
    files: list[tuple[Path, str]],
    file_mtimes: dict[str, float],
    files_omitted: list[Path],
    metadata: dict | None = None,
    context_dir: Path | None = None,
) -> Path:
    """Save the context metadata manifest.

    Args:
        label: Project label
        source_path: Path to source directory
        files: Collected files
        file_mtimes: File modification times
        files_omitted: Omitted file paths
        metadata: Structured metadata for task matching (optional)
        context_dir: Override context directory
    """
    if context_dir is None:
        context_dir = LOCAL_CONTEXT_DIR

    meta = {
        "source_path": str(source_path),
        "label": label,
        "summarized_at": datetime.now().isoformat(),
        "file_count": len(files),
        "total_chars": sum(len(content) for _, content in files),
        "files_omitted": len(files_omitted),
        "file_mtimes": file_mtimes,
    }

    if metadata:
        meta["metadata"] = metadata

    meta_path = _get_meta_path(label, context_dir)
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta_path


def _save_summary(
    label: str,
    source_path: Path,
    summary: str,
    file_count: int,
    files_omitted: int,
    context_dir: Path | None = None,
) -> Path:
    """Save the context summary with header metadata."""
    if context_dir is None:
        context_dir = LOCAL_CONTEXT_DIR

    header = (
        f"<!-- Context Summary: {label} -->\n"
        f"<!-- Source: {source_path} -->\n"
        f"<!-- Generated: {datetime.now().isoformat()} -->\n"
        f"<!-- Files analyzed: {file_count} | Files omitted: {files_omitted} -->\n\n"
        f"# Project Context: {label}\n\n"
    )

    summary_path = _get_summary_path(label, context_dir)
    summary_path.write_text(header + summary)
    return summary_path


def _extract_metadata(summary: str, api_key: str | None = None) -> dict:
    """Extract structured metadata from a context summary for task matching.

    Args:
        summary: The context summary text.
        api_key: Optional Anthropic API key.

    Returns:
        Dictionary with keys: primary_keywords, technologies, common_task_terms, related_concepts
    """
    from langchain_core.prompts import ChatPromptTemplate

    config = load_model_config()
    model = config.pop("model", DEFAULT_MODEL)
    config.pop("notes_source", None)

    # Use Haiku for metadata extraction (cheaper/faster)
    llm = ChatAnthropic(
        model="claude-haiku-4-5-20241022",
        api_key=fetch_api_key(api_key),
        **config,
    )

    prompt = ChatPromptTemplate.from_template(METADATA_EXTRACTION_PROMPT)
    chain = prompt | llm
    response = chain.invoke({"context_summary": summary})

    # Parse JSON response
    try:
        metadata = json.loads(response.content)
        # Validate structure
        required_keys = {"primary_keywords", "technologies", "common_task_terms", "related_concepts"}
        if not all(k in metadata for k in required_keys):
            raise ValueError(f"Missing required keys in metadata")
        return metadata
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback to empty metadata on parse failure
        print(f"Warning: Failed to parse metadata: {e}")
        return {
            "primary_keywords": [],
            "technologies": [],
            "common_task_terms": [],
            "related_concepts": [],
        }


def summarize_context(
    label: str,
    source_path: Path,
    force: bool = False,
    api_key: str | None = None,
) -> tuple[Path, bool]:
    """Summarize a single project directory.

    Args:
        label: The project label.
        source_path: Path to the project directory.
        force: Force re-summarization even if unchanged.
        api_key: Optional Anthropic API key.

    Returns:
        Tuple of (summary_path, was_summarized). was_summarized is False
        if the project was up to date and not force-refreshed.
    """
    context_dir = LOCAL_CONTEXT_DIR
    context_dir.mkdir(parents=True, exist_ok=True)

    # Check if summarization is needed
    if not force and not needs_resummarization(label, source_path):
        summary_path = _get_summary_path(label, context_dir)
        return summary_path, False

    # Collect and compile files
    files = collect_files(source_path)

    if not files:
        raise FileNotFoundError(f"No eligible files found in {source_path}")

    compiled, omitted = compile_content(files)
    file_mtimes = _build_file_mtimes(source_path, files)

    # Summarize via LLM
    config = load_model_config()
    model = config.pop("model", DEFAULT_MODEL)
    config.pop("notes_source", None)

    llm = ChatAnthropic(
        model=model,
        api_key=fetch_api_key(api_key),
        **config,
    )

    prompt = get_context_summary_prompt()
    chain = prompt | llm
    response = chain.invoke({"compiled_content": compiled})
    summary = response.content

    # Extract structured metadata for task matching
    metadata = _extract_metadata(summary, api_key)

    # Save outputs
    summary_path = _save_summary(
        label, source_path, summary, len(files), len(omitted), context_dir
    )
    _save_manifest(label, source_path, files, file_mtimes, omitted, metadata, context_dir)

    return summary_path, True


def select_relevant_contexts(
    task_notes: str,
    max_contexts: int = 3,
    score_threshold: float = 3.0,
    context_dir: Path | None = None,
) -> list[tuple[str, Path, float]]:
    """Select relevant project contexts based on task notes content.

    Uses weighted keyword matching against extracted metadata to identify
    which project contexts are most relevant to the given task notes.

    Args:
        task_notes: The daily task notes text to match against.
        max_contexts: Maximum number of contexts to return (default: 3).
        score_threshold: Minimum score required for inclusion (default: 3.0).
        context_dir: Override for context directory (default: LOCAL_CONTEXT_DIR).

    Returns:
        List of (label, summary_path, score) tuples, sorted by score descending.
        Empty list if no contexts match above threshold.
    """
    if context_dir is None:
        context_dir = LOCAL_CONTEXT_DIR

    if not context_dir.exists():
        return []

    # Load all context metadata files
    scores = {}
    task_lower = task_notes.lower()

    for meta_path in context_dir.glob("*.context.meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
            label = meta.get("label")
            metadata = meta.get("metadata", {})

            if not label or not metadata:
                continue

            # Weighted scoring
            score = 0.0

            # Direct label mention (highest weight)
            if label.lower() in task_lower:
                score += 10.0

            # Primary keywords (high weight)
            for keyword in metadata.get("primary_keywords", []):
                if keyword.lower() in task_lower:
                    score += 3.0

            # Technologies (medium-high weight)
            for tech in metadata.get("technologies", []):
                if tech.lower() in task_lower:
                    score += 2.5

            # Common task terms (medium weight)
            for term in metadata.get("common_task_terms", []):
                if term.lower() in task_lower:
                    score += 2.0

            # Related concepts (lower weight)
            for concept in metadata.get("related_concepts", []):
                if concept.lower() in task_lower:
                    score += 1.0

            if score >= score_threshold:
                summary_path = _get_summary_path(label, context_dir)
                if summary_path.exists():
                    scores[label] = (summary_path, score)

        except (json.JSONDecodeError, OSError, KeyError):
            continue

    # Sort by score descending and limit
    sorted_contexts = sorted(scores.items(), key=lambda x: x[1][1], reverse=True)
    return [(label, path, score) for label, (path, score) in sorted_contexts[:max_contexts]]


def summarize_all_contexts(
    force: bool = False,
    api_key: str | None = None,
) -> list[tuple[str, Path, bool]]:
    """Summarize all project directories listed in task_context.md.

    Args:
        force: Force re-summarization even if unchanged.
        api_key: Optional Anthropic API key.

    Returns:
        List of (label, summary_path, was_summarized) tuples.
    """
    entries = parse_context_file()

    if not entries:
        return []

    results = []
    for label, source_path in entries:
        try:
            summary_path, was_summarized = summarize_context(
                label, source_path, force=force, api_key=api_key
            )
            results.append((label, summary_path, was_summarized))
        except Exception as e:
            # Store error info but continue processing other entries
            print(f"  \u2717 Failed to summarize '{label}': {e}")
            results.append((label, None, False))

    return results
