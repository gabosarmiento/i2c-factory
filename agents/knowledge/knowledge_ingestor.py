# agents/knowledge/knowledge_ingestor.py

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from agents.budget_manager import BudgetManagerAgent
from agents.reflective.context_aware_operator import ContextAwareOperator
from .base import (
    EnhancedLanceDb,
    DocumentationKnowledgeBase,
    PDFDocumentationKnowledgeBase,
    MarkdownDocumentationKnowledgeBase,
    HTMLDocumentationKnowledgeBase,
    APIDocumentationKnowledgeBase,
)
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder

from agno.vectordb.lancedb import SearchType  # Make sure this import works
import traceback

class KnowledgeIngestorAgent(ContextAwareOperator):
    """Processes and ingests documentation with budget awareness"""

    def __init__(
        self,
        budget_manager: BudgetManagerAgent,
        knowledge_space: str = "default",
        **kwargs
    ):
        super().__init__(
            budget_manager=budget_manager,
            operation_type="knowledge_ingestion",
            max_reasoning_steps=3,
            default_model_tier="middle"
        )
        self.knowledge_space = knowledge_space
        self.knowledge_bases = {}

    def execute(
        self,
        document_path: Path,
        document_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Ingest a document with budget checks and validation"""
        phase_id = "document_ingestion"
        self.cost_tracker.start_phase(
            phase_id,
            f"Ingest document: {document_path.name}",
            model_id="knowledge_ingestor"
        )

        try:
            if not document_path.exists():
                raise FileNotFoundError(f"Document not found: {document_path}")

            kb = self._get_or_create_knowledge_base(document_type, document_path)

            # Request budget approval
            
            if self.budget_manager:
                description = f"Ingest document: {document_path.name}"
                prompt      = f"Load and chunk {document_path.name} into KB"
                model_id    = self.operation_type or "knowledge_ingestor"
                if not self.budget_manager.request_approval(
                    description,   # e.g. "Ingest Solidity.pdf"
                    prompt,   # e.g. "Load and chunk Solidity.pdf"
                    model_id       # e.g. "knowledge_ingestor"
                ):
                    raise Exception("Budget approval denied")

            # Load into knowledge base (includes parsing)
            success = kb.load_document(
                document_path,
                document_type,
                metadata=metadata
            )

            self.cost_tracker.end_phase(
                success=success,
                result={
                    "document_path": str(document_path),
                    "document_type": document_type
                }
            )

            return success, {
                "status": "success" if success else "failed",
                "document_path": str(document_path),
                "document_type": document_type,
                "cost_summary": self.cost_tracker.get_cost_summary()
            }

        except Exception as e:
            tb = traceback.format_exc()
            self.cost_tracker.end_phase(success=False, feedback=str(e))
            return False, {
                "status": "error",
                "error": str(e) or type(e).__name__,
                "traceback": tb,
                "document_path": str(document_path)
            }

    def _get_or_create_knowledge_base(self, document_type: str, document_path: Path):
        """Get or create appropriate knowledge base for document type"""
        embedder = SentenceTransformerEmbedder()
        # Build the vector database as before
        vector_db = EnhancedLanceDb(
            knowledge_space=self.knowledge_space,
            table_name=f"knowledge_{document_type}",
            uri="data/lancedb",
            search_type=SearchType.hybrid,
            embedder=embedder
        )

        # Pick the right KB class based on the file suffix
        suffix = document_path.suffix.lower()
        if suffix == ".pdf":
            kb_cls = PDFDocumentationKnowledgeBase
        elif suffix in [".md", ".markdown"]:
            kb_cls = MarkdownDocumentationKnowledgeBase
        elif suffix in [".html", ".htm"]:
            kb_cls = HTMLDocumentationKnowledgeBase
        elif document_type == "api_documentation":
            kb_cls = APIDocumentationKnowledgeBase
        else:
            kb_cls = DocumentationKnowledgeBase

        # Instantiate and return it
        return kb_cls(
            knowledge_space=self.knowledge_space,
            vector_db=vector_db,
            budget_manager=self.budget_manager
        )

    def _estimate_cost(self, document_path: Path) -> Dict[str, float]:
        """Estimate processing cost for a document"""
        file_size = document_path.stat().st_size
        estimated_tokens = file_size / 4
        estimated_cost = estimated_tokens * 0.0001

        return {
            "tokens": estimated_tokens,
            "cost": estimated_cost
        }
