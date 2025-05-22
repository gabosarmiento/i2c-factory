# src/i2c/__main__.py
from i2c.bootstrap import initialize_environment

# 1) one-time env & builtins setup
initialize_environment()

# 2) hand off to your app’s main()
from i2c.app import main

if __name__ == "__main__":
    main()
