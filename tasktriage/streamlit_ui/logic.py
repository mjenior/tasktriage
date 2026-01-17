"""
Business logic for UI operations.

Contains the core business logic for triage pipeline and file synchronization,
with progress callbacks for UI updates.
"""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from shutil import copy2

from tasktriage import (
    analyze_tasks,
    load_all_unanalyzed_task_notes,
    collect_weekly_analyses_for_week,
    collect_monthly_analyses_for_month,
    collect_annual_analyses_for_year,
    save_analysis,
)
from tasktriage.cli import analyze_single_file
from tasktriage.files import (
    _find_weeks_needing_analysis,
    _find_months_needing_analysis,
    _find_years_needing_analysis,
    convert_visual_files_in_directory,
)
from tasktriage.config import get_all_input_directories, is_gdrive_available


def run_triage_pipeline(progress_callback) -> dict:
    """Run the full triage analysis pipeline.

    Args:
        progress_callback: Function to call with progress updates

    Returns:
        Dictionary with results for each analysis level
    """
    results = {
        "daily": {"successful": 0, "failed": 0, "errors": []},
        "weekly": {"successful": 0, "failed": 0, "errors": []},
        "monthly": {"successful": 0, "failed": 0, "errors": []},
        "annual": {"successful": 0, "failed": 0, "errors": []},
    }

    # Level 1: Daily analyses
    progress_callback("Loading unanalyzed daily files...")
    try:
        unanalyzed_files = load_all_unanalyzed_task_notes("daily", "png")
        total_files = len(unanalyzed_files)
        progress_callback(f"Found {total_files} unanalyzed file(s)")
    except FileNotFoundError:
        # No unanalyzed files - this is OK, proceed to check weekly/monthly/annual
        unanalyzed_files = []
        total_files = 0
        progress_callback("No unanalyzed daily files found (image/PDF files require Sync first)")
    except Exception as e:
        progress_callback(f"Error loading files: {e}")
        # Continue to check for weekly/monthly/annual even if daily loading fails
        unanalyzed_files = []
        total_files = 0

    if total_files > 0:
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(
                    analyze_single_file, task_notes, notes_path, file_date, "daily", True
                ): notes_path
                for task_notes, notes_path, file_date in unanalyzed_files
            }

            completed = 0
            for future in as_completed(future_to_file):
                notes_path, output_path, success, error_msg, raw_text_path = future.result()
                completed += 1

                if success:
                    results["daily"]["successful"] += 1
                    msg = f"Processing daily notes... ({completed}/{total_files}) - {notes_path.name}"
                    if raw_text_path:
                        msg += " (+ raw text)"
                    progress_callback(msg)
                else:
                    results["daily"]["failed"] += 1
                    results["daily"]["errors"].append(f"{notes_path.name}: {error_msg}")
                    progress_callback(f"Failed: {notes_path.name}")

    progress_callback(f"Daily Summary: {results['daily']['successful']} successful, {results['daily']['failed']} failed")

    # Level 2: Weekly analyses
    progress_callback("Checking for weekly analyses...")
    try:
        weeks_to_analyze = _find_weeks_needing_analysis()
    except Exception:
        weeks_to_analyze = []

    for week_start, week_end in weeks_to_analyze:
        week_label = week_start.strftime("%B %d") + " - " + week_end.strftime("%B %d, %Y")
        progress_callback(f"Analyzing week: {week_label}")

        try:
            task_notes, notes_path, ws, we = collect_weekly_analyses_for_week(week_start, week_end)
            prompt_vars = {
                "week_start": ws.strftime("%A, %B %d, %Y"),
                "week_end": we.strftime("%A, %B %d, %Y"),
            }
            result = analyze_tasks("weekly", task_notes, **prompt_vars)
            save_analysis(result, notes_path, "weekly")
            results["weekly"]["successful"] += 1
        except Exception as e:
            results["weekly"]["failed"] += 1
            results["weekly"]["errors"].append(f"{week_label}: {str(e)}")

    if weeks_to_analyze:
        progress_callback(f"Weekly Summary: {results['weekly']['successful']} successful, {results['weekly']['failed']} failed")

    # Level 3: Monthly analyses
    progress_callback("Checking for monthly analyses...")
    try:
        months_to_analyze = _find_months_needing_analysis()
    except Exception:
        months_to_analyze = []

    for month_start, month_end in months_to_analyze:
        month_label = month_start.strftime("%B %Y")
        progress_callback(f"Analyzing month: {month_label}")

        try:
            task_notes, notes_path, ms, me = collect_monthly_analyses_for_month(month_start, month_end)
            prompt_vars = {
                "month_start": ms.strftime("%B %d, %Y"),
                "month_end": me.strftime("%B %d, %Y"),
            }
            result = analyze_tasks("monthly", task_notes, **prompt_vars)
            save_analysis(result, notes_path, "monthly")
            results["monthly"]["successful"] += 1
        except Exception as e:
            results["monthly"]["failed"] += 1
            results["monthly"]["errors"].append(f"{month_label}: {str(e)}")

    if months_to_analyze:
        progress_callback(f"Monthly Summary: {results['monthly']['successful']} successful, {results['monthly']['failed']} failed")

    # Level 4: Annual analyses
    progress_callback("Checking for annual analyses...")
    try:
        years_to_analyze = _find_years_needing_analysis()
    except Exception:
        years_to_analyze = []

    for year in years_to_analyze:
        progress_callback(f"Analyzing year: {year}")

        try:
            task_notes, notes_path, yr = collect_annual_analyses_for_year(year)
            prompt_vars = {"year": str(year)}
            result = analyze_tasks("annual", task_notes, **prompt_vars)
            save_analysis(result, notes_path, "annual")
            results["annual"]["successful"] += 1
        except Exception as e:
            results["annual"]["failed"] += 1
            results["annual"]["errors"].append(f"{year}: {str(e)}")

    if years_to_analyze:
        progress_callback(f"Annual Summary: {results['annual']['successful']} successful, {results['annual']['failed']} failed")

    progress_callback("Triage complete!")
    return results


def _sync_raw_notes_to_output(
    output_dir: Path,
    input_dirs: list[Path],
    progress_callback
) -> tuple[int, set[str], list[str]]:
    """Phase 0: Copy raw notes from input directories to output directory.

    Args:
        output_dir: Output directory path
        input_dirs: List of input directory paths
        progress_callback: Function for progress updates

    Returns:
        Tuple of (synced_count, raw_files_copied_names, errors)
    """
    valid_extensions = {".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}
    raw_files_copied = set()
    errors = []
    synced_count = 0

    for input_dir in input_dirs:
        if not input_dir.exists():
            continue

        # Find all raw note files at top level of input directory
        for file_path in input_dir.iterdir():
            if not file_path.is_file():
                continue

            # Only process valid extensions
            if file_path.suffix.lower() not in valid_extensions:
                continue

            # Skip analysis files and raw_notes files (we want original sources)
            if ".triaged.txt" in file_path.name or ".raw_notes.txt" in file_path.name:
                continue

            # Skip if we've already copied a file with this name
            if file_path.name in raw_files_copied:
                continue

            target_path = output_dir / file_path.name

            # Skip if file already exists in output directory
            if target_path.exists():
                continue

            try:
                copy2(file_path, target_path)
                synced_count += 1
                raw_files_copied.add(file_path.name)

                if progress_callback:
                    progress_callback(f"Copied raw: {file_path.name}")

            except Exception as e:
                error_msg = f"Failed to copy {file_path.name}: {str(e)}"
                errors.append(error_msg)
                if progress_callback:
                    progress_callback(f"Error copying: {file_path.name}")

    return synced_count, raw_files_copied, errors


def _convert_visual_files(output_dir: Path, progress_callback) -> dict:
    """Phase 0.5: Convert visual files to .raw_notes.txt using Claude API.

    Args:
        output_dir: Output directory path
        progress_callback: Function for progress updates

    Returns:
        Dictionary with conversion statistics
    """
    if progress_callback:
        progress_callback("Converting visual files to text...")

    conversion_stats = convert_visual_files_in_directory(output_dir, progress_callback)

    if conversion_stats["converted"] > 0:
        if progress_callback:
            progress_callback(f"Converted {conversion_stats['converted']} visual file(s)")

    return conversion_stats


def _sync_output_to_inputs(
    output_dir: Path,
    input_dirs: list[Path],
    progress_callback
) -> tuple[int, list[str]]:
    """Phase 1: Sync FROM output directory TO input directories.

    Args:
        output_dir: Output directory path
        input_dirs: List of input directory paths
        progress_callback: Function for progress updates

    Returns:
        Tuple of (synced_count, errors)
    """
    synced_count = 0
    errors = []

    # Get all files to sync (analysis files and raw notes from subdirs)
    files_from_output = []
    for subdir in ["daily", "weekly", "monthly", "annual"]:
        subdir_path = output_dir / subdir
        if subdir_path.exists():
            # Get analysis files (all now use triaged naming)
            files_from_output.extend(subdir_path.glob("*.triaged.txt"))
            # Get raw notes files from subdirs
            files_from_output.extend(subdir_path.glob("*.raw_notes.txt"))

    # Also get top-level raw_notes.txt files (created by conversion)
    files_from_output.extend(output_dir.glob("*.raw_notes.txt"))

    if progress_callback:
        progress_callback("Syncing output files to input directories...")

    for file_path in files_from_output:
        # Determine which subdirectory this file belongs to
        parent_name = file_path.parent.name

        # Check if this is a top-level file (parent is output_dir itself)
        is_top_level = file_path.parent == output_dir

        for input_dir in input_dirs:
            if is_top_level:
                # Top-level files go to top level of input directories
                target_path = input_dir / file_path.name
            else:
                # Subdirectory files go to corresponding subdirectory
                target_dir = input_dir / parent_name
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / file_path.name

            try:
                # Copy file
                copy2(file_path, target_path)
                synced_count += 1

                if progress_callback:
                    progress_callback(f"Synced: {file_path.name}")

            except Exception as e:
                error_msg = f"Failed to sync {file_path.name} to {input_dir}: {str(e)}"
                errors.append(error_msg)
                if progress_callback:
                    progress_callback(f"Error: {file_path.name}")

    return synced_count, errors


def _sync_inputs_to_output(
    output_dir: Path,
    input_dirs: list[Path],
    progress_callback
) -> tuple[int, list[str]]:
    """Phase 2: Sync FROM input directories TO output directory.

    Args:
        output_dir: Output directory path
        input_dirs: List of input directory paths
        progress_callback: Function for progress updates

    Returns:
        Tuple of (synced_count, errors)
    """
    synced_count = 0
    errors = []
    files_copied_from_input = set()

    if progress_callback:
        progress_callback("Syncing new files from input directories...")

    for input_dir in input_dirs:
        for subdir in ["daily", "weekly", "monthly", "annual"]:
            input_subdir = input_dir / subdir
            if not input_subdir.exists():
                continue

            # Find all files in this input subdirectory
            for file_path in input_subdir.iterdir():
                if not file_path.is_file():
                    continue

                output_subdir = output_dir / subdir
                output_file_path = output_subdir / file_path.name

                # Skip if file already exists in output directory
                if output_file_path.exists():
                    continue

                # Skip if we already copied this file (from another input directory)
                file_key = (subdir, file_path.name)
                if file_key in files_copied_from_input:
                    continue

                try:
                    # Create output subdirectory if it doesn't exist
                    output_subdir.mkdir(parents=True, exist_ok=True)

                    # Copy file from input to output
                    copy2(file_path, output_file_path)
                    synced_count += 1
                    files_copied_from_input.add(file_key)

                    if progress_callback:
                        progress_callback(f"Synced from input: {file_path.name}")

                except Exception as e:
                    error_msg = f"Failed to sync {file_path.name} from {input_dir}: {str(e)}"
                    errors.append(error_msg)
                    if progress_callback:
                        progress_callback(f"Error copying from input: {file_path.name}")

    return synced_count, errors


def _sync_to_gdrive(files_from_output: list[Path], progress_callback) -> tuple[int, list[str]]:
    """Phase 3: Sync to Google Drive if available.

    Args:
        files_from_output: List of file paths to sync
        progress_callback: Function for progress updates

    Returns:
        Tuple of (synced_count, errors)
    """
    synced_count = 0
    errors = []

    if not is_gdrive_available():
        return synced_count, errors

    try:
        from tasktriage.gdrive import GoogleDriveClient
        from .oauth_ui import get_oauth_manager

        # Get OAuth credentials
        oauth_mgr = get_oauth_manager()
        credentials = oauth_mgr.load_credentials()

        if not credentials:
            info_msg = "Google Drive sync skipped: Not authenticated. Please sign in with Google."
            errors.append(info_msg)
            if progress_callback:
                progress_callback(info_msg)
            return synced_count, errors

        # Create client with OAuth credentials
        client = GoogleDriveClient(credentials=credentials)

        if progress_callback:
            progress_callback("Syncing to Google Drive...")

        for file_path in files_from_output:
            subdir_name = file_path.parent.name
            file_content = file_path.read_text()

            try:
                client.upload_file(subdir_name, file_path.name, file_content)
                synced_count += 1
                if progress_callback:
                    progress_callback(f"Synced to GDrive: {file_path.name}")
            except Exception as e:
                error_msg = f"Failed to sync {file_path.name} to Google Drive: {str(e)}"
                errors.append(error_msg)
                if progress_callback:
                    progress_callback(f"GDrive error: {file_path.name}")

    except Exception as e:
        error_msg = f"Google Drive sync failed: {str(e)}"
        errors.append(error_msg)

    return synced_count, errors


def sync_files_across_directories(output_dir: Path, progress_callback=None) -> dict:
    """Sync files bidirectionally between output directory and all configured input directories.

    This performs a true sync operation:
    1. Copies raw notes (images, PDFs, text) from input directories to output directory
    2. Converts visual files (images, PDFs) to .raw_notes.txt using Claude API
    3. Copies analysis files and raw notes from output directory to all input directories
    4. Optionally syncs to Google Drive

    Args:
        output_dir: The output directory where files are currently saved
        progress_callback: Optional callback function for progress updates

    Returns:
        Dictionary with sync statistics: {total: int, synced: int, converted: int, errors: list}
    """
    stats = {"total": 0, "synced": 0, "converted": 0, "errors": []}

    if not output_dir or not output_dir.exists():
        if progress_callback:
            progress_callback("Output directory not found")
        return stats

    # Get all configured input directories
    input_dirs = get_all_input_directories()

    # Phase 0: Copy raw notes FROM input directories TO output directory
    if progress_callback:
        progress_callback("Copying raw notes from input directories...")

    synced, raw_files_copied, errors = _sync_raw_notes_to_output(
        output_dir, input_dirs, progress_callback
    )
    stats["synced"] += synced
    stats["errors"].extend(errors)

    # Phase 0.5: Convert visual files to .raw_notes.txt
    conversion_stats = _convert_visual_files(output_dir, progress_callback)
    stats["converted"] = conversion_stats["converted"]
    stats["errors"].extend(conversion_stats["errors"])

    # Phase 1: Sync FROM output directory TO input directories
    synced, errors = _sync_output_to_inputs(output_dir, input_dirs, progress_callback)
    stats["synced"] += synced
    stats["errors"].extend(errors)

    # Phase 2: Sync FROM input directories TO output directory
    synced, errors = _sync_inputs_to_output(output_dir, input_dirs, progress_callback)
    stats["synced"] += synced
    stats["errors"].extend(errors)

    # Get list of files to sync to Google Drive
    files_from_output = []
    for subdir in ["daily", "weekly", "monthly", "annual"]:
        subdir_path = output_dir / subdir
        if subdir_path.exists():
            files_from_output.extend(subdir_path.glob("*.triaged.txt"))
            files_from_output.extend(subdir_path.glob("*.raw_notes.txt"))
    files_from_output.extend(output_dir.glob("*.raw_notes.txt"))

    # Phase 3: Sync to Google Drive
    synced, errors = _sync_to_gdrive(files_from_output, progress_callback)
    stats["synced"] += synced
    stats["errors"].extend(errors)

    stats["total"] = stats["synced"]

    return stats
