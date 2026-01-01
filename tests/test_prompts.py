"""
Tests for tasker.prompts module.
"""

import pytest
from langchain_core.prompts import ChatPromptTemplate


class TestDailyPrompt:
    """Tests for daily prompt template."""

    def test_get_daily_prompt_returns_chat_prompt_template(self):
        """Should return a ChatPromptTemplate instance."""
        from tasker.prompts import get_daily_prompt

        result = get_daily_prompt()
        assert isinstance(result, ChatPromptTemplate)

    def test_daily_prompt_has_required_input_variables(self):
        """Should have current_date and task_notes as input variables."""
        from tasker.prompts import get_daily_prompt

        prompt = get_daily_prompt()
        assert "current_date" in prompt.input_variables
        assert "task_notes" in prompt.input_variables

    def test_daily_prompt_can_be_formatted(self):
        """Should format correctly with provided variables."""
        from tasker.prompts import get_daily_prompt

        prompt = get_daily_prompt()
        messages = prompt.format_messages(
            current_date="Monday, December 30, 2024",
            task_notes="Work\n    Task 1\n    Task 2"
        )

        assert len(messages) == 2
        assert "Monday, December 30, 2024" in messages[0].content
        assert "Task 1" in messages[1].content


class TestWeeklyPrompt:
    """Tests for weekly prompt template."""

    def test_get_weekly_prompt_returns_chat_prompt_template(self):
        """Should return a ChatPromptTemplate instance."""
        from tasker.prompts import get_weekly_prompt

        result = get_weekly_prompt()
        assert isinstance(result, ChatPromptTemplate)

    def test_weekly_prompt_has_required_input_variables(self):
        """Should have week_start, week_end, and task_notes as input variables."""
        from tasker.prompts import get_weekly_prompt

        prompt = get_weekly_prompt()
        assert "week_start" in prompt.input_variables
        assert "week_end" in prompt.input_variables
        assert "task_notes" in prompt.input_variables

    def test_weekly_prompt_can_be_formatted(self):
        """Should format correctly with provided variables."""
        from tasker.prompts import get_weekly_prompt

        prompt = get_weekly_prompt()
        messages = prompt.format_messages(
            week_start="Monday, December 23, 2024",
            week_end="Sunday, December 29, 2024",
            task_notes="## Monday\n\nTask analysis..."
        )

        assert len(messages) == 2
        assert "December 23, 2024" in messages[0].content
        assert "December 29, 2024" in messages[0].content
        assert "Task analysis" in messages[1].content


class TestPromptConstants:
    """Tests for prompt string constants."""

    def test_daily_system_prompt_exists_and_not_empty(self):
        """DAILY_SYSTEM_PROMPT should exist and contain content."""
        from tasker.prompts import DAILY_SYSTEM_PROMPT

        assert DAILY_SYSTEM_PROMPT is not None
        assert len(DAILY_SYSTEM_PROMPT) > 100
        assert "GTD" in DAILY_SYSTEM_PROMPT

    def test_daily_human_prompt_exists_and_not_empty(self):
        """DAILY_HUMAN_PROMPT should exist and contain task_notes placeholder."""
        from tasker.prompts import DAILY_HUMAN_PROMPT

        assert DAILY_HUMAN_PROMPT is not None
        assert "{task_notes}" in DAILY_HUMAN_PROMPT

    def test_weekly_system_prompt_exists_and_not_empty(self):
        """WEEKLY_SYSTEM_PROMPT should exist and contain content."""
        from tasker.prompts import WEEKLY_SYSTEM_PROMPT

        assert WEEKLY_SYSTEM_PROMPT is not None
        assert len(WEEKLY_SYSTEM_PROMPT) > 100
        assert "week" in WEEKLY_SYSTEM_PROMPT.lower()

    def test_weekly_human_prompt_exists_and_not_empty(self):
        """WEEKLY_HUMAN_PROMPT should exist and contain task_notes placeholder."""
        from tasker.prompts import WEEKLY_HUMAN_PROMPT

        assert WEEKLY_HUMAN_PROMPT is not None
        assert "{task_notes}" in WEEKLY_HUMAN_PROMPT

    def test_image_extraction_prompt_exists_and_not_empty(self):
        """IMAGE_EXTRACTION_PROMPT should exist and contain extraction instructions."""
        from tasker.prompts import IMAGE_EXTRACTION_PROMPT

        assert IMAGE_EXTRACTION_PROMPT is not None
        assert len(IMAGE_EXTRACTION_PROMPT) > 50
        assert "extract" in IMAGE_EXTRACTION_PROMPT.lower() or "text" in IMAGE_EXTRACTION_PROMPT.lower()


class TestPromptContent:
    """Tests for prompt content quality."""

    def test_daily_prompt_includes_priority_guidance(self):
        """Daily prompt should include task prioritization guidance."""
        from tasker.prompts import DAILY_SYSTEM_PROMPT

        # Check for priority-related content
        content_lower = DAILY_SYSTEM_PROMPT.lower()
        assert "priority" in content_lower or "urgent" in content_lower

    def test_daily_prompt_includes_time_estimates(self):
        """Daily prompt should mention time estimates."""
        from tasker.prompts import DAILY_SYSTEM_PROMPT

        content_lower = DAILY_SYSTEM_PROMPT.lower()
        assert "time" in content_lower or "minute" in content_lower or "hour" in content_lower

    def test_daily_prompt_includes_energy_levels(self):
        """Daily prompt should mention energy levels."""
        from tasker.prompts import DAILY_SYSTEM_PROMPT

        content_lower = DAILY_SYSTEM_PROMPT.lower()
        assert "energy" in content_lower

    def test_weekly_prompt_includes_pattern_analysis(self):
        """Weekly prompt should include pattern analysis guidance."""
        from tasker.prompts import WEEKLY_SYSTEM_PROMPT

        content_lower = WEEKLY_SYSTEM_PROMPT.lower()
        assert "pattern" in content_lower or "behavior" in content_lower

    def test_image_extraction_prompt_preserves_structure(self):
        """Image extraction prompt should mention preserving structure."""
        from tasker.prompts import IMAGE_EXTRACTION_PROMPT

        content_lower = IMAGE_EXTRACTION_PROMPT.lower()
        assert "structure" in content_lower or "format" in content_lower
