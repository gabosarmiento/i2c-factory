
from pathlib import Path
from typing import Dict, Any, Optional, List
import os
import asyncio
import datetime
import json
import re
from i2c.utils.json_extraction import extract_json
from agno.team import Team
from agno.agent import Message
from i2c.workflow.orchestration_team import build_orchestration_team
from i2c.cli.controller import canvas
from i2c.workflow.modification.file_operations import write_files_to_disk
from i2c.agents.quality_team.utils.language_detector import LanguageDetector

# ----------------------------------------------------------------------
# Put this somewhere above execute_agentic_evolution(), e.g. right after
# _apply_modifications_if_any() or together with your other utils.
# ----------------------------------------------------------------------
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
    }.get(arch_ctx.get("system_type"), [])

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

    if "python" in preferred:
        req_file = project_path / "requirements.txt"
        if not req_file.exists():
            req_file.write_text("fastapi\nuvicorn[standard]\npydantic\nhttpx\npytest\n")

    if "javascript" in preferred:
        # --- Force a single, root-level package.json for the Vite/React/Tailwind stack ---
        root_pkg = project_path / "package.json"
        root_pkg.write_text(
            """{
    "name": "app",
    "version": "1.0.0",
    "private": true,
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
        "@vitejs/plugin-react": "^4.0.0",
        "tailwindcss": "^3.3.0"
    }
    }"""
        )

    # Nuke any nested package.json (e.g. frontend/package.json) to avoid confusion
    nested_pkg = project_path / "frontend" / "package.json"
    if nested_pkg.exists():
        nested_pkg.unlink()
        
    if "go" in preferred:
        go_mod = project_path / "go.mod"
        if not go_mod.exists():
            go_mod.write_text("module app\n\ngo 1.20\nrequire github.com/gofiber/fiber/v2 v2.42.0\n")

    if "java" in preferred:
        pom_file = project_path / "pom.xml"
        if not pom_file.exists():
            pom_file.write_text("""<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>app</artifactId>
  <version>1.0-SNAPSHOT</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter</artifactId>
      <version>2.7.0</version>
    </dependency>
  </dependencies>
</project>""")


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
            "existing_files": os.listdir(project_path) if project_path.exists() else []
        }

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
    desired_stacks = set()
    if "react" in objective_text or "vite" in objective_text:
        desired_stacks.add("javascript")
    if "fastapi" in objective_text or "streamlit" in objective_text:
        desired_stacks.add("python")
    if "spring boot" in objective_text:
        desired_stacks.add("java")
    if "go" in objective_text or "fiber" in objective_text:
        desired_stacks.add("go")
    # Apply strict filtering
    filtered_stacks = {
        lang: config
        for lang, config in preferred_stacks.items()
        if lang in desired_stacks
    }
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
            clean_content = content.strip()

            # Remove Markdown fences
            if clean_content.startswith("```"):
                lines = clean_content.splitlines()
                if lines[0].startswith("```") and lines[-1].startswith("```"):
                    clean_content = "\n".join(lines[1:-1]).strip()

            # Clean up tool-call wrapper
            if "<function=" in clean_content and "{" in clean_content:
                json_match = re.search(r'\{.*\}', clean_content, re.DOTALL)
                if json_match:
                    clean_content = json_match.group(0)

            # Try parsing
            result_dict = json.loads(clean_content)
        else:
            raise ValueError(f"Unexpected content type: {type(content)}")

        _apply_modifications_if_any(result_dict, project_path)
        _ensure_mandatory_files(project_path, arch_ctx)
        ensure_dependency_file(project_path, arch_ctx)

        return {
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
