"""
Test package.

Importing `_support` redirects interaction logging away from the real study log.
It is imported here for package-style invocation
(`python -m unittest tests.test_x`) and again by each app-driving test module,
because `unittest discover tests` bypasses this file entirely.
"""

from tests import _support  # noqa: F401
