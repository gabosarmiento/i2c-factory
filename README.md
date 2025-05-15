# i2c Factory — Agentic-Orchestrated Code Evolution

> Transforming ideas into production-grade code through AI agents, knowledge integration, and continuous evolution loops.

---

## 🧠 What is i2c Factory?

The **i2c Factory** is an AI-powered software factory that evolves code bases using a **Reflective Multi-Agent Orchestration Model**. It combines:

* **Knowledge-augmented retrieval (RAG)**
* **Agentic orchestration**
* **Code orchestration agents**
* **Validation and self-healing cycles**

Unlike code generators, i2c Factory builds and improves software with:

* Contextual understanding from your repo & knowledge base.
* Structured modification plans.
* Iterative, validated code evolution.

---

## 🏗️ Key Architecture

### 1. **Scenario Processor**

* Reads JSON scenario files to automate project workflows.
* Ensures knowledge, objectives, and context are loaded step by step.

### 2. **Knowledge Integration Layer**

* Uses **RAG retrieval** to fetch relevant knowledge (docs, patterns, examples).
* Injects this into session state for downstream agents.

### 3. **Agentic Orchestrator**

* Builds structured tasks with embedded knowledge context.
* Delegates work to specialized teams:

  * Code Modification
  * Knowledge
  * Quality
  * SRE (Ops)

### 4. **Code Orchestration Agent**

* Leads the evolution process.
* Uses knowledge-rich prompts to plan, modify, validate code.
* Coordinates sub-teams for iterative improvements.

### 5. **Modification Team**

* Receives `ModificationRequest` with RAG context.
* Analyzes code, plans diffs, applies modifications.
* Ensures repository style and architectural coherence.

### 6. **Validation & Quality Loop**

* Automated tests, quality gates, operational checks.
* Supports reflection & refinement loops for adaptive improvements.

---

## 🔄 How Knowledge Drives Code Evolution

1. **Retrieve Knowledge (RAG)**: Pulls relevant documentation, code examples, best practices.
2. **Integrate & Contextualize**: Builds session state with project path, objectives, and knowledge.
3. **Orchestrate with Knowledge**: Agentic Orchestrator creates structured tasks for agents using this knowledge.
4. **Agent-Driven Code Modification**: Code agents modify codebases guided by retrieved knowledge.
5. **Validate & Iterate**: Runs tests, quality checks, and reflects on failures to adapt.
6. **Final Decision**: Agents decide to approve or refine based on reasoning trajectories.

---

## 📦 Project Structure (Refined)

```
src/
├── agents/               # Specialized agents (code, quality, knowledge, SRE)
├── workflow/             # Orchestration flows, knowledge integration, scenario processing
├── cli/                  # User interface (Canvas controller & views)
├── config/               # Environment settings, keys, model configs
├── llm_providers.py      # LLM provider registry (Groq, OpenAI, etc.)
├── main.py               # CLI entry point
└── README.md             # This document
```

---

## 🚀 Getting Started

### Installation

```bash
git clone https://github.com/gabosarmiento/i2c-factory.git
cd i2c-factory
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_groq_api_key_here" > .env
```

### Usage

```bash
python main.py --idea "Add logging to all public methods" --out-dir ./output
```

For advanced workflows, see below how to provide a **scenario JSON file** to automate multi-step evolutions.

---
## 🧩 Working with Knowledge

### Option 1: Simple Knowledge Injection (Focused Tasks)
Provide focused documents and code examples to guide the factory for specific tasks.

Example usage:
```json
{
  "action": "knowledge_management",
  "params": {
    "sources": ["docs/logging-guidelines.md", "examples/logging_example.py"]
  }
}
```

### Option 2: Repository-Based Knowledge Import (Deep Contextual Understanding)
Clone full repositories as knowledge bases to enable intelligent, context-rich code evolution.

```bash
git clone https://github.com/tensorflow/tensorflow.git projects/tensorflow
```

Scenario reference:
```json
{
  "action": "load_project",
  "params": {
    "path": "projects/tensorflow"
  }
}
```

This allows i2c Factory to act as a PhD-level assistant for your project.

---

## 📝 How Scenarios Work

A scenario JSON defines the evolution workflow with step-by-step instructions.

Example Scenario:
```json
{
  "scenario_name": "Enhance Logging",
  "steps": [
    { "action": "load_project", "params": { "path": "projects/my-project" } },
    { "action": "knowledge_management", "params": { "sources": ["docs/logging-guidelines.md"] } },
    { "action": "code_modification", "params": { "file": "app/handler.py", "goal": "Add logging decorators" } },
    { "action": "validate_changes", "params": { "tests": "all" } }
  ]
}
```

| Action                | What it Does                                                                 |
|-----------------------|------------------------------------------------------------------------------|
| **load_project**       | Loads the specified project into the factory's context.                       |
| **knowledge_management** | Retrieves and integrates knowledge to guide modifications.                  |
| **code_modification**  | Executes knowledge-driven code modifications.                                |
| **validate_changes**   | Runs tests and quality validations post-modification.                        |

---

## 🚀 Usage Guide

### Folder Structure:
```
i2c-factory/
├── projects/              # Your target codebases
├── docs/                  # Knowledge documents
├── examples/              # Code examples
├── scenarios/             # Scenario JSON files
├── src/                   # Factory core code
└── README.md
```

### Run a Scenario:
```bash
poetry run i2c --scenario scenarios/my-scenario.json
```

---

## ✅ Supported Languages
- **Python**: Fully supported with best practices enforcement.
- Extensible to **JavaScript, TypeScript, Go, YAML, Markdown** via knowledge-driven prompts.
- Language-agnostic at architecture level — knowledge defines the style and conventions.

---

## ✅ CI & Testing

* CI pipeline with GitHub Actions for linting, testing, and basic smoke runs.
* Planned Pytest suites for:

  * Agent output validation.
  * Knowledge integration tests.
  * End-to-end scenario execution.

---

## 🎯 Why i2c Factory Matters

* **Bridges raw AI generation with structured software engineering**.
* Ensures code evolves with context, best practices, and human-grade quality.
* Built for teams who want **repeatable, reliable, and scalable AI-assisted development**.
* Scales from simple helper scripts to enterprise-grade code orchestration.
* Bridges LLM generation with structured software engineering rigor.
* Evolves codebases using repository-specific knowledge, patterns, and reasoning agents.

---

> Made by humans, evolved by agents.
> Powered by Groq, AGNO, and your knowledge base.

---