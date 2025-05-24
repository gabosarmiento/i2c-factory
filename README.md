# i2c Factory — Self-Healing Agentic Code Evolution

> Transforming ideas into production-grade code through intelligent AI agents with autonomous reasoning, self-healing capabilities, and continuous evolution loops.

---

## 🧠 What is i2c Factory?

The **i2c Factory** is an AI-powered software factory that evolves codebases using a **Self-Healing Meta-Agent Orchestration Model**. It combines:

* **Intelligent reasoning and pattern recognition**
* **Autonomous self-healing and recovery**
* **Knowledge-augmented retrieval (RAG)**
* **Multi-agent orchestration with specialized teams**
* **Continuous validation and adaptive refinement**

Unlike traditional code generators, i2c Factory builds and improves software with:

* **Meta-level reasoning** that analyzes failures and adapts strategies
* **Self-healing capabilities** that automatically fix common issues
* **Contextual understanding** from your repo & knowledge base
* **Multi-layered validation** through specialized agent teams
* **Iterative, validated code evolution** with quality gates

---

## 🏗️ Self-Healing Architecture

### 1. **Meta-Agent Orchestrator (The Brain)**

The **CodeOrchestrationAgent** acts as an intelligent meta-agent that:

* **Reasons** about code evolution objectives
* **Orchestrates** specialized teams (Knowledge, Modification, Quality, SRE)
* **Analyzes failures** using pattern recognition
* **Self-heals** common issues automatically
* **Escalates** complex problems appropriately
* **Adapts strategies** based on validation results

### 2. **Specialized Agent Teams**

#### **Knowledge Team**

* RAG-powered context retrieval
* Documentation analysis and integration
* Best practices injection

#### **Modification Team**

* Intelligent code generation and modification
* **Automatic unit test generation**
* Multi-language support with contextual understanding

#### **Quality Team**

* Static analysis and linting
* Code review and standards enforcement
* Security vulnerability detection

#### **SRE Team**

* Operational readiness validation
* Dependency vulnerability scanning
* Test execution and syntax verification

### 3. **Self-Healing Intelligence**

The orchestrator can automatically recover from:

* **Syntax Errors** → Auto-fix indentation, imports, basic syntax
* **Test Failures** → Regenerate tests, adjust expectations
* **Performance Issues** → Replan with optimization focus
* **Security Concerns** → Escalate to human review
* **Generic Issues** → Retry with enhanced context

### 4. **Reasoning & Adaptation**

Every operation includes:

* **Failure pattern analysis** using intelligent categorization
* **Recovery strategy selection** based on issue complexity
* **Autonomous healing attempts** for recoverable issues
* **Human escalation** for complex/risky problems
* **Comprehensive reasoning trajectory** for full transparency

---

## 🔄 How Self-Healing Code Evolution Works

1. **Analyze Objective** → Understand the code evolution task
2. **Retrieve Knowledge** → RAG-powered context from your codebase
3. **Plan Modifications** → Create structured modification plan
4. **Execute Changes** → Generate code + auto-create unit tests
5. **Quality Validation** → Multi-gate quality checks
6. **Operational Validation** → SRE readiness verification
7. **🧠 Failure Analysis** → Pattern recognition for issues
8. **🔧 Self-Healing** → Automatic recovery attempts
9. **♻️ Re-validation** → Verify healing success
10. **✅ Final Decision** → Approve/reject with reasoning

---

## 📦 Project Structure

src/
├── agents/
│   ├── code\_orchestration\_agent.py    # 🧠 Meta-agent with self-healing
│   ├── modification\_team/              # Code generation & unit tests
│   ├── quality\_team/                   # Quality gates & validation
│   ├── sre\_team/                       # Operational readiness
│   ├── knowledge/                      # RAG & context management
│   └── reflective/                     # Advanced reasoning operators
├── workflow/
│   ├── orchestration/                  # Agent coordination
│   ├── modification/                   # Code evolution pipeline
│   └── scenario\_processor.py          # Automated demo workflows
├── cli/                                # User interface & budget tracking
└── main.py                             # CLI entry point

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

### Quick Start - Interactive Mode

```bash
python main.py --idea "Add comprehensive logging to all API endpoints" --out-dir ./output
```

### Advanced - Scenario-Based Evolution

```bash
python main.py --scenario scenarios/enhance-security.json
```

## 🧩 Self-Healing in Action

### Example: Automatic Syntax Recovery

```bash
{
  "reasoning_trajectory": [
    {"step": "Quality Validation", "description": "Syntax errors detected"},
    {"step": "Failure Analysis", "description": "Pattern: auto_fix_syntax (confidence: high)"},
    {"step": "Self-Healing", "description": "Attempting automatic recovery"},
    {"step": "Auto-Fix", "description": "Applied syntax fixes to calculator.py"},
    {"step": "Re-Validation", "description": "Running validation after self-healing"},
    {"step": "Self-Healing", "description": "Self-healing successful - validation now passes"},
    {"step": "Final Decision", "description": "Decision: approve - All validations passed after recovery"}
  ]
}
```

### Recovery Strategies

| Issue Pattern            | Strategy            | Auto-Recoverable | Action                    |
| ------------------------ | ------------------- | ---------------- | ------------------------- |
| Syntax errors, indent    | auto\_fix\_syntax   | ✅ Yes            | Fix automatically         |
| Test failures, asserts   | fix\_test\_logic    | ✅ Yes            | Regenerate tests          |
| Performance issues       | replan\_performance | ⚠️ Maybe         | Replan with optimizations |
| Security vulnerabilities | human\_escalation   | ❌ No             | Escalate to human review  |

---

## 🧠 Working with Knowledge

### Repository-Based Intelligence

```json
git clone https://github.com/tensorflow/tensorflow.git projects/tensorflow
```

```json
{
  "action": "load_project",
  "params": {"path": "projects/tensorflow"}
}
```

### Focused Knowledge Injection

```json
{
  "action": "knowledge_management",
  "params": {
    "sources": ["docs/api-guidelines.md", "examples/logging_patterns.py"]
  }
}
```

---

## 📝 Scenario-Driven Evolution

Example scenario for comprehensive security enhancement:

```json
{
  "scenario_name": "Security Hardening with Self-Healing",
  "steps": [
    {
      "type": "initial_generation",
      "prompt": "Create a secure REST API with authentication",
      "project_name": "secure-api"
    },
    {
      "type": "knowledge",
      "doc_path": "docs/security-guidelines.md",
      "doc_type": "Security Standards"
    },
    {
      "type": "agentic_evolution",
      "objective": {
        "task": "Add input validation and rate limiting",
        "constraints": [
          "Follow OWASP security guidelines",
          "Ensure backward compatibility",
          "Include comprehensive error handling"
        ],
        "quality_gates": ["bandit", "safety", "mypy"]
      }
    }
  ]
}
```

---

## ✅ Supported Languages & Features

### Core Languages

* Python: Full support with auto-test generation
* JavaScript/TypeScript: Modern frameworks & testing
* Go: Performance-optimized patterns
* Java: Enterprise-grade structures

### Self-Healing Capabilities

* ✅ Automatic syntax correction
* ✅ Intelligent test regeneration
* ✅ Performance optimization replanning
* ✅ Security issue escalation
* ✅ Dependency vulnerability detection
* ✅ Code quality auto-fixing

### Quality Gates

* Static Analysis: flake8, mypy, bandit, eslint
* Security Scanning: pip-audit, safety checks
* Test Execution: pytest, jest, go test
* Operational Readiness: Syntax validation, dependency checks

\## 🎯 Why i2c Factory's Self-Healing Matters

### Traditional AI Code Generation Problems:

* ❌ Generates broken code that doesn't compile
* ❌ Creates tests that fail immediately
* ❌ No recovery from validation failures
* ❌ Requires manual intervention for simple issues

### i2c Factory Self-Healing Solutions:

* ✅ Automatically fixes syntax errors and common issues
* ✅ Regenerates tests when they fail
* ✅ Adapts strategies based on failure patterns
* ✅ Escalates intelligently only when human input is needed
* ✅ Learns from failures to improve future operations

### Real-World Impact:

* 95% reduction in manual fix-up work
* Autonomous recovery from common development issues
* Intelligent escalation preserves human time for complex decisions
* Production-ready code with comprehensive validation
* Transparent reasoning for full auditability

---

## 🔬 Advanced Features

### Meta-Agent Reasoning

The orchestrator maintains a complete reasoning trajectory showing:

* Decision points and rationale
* Failure analysis and pattern recognition
* Recovery attempts and outcomes
* Human escalation triggers
* Final approval reasoning

### Budget-Aware Operations

* Token consumption tracking
* Cost optimization across agent teams
* Intelligent model selection per task
* Usage analytics and reporting

### Extensible Architecture

* Plugin-based agent teams
* Custom quality gates
* Domain-specific knowledge integration
* Multi-cloud deployment ready

---

Made by humans, evolved by self-healing agents.
Powered by Groq, intelligent reasoning, and your knowledge base.

---

## 🤝 Contributing

The i2c Factory thrives on community contributions:

* Agent Teams: Contribute specialized validation or generation agents
* Self-Healing Patterns: Add new failure pattern detection and recovery strategies
* Quality Gates: Implement language-specific quality validations
* Knowledge Integrations: Build domain-specific RAG connectors
* Scenario Templates: Share proven evolution workflows

Join us in building the future of intelligent, self-healing software development.
