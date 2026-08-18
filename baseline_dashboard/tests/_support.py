"""
Shared test setup, imported for its side effect.

Kept as a module so package-style invocation picks it up via `tests/__init__.py`.
App-driving test modules call `use_temporary_log_dir()` from `study.events`
directly instead, because `unittest discover tests` imports test modules as
top-level names — `tests/` is not on `sys.path` under package invocation and
`tests/__init__.py` never runs under discovery, so neither import style works
for both.
"""

from study.events import use_temporary_log_dir

TEST_LOG_DIR = use_temporary_log_dir()
