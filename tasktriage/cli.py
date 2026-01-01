#!/usr/bin/env python3
"""
Command-line interface for TaskTriage.

Provides the main entry point for analyzing daily and weekly task notes.
"""

import argparse
import sys

from .analysis import analyze_tasks
from .files import load_task_notes, collect_weekly_analyses, save_analysis, get_notes_source
from .image import IMAGE_EXTENSIONS


def main():
    """Main CLI entry point for task analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze daily task notes and generate an execution plan"
    )
    parser.add_argument(
        "--type",
        type=str,
        default="daily",
        help="Analysis type: daily or weekly (default: daily)"
    )

    args = parser.parse_args()

    try:
        # Show which notes source is being used
        source = get_notes_source()
        source_label = "Google Drive" if source == "gdrive" else "USB/Local"
        print(f"Using notes source: {source_label}\n")

        if args.type == "weekly":
            # Collect previous week's daily analyses
            task_notes, notes_path, week_start, week_end = collect_weekly_analyses()
            print(f"Collecting daily analyses for weekly review...\n")

            # Format dates for the prompt
            prompt_vars = {
                "week_start": week_start.strftime("%A, %B %d, %Y"),
                "week_end": week_end.strftime("%A, %B %d, %Y"),
            }
        else:
            task_notes, notes_path, file_date = load_task_notes(args.type)

            # Indicate if text was extracted from an image
            if notes_path.suffix.lower() in IMAGE_EXTENSIONS:
                print(f"Extracted text from image: {notes_path.name}")
            print(f"Analyzing daily tasks: {notes_path.name}\n")

            # Format date for the prompt
            prompt_vars = {
                "current_date": file_date.strftime("%A, %B %d, %Y"),
            }

        result = analyze_tasks(args.type, task_notes, **prompt_vars)

        output_path = save_analysis(result, notes_path, args.type)
        print(f"\nAnalysis saved to: {output_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
