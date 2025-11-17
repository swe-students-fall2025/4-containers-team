"""Unit tests for machine learning client."""

import sys
import os
import main
import language_learner
import database



class TestMain:
    """Tests for main module."""

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        assert callable(main)

    def test_main_runs_without_error(self):
        """Test that main function runs without error."""
        main()
        assert True
