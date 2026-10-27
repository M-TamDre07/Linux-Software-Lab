# Integration tests

Test boundaries between the application, its data providers, operating-system adapters, and packaging code. Prefer fixtures and disposable environments.

Production services must not be mutated by ordinary pull-request tests. Any live integration probe must be read-only, narrowly scoped, explicitly configured, and clearly marked as a separate check.
