"""
Core analysis functionality for TaskTriage.

Uses Claude via LangChain to analyze task notes and generate execution plans.
"""

from pathlib import Path

from langchain_anthropic import ChatAnthropic

from .config import fetch_api_key, load_model_config, DEFAULT_MODEL
from .prompts import get_daily_prompt, get_weekly_prompt, get_monthly_prompt, get_annual_prompt


def _build_context_section(selected_contexts: list[tuple[str, Path, float]]) -> str:
    """Build the context section to inject into the prompt.

    Args:
        selected_contexts: List of (label, summary_path, score) tuples

    Returns:
        Formatted context section with project summaries
    """
    if not selected_contexts:
        return ""

    lines = ["\n## Relevant Project Context\n"]
    lines.append("The following project contexts are relevant to today's tasks:\n")

    for label, summary_path, score in selected_contexts:
        try:
            summary = summary_path.read_text()
            # Extract just the content (skip HTML comments and title)
            content_lines = []
            skip_header = True
            for line in summary.split("\n"):
                if skip_header and line.startswith("# Project Context:"):
                    skip_header = False
                    continue
                if not skip_header and not line.startswith("<!--"):
                    content_lines.append(line)

            context_content = "\n".join(content_lines).strip()
            lines.append(f"\n### Project: {label}\n")
            lines.append(f"{context_content}\n")
        except OSError:
            continue

    return "\n".join(lines)


def analyze_tasks(
    analysis_type: str,
    task_notes: str,
    api_key: str | None = None,
    inject_context: bool = True,
    inject_context_method: str = "auto",
    verbose: bool = True,
    **prompt_vars
) -> str:
    """Analyze task notes using Claude via LangChain.

    Args:
        analysis_type: Type of analysis ("daily", "weekly", "monthly", or "annual")
        task_notes: The task notes to analyze
        api_key: Optional Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        inject_context: Whether to inject relevant project contexts (default: True, only for daily)
        inject_context_method: Method for context selection (default: "auto")
            - "auto": Try semantic matching first, fall back to keyword matching
            - "semantic": Use only semantic matching (embeddings)
            - "keyword": Use only keyword matching
        verbose: Whether to print context matching messages (default: True)
        **prompt_vars: Variables to inject into the prompt template
            - For daily: current_date (str)
            - For weekly: week_start (str), week_end (str)
            - For monthly: month_start (str), month_end (str)
            - For annual: year (str)

    Returns:
        The analysis and execution plan

    Raises:
        ValueError: If inject_context_method is not one of: "auto", "semantic", "keyword"
    """
    # Validate inject_context_method
    valid_methods = {"auto", "semantic", "keyword"}
    if inject_context_method not in valid_methods:
        raise ValueError(
            f"Invalid inject_context_method: {inject_context_method}. "
            f"Must be one of: {', '.join(sorted(valid_methods))}"
        )
    config = load_model_config()

    # Extract model from config or use default
    model = config.pop("model", DEFAULT_MODEL)

    # Remove non-ChatAnthropic configuration keys
    # notes_source is a tasktriage-specific config, not a ChatAnthropic parameter
    config.pop("notes_source", None)

    # Build ChatAnthropic with config parameters
    llm = ChatAnthropic(
        model=model,
        api_key=fetch_api_key(api_key),
        **config
    )

    # Inject project context for daily analysis (if enabled and available)
    enriched_task_notes = task_notes
    if analysis_type == "daily" and inject_context:
        try:
            from .context import (
                select_relevant_contexts,
                select_relevant_contexts_semantic,
                DEFAULT_MAX_CONTEXTS,
                SEMANTIC_SIMILARITY_THRESHOLD,
                KEYWORD_SCORE_THRESHOLD,
            )

            selected_contexts = []

            # Try semantic matching first (auto or semantic)
            if inject_context_method in ("auto", "semantic"):
                selected_contexts = select_relevant_contexts_semantic(
                    task_notes,
                    max_contexts=DEFAULT_MAX_CONTEXTS,
                    score_threshold=SEMANTIC_SIMILARITY_THRESHOLD,
                )
                if selected_contexts and inject_context_method == "auto" and verbose:
                    print("  Using semantic context matching")

            # Fall back to keyword matching if needed (auto with no semantic results, or explicit keyword)
            if not selected_contexts and inject_context_method in ("auto", "keyword"):
                selected_contexts = select_relevant_contexts(
                    task_notes,
                    max_contexts=DEFAULT_MAX_CONTEXTS,
                    score_threshold=KEYWORD_SCORE_THRESHOLD,
                )
                if selected_contexts and inject_context_method == "auto" and verbose:
                    print("  Using keyword context matching (semantic unavailable)")

            if selected_contexts:
                context_section = _build_context_section(selected_contexts)
                enriched_task_notes = f"{task_notes}{context_section}"
        except Exception as e:
            # Context injection is optional - proceed without if it fails
            if verbose:
                print(f"Warning: Context injection failed: {e}")

    # Get the appropriate prompt template
    if analysis_type == "annual":
        prompt = get_annual_prompt()
    elif analysis_type == "monthly":
        prompt = get_monthly_prompt()
    elif analysis_type == "weekly":
        prompt = get_weekly_prompt()
    else:
        prompt = get_daily_prompt()

    # Create the chain: prompt | llm
    chain = prompt | llm

    # Invoke with task_notes and any additional prompt variables
    response = chain.invoke({"task_notes": enriched_task_notes, **prompt_vars})
    return response.content
