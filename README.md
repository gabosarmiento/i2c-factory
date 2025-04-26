# i2c Alive Factory CLI

**i2c** is an interactive, AI-driven CLI tool that transforms high-level ideas into complete, runnable code projects. Built with AGNO agents and a live Canvas interface, it provides a modular, immersive experience for generating software projects.

---

## Features

- **AI-Powered Agents**: Declarative agents for idea clarification, file planning, and code generation using Groq LLMs.
- **Alive Canvas Interface**: Clean separation of logic and view, with step notifications, success/error reporting, and customizable themes.
- **Modular Architecture**: Easily extendable modules for CLI session, theming, ASCII art, input handling, error recovery, and LLM providers.
- **Configurability**: Supports multiple Groq model sizes (`highest`, `middle`, `small`, `xs`) out of the box.
- **Extensible CLI Flags**: Planned support for customizable flags (e.g., output directory, model selection).
- **Automated Testing**: Placeholder for Pytest suites to validate agent outputs and workflow steps.
- **CI Integration**: Example GitHub Actions workflow to lint, test, and run smoke tests on each commit.

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/gabosarmiento/i2c-factory.git
   cd i2c-factory
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

---

## Usage

```bash
python main.py [--idea "My project idea"] [--out-dir ./custom_output] [--model middle]
```

After launch, follow on-screen prompts to generate your project.

---

## Project Structure

```
├── agents/               # AGNO Pro agent definitions
├── cli/                  # Canvas controller and view modules
├── config/               # Environment and key loaders
├── llm_providers.py      # Central LLM client registry
├── tests/                # Pytest suites (to be implemented)
├── .github/
│   └── workflows/
│       └── ci.yml        # CI pipeline (example)
├── main.py               # Entry point
├── workflow.py           # Pure application logic orchestration
└── README.md
```

---

## Testing

_TODO_: Add unit tests in `tests/` to validate:
- Agent outputs conform to JSON schemas.
- Workflow steps complete without errors.
- Generated files exist and contain expected content.

---

## CI / GitHub Actions

_Add `.github/workflows/ci.yml` with:_
```yaml
name: CI
on: [push, pull_request]
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: python-version: '3.12'
      - run: python -m venv .venv
      - run: . .venv/bin/activate && pip install -r requirements.txt
      - run: . .venv/bin/activate && pytest --maxfail=1 --disable-warnings -q
      - run: . .venv/bin/activate && python main.py --idea "echo Hello" --out-dir /tmp/test_output
```

---

## Next Steps

1. Implement CLI flags and argparse in `main.py`.
2. Build Pytest suites in `tests/` for agents and workflow.
3. Finalize CI pipeline and code coverage reporting.
4. Enhance visuals: progress spinners, color themes, ASCII art variations.

---

> Crafted by AgentArchitectGPT & i2c Alive Factory Team 🚀

