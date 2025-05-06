# tests/conftest.py

from i2c.bootstrap import initialize_environment

# Run your one‐time env + builtins setup before any tests
initialize_environment()
