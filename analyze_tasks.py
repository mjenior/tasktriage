#!/usr/bin/env python3
"""
Daily Task Analyzer

Analyzes daily task notes using Claude via LangChain and generates
an actionable execution plan based on GTD principles.
"""

import argparse
import sys
import os
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


def fetch_api_key(api_key: str | None = None) -> str:
    """Get Anthropic API key"""
    if api_key:
        return api_key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return api_key




def load_system_prompt(prompt_path: Path) -> str:
    """Load the system prompt from a file."""
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found: {prompt_path}")
    return prompt_path.read_text()


def load_task_notes(notes_path: Path) -> str:
    """Load the daily task notes from a file."""
    if not notes_path.exists():
        raise FileNotFoundError(f"Task notes file not found: {notes_path}")
    return notes_path.read_text()


def analyze_tasks(system_prompt: str, task_notes: str, model: str = "claude-haiku-4-5-20241022", api_key: str | None = None) -> str:
    """
    Analyze task notes using Claude via LangChain.

    Args:
        system_prompt: The system instructions for the assistant
        task_notes: The daily task notes to analyze
        model: The Claude model to use
        api_key: Optional Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)

    Returns:
        The analysis and execution plan
    """
    llm = ChatAnthropic(model=model, api_key=fetch_api_key(api_key))

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Please analyze the following daily task notes and create an execution plan:\n\n{task_notes}")
    ]

    response = llm.invoke(messages)
    return response.content


def main():
    parser = argparse.ArgumentParser(
        description="Analyze daily task notes and generate an execution plan"
    )
    parser.add_argument(
        "notes_file",
        type=Path,
        help="Path to the daily task notes file"
    )
    parser.add_argument(
        "--prompt",
        type=Path,
        default=Path(__file__).parent / "prompts" / "daily.txt",
        help="Path to the system prompt file (default: prompts/daily.txt)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-haiku-4-5-20241022",
        help="Claude model to use (default: claude-haiku-4-5-20241022)"
    )

    args = parser.parse_args()

    try:
        system_prompt = load_system_prompt(args.prompt)
        task_notes = load_task_notes(args.notes_file)

        print("Analyzing tasks...\n")
        result = analyze_tasks(system_prompt, task_notes, args.model)
        print(result)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
