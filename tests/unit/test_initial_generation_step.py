import json
import tempfile
from pathlib import Path
import re
import pytest

from i2c.workflow.scenario_processor import ScenarioProcessor
from i2c.cli.controller import canvas

PDF_PATH = Path("src/i2c/docs/agno_cheat_sheet.pdf")
AGNO_IMPORT_PATTERNS = [
    r'from\s+agno\.knowledge\.pdf_url\s+import\s+PDFUrlKnowledgeBase',
    r'from\s+agno\.agent\s+import\s+AgentKnowledge',
    r'from\s+agno\.vectordb\.pgvector\s+import\s+PgVector',
]


def create_test_scenario():
    """
    Create a scenario with a knowledge step (loading the AGNO PDF)
    followed by an initial_generation step that should _use_ that knowledge.
    Returns the path to the JSON file and the temp directory (so we can cleanup).
    """
    scenario = {
        "name": "AGNO Knowledge Application Test",
        "description": "Ensure initial generation uses PDF knowledge",
        "steps": [
            {
                "type": "knowledge",
                "name": "Ingest AGNO Cheat Sheet",
                "doc_path": str(PDF_PATH),
                "doc_type": "AGNO Cheat Sheet",
                "framework": "AGNO",
                "version": "1.0",
                "project_name": "agno_cli_reflector",  
                "global": True
            },
            {
                "type": "initial_generation",
                "name": "Generate CLI Reflection Tool",
                "prompt": (
                    "Based on the AGNO cheat sheet, build a CLI tool to test reflection. "
                    "Use PDFUrlKnowledgeBase and vector DB to load documents."
                ),
                "project_name": "agno_cli_reflector",
                "input": {
                    "instruction": "IGNORED"
                },
                "output_type": "code",
                "agent": "CodeBuilderAgent"
            }
        ]
    }

    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / "scenario.json"
    path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    return path, tmp


class TrackingProcessor(ScenarioProcessor):
    """
    Subclass that tracks whether ingestion was actually called
    during process_scenario().
    """
    def __init__(self, scenario_path: str):
        super().__init__(scenario_path=scenario_path)
        self.ingested_docs = []

    def _handle_knowledge_ingestion(self, document_path, doc_type, metadata, *, is_folder=False, force_refresh=False):
        """Override the actual method that gets called"""
        # Record the document being ingested
        self.ingested_docs.append(str(document_path))
        canvas.info(f"🔍 DEBUG: Tracked ingestion of {document_path}")
        
        # Call the original method
        return super()._handle_knowledge_ingestion(
            document_path, doc_type, metadata, 
            is_folder=is_folder, force_refresh=force_refresh
        )

@pytest.mark.integration
def test_agno_knowledge_application():
    canvas.info("🔎 Starting AGNO knowledge application integration test")

    # 1) Create scenario JSON
    scenario_path, tmpdir = create_test_scenario()

    # 2) Run it end-to-end
    processor = TrackingProcessor(str(scenario_path))
    success = processor.process_scenario()
    assert success, "❌ process_scenario() failed"

    # 3) Check ingestion happened
    assert processor.ingested_docs, "❌ Knowledge ingestion was never triggered"

    # ✅ 4) Use the actual generated project path
    scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
    project_name = processor.scenario.project_name
    output_dir = Path("output") / project_name
    assert output_dir.exists(), f"❌ Output dir not found: {output_dir}"
    canvas.info(f"📁 Found generated output at: {output_dir}")

    # 5) Read all generated code into one string
    py_files = list(output_dir.rglob("*.py"))
    assert py_files, "❌ No Python files generated"
    code = "\n".join(f.read_text(encoding="utf-8") for f in py_files)

    # 6) Assert at least one AGNO import from the cheat-sheet appears
    found = []
    for pattern in AGNO_IMPORT_PATTERNS:
        if re.search(pattern, code):
            found.append(pattern)

    if not found:
        canvas.error("❌ None of the expected AGNO imports were found in generated code.")
        canvas.info("Searched patterns:")
        for pat in AGNO_IMPORT_PATTERNS:
            canvas.info(f"  • {pat}")
    else:
        canvas.success(f"✅ Found AGNO imports: {found}")

    assert found, "❌ Generated code did not apply any AGNO cheat-sheet knowledge"
