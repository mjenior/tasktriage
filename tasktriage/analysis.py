"""
Core analysis functionality for TaskTriage.

Uses Claude via LangChain to analyze task notes and generate execution plans.
"""

from langchain_anthropic import ChatAnthropic

from .config import fetch_api_key, load_model_config, DEFAULT_MODEL
from .prompts import get_daily_prompt, get_weekly_prompt, get_monthly_prompt, get_annual_prompt


def analyze_tasks(
    analysis_type: str,
    task_notes: str,
    api_key: str | None = None,
    **prompt_vars
) -> str:
    """Analyze task notes using Claude via LangChain.

    Args:
        analysis_type: Type of analysis ("daily", "weekly", "monthly", or "annual")
        task_notes: The task notes to analyze
        api_key: Optional Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        **prompt_vars: Variables to inject into the prompt template
            - For daily: current_date (str)
            - For weekly: week_start (str), week_end (str)
            - For monthly: month_start (str), month_end (str)
            - For annual: year (str)

    Returns:
        The analysis and execution plan
    """
    config = load_model_config()

    # Extract model from config or use default
    model = config.pop("model", DEFAULT_MODEL)

    # Build ChatAnthropic with config parameters
    llm = ChatAnthropic(
        model=model,
        api_key=fetch_api_key(api_key),
        **config
    )

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
    response = chain.invoke({"task_notes": task_notes, **prompt_vars})
    return response.content
