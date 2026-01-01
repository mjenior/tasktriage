"""
Tests for tasktriage.analysis module.
"""

from unittest.mock import MagicMock, patch, call

import pytest


class TestAnalyzeTasks:
    """Tests for analyze_tasks function."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock ChatAnthropic instance."""
        with patch("tasktriage.analysis.ChatAnthropic") as mock_class:
            mock_instance = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """# Daily Execution Order

1. **Review budget** [Energy: High] [Est: 45min]
   - Open spreadsheet
   - Identify issues

## Critical Assessment
Good task clarity.
"""
            mock_instance.invoke.return_value = mock_response
            mock_class.return_value = mock_instance
            yield mock_class, mock_instance, mock_response

    def test_returns_analysis_content(self, mock_llm):
        """Should return the LLM response content."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_prompt:
            # Set up prompt mock to work with chain
            mock_prompt_template = MagicMock()
            mock_prompt_template.__or__ = lambda self, other: mock_instance
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks

            result = analyze_tasks(
                "daily",
                "Work\n    Task 1\n    Task 2",
                current_date="Monday, December 30, 2024"
            )

            assert "Daily Execution Order" in result
            assert "Review budget" in result

    def test_uses_daily_prompt_for_daily_analysis(self, mock_llm):
        """Should use daily prompt template for daily analysis."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_daily, \
             patch("tasktriage.analysis.get_weekly_prompt") as mock_weekly:
            mock_prompt = MagicMock()
            mock_prompt.__or__ = lambda self, other: mock_instance
            mock_daily.return_value = mock_prompt

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "daily",
                "Task notes",
                current_date="Monday, December 30, 2024"
            )

            mock_daily.assert_called_once()
            mock_weekly.assert_not_called()

    def test_uses_weekly_prompt_for_weekly_analysis(self, mock_llm):
        """Should use weekly prompt template for weekly analysis."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_daily, \
             patch("tasktriage.analysis.get_weekly_prompt") as mock_weekly:
            mock_prompt = MagicMock()
            mock_prompt.__or__ = lambda self, other: mock_instance
            mock_weekly.return_value = mock_prompt

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "weekly",
                "Weekly notes",
                week_start="Monday, December 23, 2024",
                week_end="Sunday, December 29, 2024"
            )

            mock_weekly.assert_called_once()
            mock_daily.assert_not_called()

    def test_uses_provided_api_key(self, mock_llm):
        """Should use the provided API key."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key") as mock_fetch, \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_prompt:
            mock_fetch.return_value = "custom-api-key"
            mock_prompt_template = MagicMock()
            mock_prompt_template.__or__ = lambda self, other: mock_instance
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "daily",
                "Task notes",
                api_key="custom-api-key",
                current_date="Monday, December 30, 2024"
            )

            mock_fetch.assert_called_with("custom-api-key")

    def test_uses_default_model_when_not_configured(self, mock_llm):
        """Should use default model when not specified in config."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_prompt:
            mock_prompt_template = MagicMock()
            mock_prompt_template.__or__ = lambda self, other: mock_instance
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks, DEFAULT_MODEL

            analyze_tasks(
                "daily",
                "Task notes",
                current_date="Monday, December 30, 2024"
            )

            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["model"] == DEFAULT_MODEL

    def test_uses_model_from_config(self, mock_llm):
        """Should use model specified in config."""
        mock_class, mock_instance, mock_response = mock_llm
        config = {"model": "claude-sonnet-4-20250514", "temperature": 0.5}

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value=config.copy()), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_prompt:
            mock_prompt_template = MagicMock()
            mock_prompt_template.__or__ = lambda self, other: mock_instance
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "daily",
                "Task notes",
                current_date="Monday, December 30, 2024"
            )

            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"

    def test_passes_config_params_to_llm(self, mock_llm):
        """Should pass config parameters to ChatAnthropic."""
        mock_class, mock_instance, mock_response = mock_llm
        config = {"model": "claude-haiku-4-5-20241022", "temperature": 0.3, "max_tokens": 2000}

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value=config.copy()), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_prompt:
            mock_prompt_template = MagicMock()
            mock_prompt_template.__or__ = lambda self, other: mock_instance
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "daily",
                "Task notes",
                current_date="Monday, December 30, 2024"
            )

            mock_class.assert_called_once()
            call_kwargs = mock_class.call_args[1]
            assert call_kwargs["temperature"] == 0.3
            assert call_kwargs["max_tokens"] == 2000

    def test_invokes_chain_with_task_notes(self, mock_llm):
        """Should invoke the chain with task_notes and prompt variables."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_daily_prompt") as mock_prompt:
            mock_prompt_template = MagicMock()
            # Track what invoke is called with
            chain_mock = MagicMock()
            chain_mock.invoke.return_value = mock_response
            mock_prompt_template.__or__ = lambda self, other: chain_mock
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "daily",
                "My task notes content",
                current_date="Monday, December 30, 2024"
            )

            chain_mock.invoke.assert_called_once()
            call_args = chain_mock.invoke.call_args[0][0]
            assert call_args["task_notes"] == "My task notes content"
            assert call_args["current_date"] == "Monday, December 30, 2024"

    def test_passes_weekly_prompt_vars(self, mock_llm):
        """Should pass week_start and week_end for weekly analysis."""
        mock_class, mock_instance, mock_response = mock_llm

        with patch("tasktriage.analysis.fetch_api_key", return_value="test-key"), \
             patch("tasktriage.analysis.load_model_config", return_value={}), \
             patch("tasktriage.analysis.get_weekly_prompt") as mock_prompt:
            chain_mock = MagicMock()
            chain_mock.invoke.return_value = mock_response
            mock_prompt_template = MagicMock()
            mock_prompt_template.__or__ = lambda self, other: chain_mock
            mock_prompt.return_value = mock_prompt_template

            from tasktriage.analysis import analyze_tasks

            analyze_tasks(
                "weekly",
                "Weekly notes",
                week_start="Monday, December 23, 2024",
                week_end="Sunday, December 29, 2024"
            )

            chain_mock.invoke.assert_called_once()
            call_args = chain_mock.invoke.call_args[0][0]
            assert call_args["week_start"] == "Monday, December 23, 2024"
            assert call_args["week_end"] == "Sunday, December 29, 2024"


class TestAnalysisIntegration:
    """Integration-style tests for analysis module."""

    def test_default_model_constant_exists(self):
        """DEFAULT_MODEL constant should be defined."""
        from tasktriage.analysis import DEFAULT_MODEL

        assert DEFAULT_MODEL is not None
        assert "claude" in DEFAULT_MODEL.lower()

    def test_imports_required_dependencies(self):
        """Should be able to import required functions."""
        from tasktriage.analysis import analyze_tasks
        from tasktriage.analysis import fetch_api_key, load_model_config
        from tasktriage.analysis import get_daily_prompt, get_weekly_prompt

        assert callable(analyze_tasks)
        assert callable(fetch_api_key)
        assert callable(load_model_config)
        assert callable(get_daily_prompt)
        assert callable(get_weekly_prompt)
