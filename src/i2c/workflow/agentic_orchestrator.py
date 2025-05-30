from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import asyncio
import datetime
import json
import re

from agno.team import Team
from agno.agent import Message
from i2c.workflow.orchestration_team import build_orchestration_team
try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
        def success(self, *args, **kwargs): pass
    canvas = DummyCanvas()
from i2c.workflow.modification.file_operations import write_files_to_disk
from i2c.agents.quality_team.utils.language_detector import LanguageDetector

"""
Agentic orchestrator for evolving software projects using AGNO agents.

Handles:
- Orchestration of AI agents for software synthesis
- Architectural context enrichment
- Smart file writing with language-aware stubs
- Dependency initialization and folder normalization
"""
# --------------------------------------------------------------------------- #
#  Smart directory resolver                                                   #
# --------------------------------------------------------------------------- #
from collections import defaultdict
LANG_SIGNS = {
    "python":  [".py", "fastapi", "pydantic"],
    "javascript": [".js", ".jsx", ".ts", ".tsx", "react", "vite"],
    "go":      [".go", "module", "fiber"],
    "java":    [".java", ".kt", "spring", "pom.xml"],
}

def _detect_lang_roots(project_path: Path) -> dict[str, Path]:
    """
    Walk the tree once and record where each language first appears.
    Returns {lang: directory_path}
    """
    roots: dict[str, Path] = {}
    for p in project_path.rglob("*"):
        if p.is_dir():
            continue
        lower_name = p.name.lower()
        for lang, signs in LANG_SIGNS.items():
            if any(lower_name.endswith(s) or s in lower_name for s in signs):
                roots.setdefault(lang, p.parent)
    return roots


TEMPLATES_BY_LANG: dict[str, str] = {
    # ------------------------------------------------------------------
    # 🐍 Python – FastAPI entry point
    # ------------------------------------------------------------------
    "python": (
        '"""Minimal FastAPI scaffold generated automatically."""\n'
        'from fastapi import FastAPI\n\n'
        'app = FastAPI()\n\n'
        '@app.get("/")\n'
        'async def root():\n'
        '    return {"status": "ok"}\n\n'
        'if __name__ == "__main__":\n'
        '    import uvicorn\n'
        '    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)\n'
    ),

    # ------------------------------------------------------------------
    # ⚛️ React JSX – App component
    # ------------------------------------------------------------------
    "jsx": (
        '/* Minimal React scaffold generated automatically */\n'
        'import React from "react";\n\n'
        'function App() {\n'
        '  return (\n'
        '    <main style={{ padding: "2rem" }}>\n'
        '      <h1>👋 Hello from the auto-generated scaffold!</h1>\n'
        '    </main>\n'
        '  );\n'
        '}\n\n'
        'export default App;\n'
    ),

    # ------------------------------------------------------------------
    # 🟦 TypeScript – simple CLI / lib entry
    # ------------------------------------------------------------------
    "typescript": (
        '// auto-generated TypeScript scaffold\n'
        'export function main(): void {\n'
        '  console.log("Hello, TypeScript world!");\n'
        '}\n\n'
        'if (require.main === module) {\n'
        '  main();\n'
        '}\n'
    ),

    # ------------------------------------------------------------------
    # 🟨 JavaScript – Express server (common default)
    # ------------------------------------------------------------------
    "javascript": (
        '// auto-generated Express scaffold\n'
        'import express from "express";\n\n'
        'const app = express();\n'
        'const PORT = process.env.PORT || 3000;\n\n'
        'app.get("/", (_req, res) => {\n'
        '  res.json({ status: "ok" });\n'
        '});\n\n'
        'app.listen(PORT, () => {\n'
        '  console.log(`Server running on http://localhost:${PORT}`);\n'
        '});\n'
    ),

    # ------------------------------------------------------------------
    # 🐹 Go – tiny HTTP handler
    # ------------------------------------------------------------------
    "go": (
        '// Auto-generated Go scaffold\n'
        'package main\n\n'
        'import (\n'
        '    "fmt"\n'
        '    "net/http"\n'
        ')\n\n'
        'func main() {\n'
        '    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n'
        '        fmt.Fprintln(w, `{"status":"ok"}`)\n'
        '    })\n'
        '    fmt.Println("Server on :8080")\n'
        '    if err := http.ListenAndServe(":8080", nil); err != nil {\n'
        '        panic(err)\n'
        '    }\n'
        '}\n'
    ),
}

SPECIAL_CASE_STUBS: dict[str, str] = {
    # Mandatory entry points
    "backend/main.py": TEMPLATES_BY_LANG["python"],
    "frontend/src/App.jsx": TEMPLATES_BY_LANG["jsx"],

    # Optional placeholders
    "backend/api/__init__.py": "",
    "backend/api/snippets.py": (
        "from fastapi import APIRouter\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/')\n"
        "async def list_snippets():\n"
        "    return []\n"
    ),
    "frontend/README.md": "# Front-end code lives here\n",
}

# One clean definition for the component placeholder
COMPONENT_STUB = (
    "/* Auto-generated placeholder component */\n"
    "import React from 'react';\n\n"
    "export default function Placeholder() {\n"
    "  return <div style={{ padding: '1rem' }}>Placeholder component</div>;\n"
    "}\n"
)
SPECIAL_CASE_STUBS["frontend/src/components/Placeholder.jsx"] = COMPONENT_STUB

# helper: crude keyword gate
FRONTEND_HINTS = {"react", "vue", "svelte", "angular", "vite", "tailwind",
                  "next.js", "nuxt", "frontend", "ui", "browser"}

def _guess_needs_frontend(text: str) -> bool:
    return any(k in text for k in FRONTEND_HINTS)

def _stub_for(rel_path: str, lang: str) -> str:
    """
    Return the exact code stub we should write for `rel_path`.

    Priority:
      1. Explicit SPECIAL_CASE_STUBS
      2. Language template (by ext / detector)
      3. Generic “TODO” comment
    """
    if rel_path in SPECIAL_CASE_STUBS:
        return SPECIAL_CASE_STUBS[rel_path]

    if lang in TEMPLATES_BY_LANG:
        return TEMPLATES_BY_LANG[lang]

    comment = "//" if Path(rel_path).suffix in {".js", ".jsx", ".ts"} else "#"
    return f"{comment} TODO: implement {rel_path}\n"

# helper already in agentic_orchestrator.py
def _apply_modifications_if_any(result_json: dict, project_path: Path) -> None:
    mods = result_json.get("modifications", {})
    if not isinstance(mods, dict) or not mods:
        return

    prepared: dict[str, str] = {}
    for rel_path, body in mods.items():
        if not isinstance(body, str):
            body = str(body)

        # full code provided?
        if "\n" in body.strip():
            if not body.endswith("\n"):
                body += "\n"
            prepared[rel_path] = body
            continue

        # otherwise create stub
        lang = (
            LanguageDetector.detect_language(Path(rel_path).suffix)
            or LanguageDetector.detect_language(body)
            or ""
        )

        prepared[rel_path] = _stub_for(rel_path, lang.lower())

    write_files_to_disk(prepared, project_path)

# --- consolidate helpers ----------------------------------------
def _ensure_mandatory_files(project_path: Path, arch_ctx: dict):
    required = {
        "fullstack_web_app": [
            ("backend/main.py", "python"),
            ("frontend/src/App.jsx", "jsx"),
        ],
        "api_service": [("backend/main.py", "python")],
        "cli_tool": [("main.py", "python")],
    }.get(arch_ctx.get("architecture_pattern"), [])

    for rel_path, lang in required:
        target = project_path / rel_path
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(TEMPLATES_BY_LANG.get(lang, f"# TODO: {rel_path}\n"))


def is_json_like_string(s: str) -> bool:
    s = s.strip()
    return s.startswith("{") and s.endswith("}")

def ensure_dependency_file(project_path: Path, arch_ctx: dict):
    preferred = arch_ctx.get("preferred_stacks", {})
    lang_roots = _detect_lang_roots(project_path)

    # ---------- Python ------------------------------------------------------
    if "python" in preferred:
        root = lang_roots.get("python", project_path / "backend")
        root.mkdir(parents=True, exist_ok=True)
        req = root / "requirements.txt"
        if not req.exists():
            req.write_text(
                "fastapi\nuvicorn[standard]\npydantic\nhttpx\npytest\n",
                encoding="utf-8",
            )

    # ---------- JavaScript / TypeScript ------------------------------------
    if "javascript" in preferred:
        root = lang_roots.get("javascript", project_path / "frontend")
        root.mkdir(parents=True, exist_ok=True)
        pkg = root / "package.json"
        if not pkg.exists():
            pkg.write_text(
                """{
  "name": "app",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^4.0.0",
    "tailwindcss": "^3.3.0"
  }
}""",
                encoding="utf-8",
            )

    # ---------- Go ----------------------------------------------------------
    if "go" in preferred:
        root = lang_roots.get("go", project_path)
        go_mod = root / "go.mod"
        if not go_mod.exists():
            go_mod.write_text(
                "module app\n\ngo 1.21\nrequire github.com/gofiber/fiber/v2 v2.50.0\n",
                encoding="utf-8",
            )

    # ---------- Java / Maven -----------------------------------------------
    if "java" in preferred:
        root = lang_roots.get("java", project_path / "java")
        root.mkdir(parents=True, exist_ok=True)
        pom = root / "pom.xml"
        if not pom.exists():
            pom.write_text(
                """<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>app</artifactId>
  <version>1.0-SNAPSHOT</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter</artifactId>
      <version>3.2.0</version>
    </dependency>
  </dependencies>
</project>""",
                encoding="utf-8",
            )


async def execute_agentic_evolution(
    objective: Dict[str, Any],
    project_path: Path,
    session_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Orchestrate an agentic evolution run with architectural intelligence enforcement.
    """

    if session_state is None:
        session_state = {
            "project_path": str(project_path),
            "objective": objective,
            "reasoning_trajectory": [],
            "start_time": datetime.datetime.now().isoformat(),
            "existing_files": [
                f for f in os.listdir(project_path) if os.path.isfile(project_path / f)
            ] if project_path.exists() else []
        }
    
    # Add reflection memory if not already present
    if "reflection_memory" not in session_state:
        session_state["reflection_memory"] = []

    # Enhance objective with reflection context if we have previous steps

    if session_state["reflection_memory"]:
        # Extract common patterns and issues
        failures = [step for step in session_state["reflection_memory"] if not step.get('success', False)]
        incomplete_tasks = []
        recurring_patterns = {}
        
        # Analyze failures and incomplete work
        for step in session_state["reflection_memory"]:
            task = step.get('task', '')
            success = step.get('success', False)
            summary = step.get('summary', '')
            
            # Identify incomplete tasks
            if not success:
                incomplete_tasks.append({
                    "task": task,
                    "summary": summary,
                    "files_modified": step.get('files_modified', [])
                })
            
            # Track common terms/patterns
            for term in ["test", "feature", "component", "UI", "backend", "API", "incomplete"]:
                if term.lower() in task.lower() or term.lower() in summary.lower():
                    recurring_patterns[term] = recurring_patterns.get(term, 0) + 1
        
        # Create enhanced reflection with structured insights
        reflection_insights = {
            "incomplete_tasks": incomplete_tasks,
            "recurring_issues": [k for k, v in recurring_patterns.items() if v > 1],
            "success_rate": f"{sum(1 for s in session_state['reflection_memory'] if s.get('success', False))}/{len(session_state['reflection_memory'])}"
        }
        
        # Create concise summaries as before
        step_summaries = []
        for i, step in enumerate(session_state["reflection_memory"]):
            success_str = "✅" if step.get('success', False) else "❌"
            summary = (
                f"Step {i+1}: {success_str} {step.get('task', 'Unknown')[:50]}... "
                f"Files: {', '.join(step.get('files_modified', [])[:3])} "
                f"Outcome: {step.get('summary', 'No details')[:100]}..."
            )
            step_summaries.append(summary)
        
        # Create enhanced reflection prompt with structured insights
        reflection_context = "\n== REFLECTION FROM PREVIOUS STEPS ==\n" + "\n".join(step_summaries)
        
        if incomplete_tasks:
            reflection_context += "\n\n== INCOMPLETE TASKS REQUIRING ATTENTION ==\n"
            for task in incomplete_tasks:
                reflection_context += f"• {task['task'][:80]}...\n  Reason: {task['summary'][:100]}...\n"
        
        if reflection_insights["recurring_issues"]:
            reflection_context += f"\n\n== RECURRING THEMES ==\n• {', '.join(reflection_insights['recurring_issues'])}\n"
        
        reflection_context += f"\n== PROGRESS SUMMARY ==\nSuccess rate: {reflection_insights['success_rate']}\n"
        
        # Log for debugging
        print(f"Enhanced reflection context: {reflection_context}")
        
        # Inject into objective
        if isinstance(objective.get("task"), str):
            reflection_prompt = "\n\nIMPORTANT - REVIEW PREVIOUS STEPS BEFORE PROCEEDING:\n" + reflection_context
            objective["task"] = objective["task"] + reflection_prompt
        
        # Add structured insights for more advanced agents
        objective["reflection_insights"] = reflection_insights
        objective["reflection_context"] = reflection_context
        
        # Store enhanced objective
        session_state["enhanced_objective"] = objective
    

    enhanced_objective = await _enhance_objective_with_architectural_intelligence(
        objective, project_path, session_state
    )
    # === Multi-language lean stack preferences ===
    preferred_stacks = {
        "javascript": {
            "frontend_template": "vite_react_tailwind",
            "framework": "React",
            "style": "Tailwind CSS",
            "builder": "Vite",
            "avoid": ["Next.js monorepo", "Electron", "Theia"]
        },
        "python": {
            "ui_framework": "streamlit",
            "api_framework": "fastapi",
            "avoid": ["Dash", "Flask boilerplates"]
        },
        "java": {
            "framework": "Spring Boot",
            "build_tool": "Maven",
            "avoid": ["heavy enterprise scaffolds"]
        },
        "go": {
            "framework": "Fiber",
            "style": "minimalist",
            "avoid": ["monolith", "too many codegen layers"]
        }
    }
    
    # Infer desired stacks from the scenario objective
    objective_text = json.dumps(objective).lower()
    needs_front = _guess_needs_frontend(objective_text)
    desired_stacks: set[str] = set()
    if "fastapi" in objective_text or "django" in objective_text:
        desired_stacks.add("python")
    if needs_front:
        desired_stacks.add("javascript")
        
    filtered_stacks = {lang: cfg for lang, cfg in preferred_stacks.items()
                   if lang in desired_stacks}
    
    # choose architecture
    arch_pattern = "fullstack_web" if needs_front else "api_service"
    enhanced_objective["architecture_pattern"] = arch_pattern

    # make it crystal-clear for downstream agents
    if not needs_front:
        constraints = enhanced_objective.get("constraints", [])
        if isinstance(constraints, dict):
            constraints = []
        if isinstance(constraints, list):
            constraints.append("No UI/client-side code; produce a pure backend service.")
        enhanced_objective["constraints"] = constraints

    # Always fall back to Python so at least one stack exists
    if not desired_stacks:
        desired_stacks = {"python"}

    filtered_stacks = {lang: preferred_stacks[lang] for lang in desired_stacks}
    enhanced_objective.setdefault("architectural_context", {})["preferred_stacks"] = filtered_stacks
    session_state.setdefault("architectural_context", {})["preferred_stacks"] = filtered_stacks

    session_state["enhanced_objective"] = enhanced_objective
    session_state["architectural_context"] = enhanced_objective.get("architectural_context", {})

    team_input = {
        "objective": enhanced_objective,
        "session_state": session_state
    }

    team = build_orchestration_team(team_input)
    message = Message(role="user", content=json.dumps(team_input))
    result = await team.arun(message=message)

    # Handle intermediate events if paused
    intermediate_events = {"run_paused", "waiting", "intermediate"}
    while getattr(result, "event", None) in intermediate_events:
        canvas.info(f"Waiting on agentic evolution, current state: {result.event}")
        await asyncio.sleep(1)
        if hasattr(team, "resume_run"):
            result = await team.resume_run(result.run_id)
        else:
            result = await team.get_next_result(result.run_id)

    # Once final, parse the content safely
    content = getattr(result, "content", None)
    arch_ctx = enhanced_objective.get("architectural_context", {})
    session_state["architectural_context"] = arch_ctx

    try:
        if hasattr(content, "dict"):
            result_dict = content.dict()
        elif isinstance(content, dict):
            result_dict = content
        elif isinstance(content, str):
            from i2c.utils.json_extraction import extract_json_with_fallback
            
            fallback = {
                "decision": "approve", 
                "reason": "Fallback due to parsing error",
                "modifications": {},
                "quality_results": {},
                "sre_results": {},
                "reasoning_trajectory": []
            }
            
            result_dict = extract_json_with_fallback(content, fallback)
        else:
            raise ValueError(f"Unexpected content type: {type(content)}")

        _apply_modifications_if_any(result_dict, project_path)
        _ensure_mandatory_files(project_path, arch_ctx)
        ensure_dependency_file(project_path, arch_ctx)
        
        # Store reflection about this step
        
        step_reflection = {
            "task": objective.get("task", ""),
            "files_modified": list(result_dict.get("modifications", {}).keys()) if result_dict and isinstance(result_dict.get("modifications"), dict) else (result_dict.get("modifications", []) if isinstance(result_dict.get("modifications"), list) else []),
            "success": result_dict.get("decision", "") == "approve" if result_dict else False,
            "summary": result_dict.get("reason", "") if result_dict else "No summary available"
        }
        session_state["reflection_memory"].append(step_reflection)

        # Cap reflection memory to prevent unbounded growth
        MAX_REFLECTIONS = 10
        if len(session_state["reflection_memory"]) > MAX_REFLECTIONS:
            session_state["reflection_memory"] = session_state["reflection_memory"][-MAX_REFLECTIONS:]

        return {
            "status": "ok",
            "result": result_dict,
            "session_state": session_state
        }

    except (json.JSONDecodeError, ValueError) as e:
        # Self-healing fallback structure
        fallback_result = {
            "decision": "reject",
            "reason": f"Failed to parse team response: {str(e)}",
            "modifications": {},
            "quality_results": {},
            "sre_results": {},
            "reasoning_trajectory": []
        }
        return {
            "status": "error",
            "result": fallback_result,
            "session_state": session_state
        }
        
async def _enhance_objective_with_architectural_intelligence(
    objective: Dict[str, Any],
    project_path: Path,
    session_state: Dict[str, Any]
) -> Dict[str, Any]:
    """Enhance objective with architectural intelligence before passing to orchestration agent"""
    
    try:
        from i2c.agents.architecture.architecture_understanding_agent import get_architecture_agent
        
        canvas.info("🏗️ Analyzing architectural context for agentic evolution...")
        
        # Get existing files for analysis
        existing_files = []
        if project_path.exists():
            for file_path in project_path.rglob("*"):
                if file_path.is_file() and not any(ignore in file_path.parts for ignore in ['.git', '__pycache__', '.venv']):
                    existing_files.append(str(file_path.relative_to(project_path)))
        
        # Get content samples for analysis
        content_samples = _get_content_samples_for_analysis(project_path, existing_files[:5])
        
        # Analyze system architecture
        architecture_agent = get_architecture_agent(session_state)
        structural_context = architecture_agent.analyze_system_architecture(
            objective=objective.get("task", ""),
            existing_files=existing_files,
            content_samples=content_samples
        )
        
        # Build enhanced objective with architectural context
        enhanced_objective = objective.copy()
        
        # Add architectural intelligence to the objective
        enhanced_objective.update({
            "architectural_context": {
                "system_type": structural_context.system_type,
                "architecture_pattern": structural_context.architecture_pattern.value,
                "modules": {
                    name: {
                        "boundary_type": module.boundary_type.value,
                        "languages": list(module.languages),
                        "responsibilities": module.responsibilities,
                        "folder_structure": module.folder_structure
                    }
                    for name, module in structural_context.modules.items()
                },
                "file_organization_rules": structural_context.file_organization_rules,
                "constraints": structural_context.constraints,
                "integration_patterns": structural_context.integration_patterns
            }
        })
        
        # FULLSTACK WEB APP SPECIFIC ENHANCEMENTS
        if structural_context.system_type == "fullstack_web_app":
            enhanced_objective = _enhance_fullstack_objective(enhanced_objective, structural_context)
            canvas.info("🌐 Enhanced objective for fullstack web application")
        
        # API SERVICE SPECIFIC ENHANCEMENTS
        elif structural_context.system_type == "api_service":
            enhanced_objective = _enhance_api_service_objective(enhanced_objective, structural_context)
            canvas.info("🔌 Enhanced objective for API service")
        
        # CLI TOOL SPECIFIC ENHANCEMENTS
        elif structural_context.system_type == "cli_tool":
            enhanced_objective = _enhance_cli_tool_objective(enhanced_objective, structural_context)
            canvas.info("💻 Enhanced objective for CLI tool")
        
        canvas.success(f"✅ Architectural intelligence applied: {structural_context.system_type}")
        return enhanced_objective
        
    except Exception as e:
        canvas.warning(f"⚠️ Architectural intelligence failed, using fallback: {e}")
        
        # Fallback: Add basic architectural context
        fallback_context = {
            "system_type": "web_app",
            "architecture_pattern": "fullstack_web", 
            "modules": {},
            "file_organization_rules": {
                "frontend_components": "frontend/src/components",
                "backend_api": "backend/api",
                "main_backend": "backend"
            },
            "constraints": [],
            "integration_patterns": ["REST API"]
        }
        
        enhanced_objective = objective.copy()
        enhanced_objective["architectural_context"] = fallback_context
        return enhanced_objective

def _enhance_fullstack_objective(objective: Dict[str, Any], structural_context) -> Dict[str, Any]:
    """Enhance objective specifically for fullstack web applications"""
    
    # Add fullstack-specific constraints
    fullstack_constraints = [
        "Create proper FastAPI backend structure in backend/ directory",
        "Create proper React frontend structure in frontend/src/ directory",
        "Main backend file must be backend/main.py with FastAPI app instance",
        "Main frontend file must be frontend/src/App.jsx with React component",
        "React components must be in frontend/src/components/ as separate .jsx files",
        "API endpoints must be in backend/api/ directory",
        "Use proper CORS configuration for frontend-backend communication",
        "No mixing of frontend (.jsx) and backend (.py) code in same files",
        "Backend must include proper FastAPI imports and app instance",
        "Frontend must include proper React imports and component exports"
    ]
    
    existing_constraints = objective.get("constraints", [])
    objective["constraints"] = existing_constraints + fullstack_constraints
    
    # Add specific architectural guidance
    objective["architectural_guidance"] = {
        "backend_structure": {
            "main_file": "backend/main.py",
            "required_content": ["from fastapi import FastAPI", "app = FastAPI()", "uvicorn.run()"],
            "api_directory": "backend/api/",
            "models_directory": "backend/models/"
        },
        "frontend_structure": {
            "main_file": "frontend/src/App.jsx",
            "required_content": ["import React", "function App()", "export default App"],
            "components_directory": "frontend/src/components/",
            "styles_directory": "frontend/src/"
        },
        "integration_requirements": [
            "CORS middleware in FastAPI backend",
            "API calls from React frontend to /api endpoints",
            "JSON data exchange between frontend and backend"
        ]
    }
    
    return objective

def _enhance_api_service_objective(objective: Dict[str, Any], structural_context) -> Dict[str, Any]:
    """Enhance objective specifically for API services"""
    
    api_constraints = [
        "Use FastAPI or Flask as the main framework",
        "Organize API endpoints in api/ or routes/ directory", 
        "Include proper request/response models using Pydantic",
        "Add comprehensive input validation and error handling",
        "Include API documentation (OpenAPI/Swagger)",
        "Structure as: main.py, api/routes.py, models/schemas.py"
    ]
    
    existing_constraints = objective.get("constraints", [])
    objective["constraints"] = existing_constraints + api_constraints
    
    return objective

def _enhance_cli_tool_objective(objective: Dict[str, Any], structural_context) -> Dict[str, Any]:
    """Enhance objective specifically for CLI tools"""
    
    cli_constraints = [
        "Main entry point must handle command line arguments properly",
        "Use argparse or click for robust argument parsing",
        "Include comprehensive help text and usage examples",
        "Structure commands in organized modules if complex",
        "Provide clear error messages and exit codes"
    ]
    
    existing_constraints = objective.get("constraints", [])
    objective["constraints"] = existing_constraints + cli_constraints
    
    return objective

def _get_content_samples_for_analysis(project_path: Path, file_list: List[str]) -> Dict[str, str]:
    """Get content samples from key files for architectural analysis"""
    content_samples = {}
    
    for file_rel in file_list:
        try:
            file_path = project_path / file_rel
            if file_path.exists() and file_path.is_file():
                # Read file content (limit size for analysis)
                content = file_path.read_text(encoding='utf-8')
                if len(content) > 1000:
                    content = content[:1000] + "..."
                content_samples[file_rel] = content
        except Exception:
            pass  # Skip files that can't be read
    
    return content_samples

def execute_agentic_evolution_sync(
    objective: Dict[str, Any],
    project_path: Path,
    session_state: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for execute_agentic_evolution. Runs the async function to completion.

    :param objective: The dictionary describing task, constraints, and metadata.
    :param project_path: Path to the current project directory.
    :param session_state: Optional initial session state passed through runs.
    :returns: Final parsed JSON response from the agent team.
    """
    return asyncio.get_event_loop().run_until_complete(
        execute_agentic_evolution(objective, project_path, session_state)
    )

__all__ = [
    "execute_agentic_evolution",
    "execute_agentic_evolution_sync",
    "_enhance_objective_with_architectural_intelligence"
]