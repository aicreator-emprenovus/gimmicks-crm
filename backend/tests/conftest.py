"""Shared test configuration - credentials loaded from environment."""
import os

TEST_EMAIL = os.environ.get("TEST_EMAIL", "admin@gimmicks.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "admin123456")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
