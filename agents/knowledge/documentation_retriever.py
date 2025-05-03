# /agents/knowledge/documentation_retriever.py
"""DocumentationRetrieverAgent

Retrieves external documentation from the knowledge_base table to enhance RAG context.
Integrates with PlanRefinementOperator for plan improvement.
"""

from __future__ import annotations
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from cli.controller import canvas
from llm_providers import llm_highest
from agno.agent import Agent
from agents.reflective.context_aware_operator import ContextAwareOperator, ValidationHook
from db_utils import query_context, TABLE_KNOWLEDGE_BASE

class DocumentationRetrieverAgent(ContextAwareOperator):
    """Retrieves external documentation using LanceDB vector search."""

    def __init__(
        self,
        budget_manager,
        embed_model,
        max_reasoning_steps: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(
            budget_manager=budget_manager,
            operation_type="documentation_retrieval",
            max_reasoning_steps=max_reasoning_steps,
            default_model_tier="highest",
        )
        self.embed_model = embed_model
        self.reasoning_agent = Agent(
            model=llm_highest,
            reasoning=True,
            name="DocumentationRetriever",
            description="Retrieves relevant external documentation",
            instructions=[
                "You are an expert in retrieving relevant documentation.",
                "Analyze the query and context to find the most relevant documentation.",
                "Return structured JSON with source, content, and relevance score.",
            ],
        )
        self._register_default_validation_hooks()

    def _register_default_validation_hooks(self) -> None:
        """Register validation hooks for retrieved documentation."""
        self.register_validation_hook(
            ValidationHook(
                hook_id="doc_relevance",
                hook_type="relevance",
                description="Ensures retrieved docs are relevant to the query",
                validation_function=self._validate_doc_relevance,
                priority=8,
            )
        )

    def execute(
        self,
        query: str,
        project_path: Path,
        language: str,
        db_connection,
    ) -> Tuple[bool, Dict]:
        """Retrieve relevant documentation for a given query."""
        phase_id = "retrieve_docs"
        self.cost_tracker.start_phase(
            phase_id,
            "Retrieve external documentation",
            model_id=getattr(llm_highest, "id", "Unknown"),
        )

        try:
            # Generate embedding for the query - handle both numpy arrays and lists
            embedding = self.embed_model.encode(query)
            if isinstance(embedding, np.ndarray):
                query_vector = embedding.tolist()
            else:
                query_vector = list(embedding)

            # Query LanceDB knowledge_base table
            results_df = query_context(db_connection, TABLE_KNOWLEDGE_BASE, query_vector, limit=5)
            if results_df is None or results_df.empty:
                canvas.warning("No relevant documentation found.")
                self.cost_tracker.end_phase(False, feedback="No documentation retrieved")
                return False, {"error": "No documentation retrieved", "reasoning_trajectory": self.cost_tracker.trajectory}

            # Format results for LLM analysis
            docs = [{"source": row["source"], "content": row["content"]} for _, row in results_df.iterrows()]
            analysis_prompt = self._prepare_analysis_prompt(query, docs, language)
            analysis_result = self._execute_reasoning_step(
                phase_id=phase_id,
                step_id="analyze_docs",
                prompt=analysis_prompt,
                model_tier="highest",
            )

            if not analysis_result:
                self.cost_tracker.end_phase(False, feedback="Failed to analyze documentation")
                return False, {"error": "Failed to analyze documentation", "reasoning_trajectory": self.cost_tracker.trajectory}

            selected_docs = self._extract_selected_docs(analysis_result["response"])
            validation = self.run_validation_hooks(selected_docs)
            valid = bool(selected_docs) and all(v["outcome"] for v in validation.values())
            self.cost_tracker.record_validation("analyze_docs", valid, json.dumps(validation, indent=2))

            iterations = 0
            while not valid and iterations < self.max_reasoning_steps:
                fix_prompt = self._prepare_fix_prompt(query, selected_docs, validation)
                fix_result = self._execute_reasoning_step(
                    phase_id=phase_id,
                    step_id=f"fix_docs_{iterations}",
                    prompt=fix_prompt,
                    model_tier="highest",
                )
                if not fix_result:
                    break
                selected_docs = self._extract_selected_docs(fix_result["response"])
                validation = self.run_validation_hooks(selected_docs)
                valid = bool(selected_docs) and all(v["outcome"] for v in validation.values())
                self.cost_tracker.record_validation(f"fix_docs_{iterations}", valid, json.dumps(validation, indent=2))
                iterations += 1

            self.cost_tracker.end_phase(valid, result=selected_docs)
            final = {
                "documents": selected_docs,
                "valid": valid,
                "iterations": iterations,
                "reasoning_trajectory": self.cost_tracker.trajectory,
            }
            self.cost_tracker.complete_operation(success=valid, final_result=final)
            return valid, final

        except Exception as e:
            canvas.error(f"Error in documentation retrieval: {e}")
            self.cost_tracker.complete_operation(success=False, final_result={"error": str(e), "reasoning_trajectory": self.cost_tracker.trajectory})
            return False, {"error": str(e), "reasoning_trajectory": self.cost_tracker.trajectory}

    def _prepare_analysis_prompt(self, query: str, docs: List[Dict], language: str) -> str:
        """Craft prompt for analyzing retrieved documentation."""
        return f"""
# Documentation Analysis Task
## Query
{query}
## Language
{language}
## Retrieved Documents
{json.dumps(docs, indent=2)}
## Task
Analyze the retrieved documents and select the most relevant ones.
Return a JSON array of selected documents with source, content, and relevance_score (0-1).
"""

    def _prepare_fix_prompt(self, query: str, docs: List[Dict], validation_results: Dict) -> str:
        """Craft prompt for fixing invalid documentation selections."""
        feedback = "\n".join(
            f"- {hid}: {'✅' if res['outcome'] else '❌'} {res['feedback']}"
            for hid, res in validation_results.items()
            if not res["outcome"]
        )
        return f"""
# Documentation Fix Task
## Query
{query}
## Current Selection
{json.dumps(docs, indent=2)}
## Validation Issues
{feedback}
## Task
Return a corrected JSON array of selected documents.
"""

    def _extract_selected_docs(self, response: str) -> List[Dict]:
        """Extract selected documents from LLM response."""
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if match:
            try:
                obj = json.loads(match.group(1))
                return obj if isinstance(obj, list) else []
            except Exception:
                pass
        canvas.warning("Failed to extract documents; returning empty list.")
        return []

    @staticmethod
    def _validate_doc_relevance(docs: List[Dict]) -> Tuple[bool, str]:
        """Validate that selected documents are relevant."""
        if not docs:
            return False, "No documents selected."
        for doc in docs:
            if not all(key in doc for key in ["source", "content", "relevance_score"]):
                return False, "Document missing required fields."
            if not (0 <= doc["relevance_score"] <= 1):
                return False, "Relevance score out of range."
        return True, "Documents are relevant and well-formed."