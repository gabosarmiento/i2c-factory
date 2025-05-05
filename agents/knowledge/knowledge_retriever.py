# agents/knowledge/knowledge_retriever.py
from typing import Dict, List, Any, Optional, Tuple
from agno.agent import Agent
from agents.reflective.context_aware_operator import ContextAwareOperator
from agents.budget_manager import BudgetManagerAgent
from agents.knowledge.base import EnhancedLanceDb

class KnowledgeRetrieverAgent(ContextAwareOperator):
    """Multi-stage knowledge retrieval with filtering and re-ranking"""
    
    def __init__(
        self,
        budget_manager: BudgetManagerAgent,
        vector_db: EnhancedLanceDb,
        embed_model: Any,
        reranker: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            budget_manager=budget_manager,
            operation_type="knowledge_retrieval",
            max_reasoning_steps=3,
            default_model_tier="middle"
        )
        
        self.vector_db = vector_db
        self.embed_model = embed_model
        self.reranker = reranker
        
        # Create reasoning agent for query analysis
        self.reasoning_agent = Agent(
            model=self.model,
            name="KnowledgeReasoningAgent",
            instructions=[
                "Analyze queries to extract key concepts",
                "Generate optimal search terms",
                "Identify filtering criteria"
            ]
        )
    
    def execute(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        max_results: int = 10,
        **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """Execute multi-stage knowledge retrieval"""
        phase_id = "knowledge_retrieval"
        self.cost_tracker.start_phase(
            phase_id,
            f"Retrieve knowledge for: {query[:50]}...",
            model_id=str(self.model)
        )
        
        try:
            # Stage 1: Query Analysis and Term Generation
            search_terms = self._analyze_query(query)
            
            # Stage 2: Initial Retrieval with Filters
            initial_results = self._initial_retrieval(
                search_terms,
                filters,
                max_results * 2  # Retrieve more for re-ranking
            )
            
            # Stage 3: Re-ranking and Final Selection
            final_results = self._rerank_results(
                query,
                initial_results,
                max_results
            )
            
            # Stage 4: Result Validation
            validated_results = self._validate_results(final_results)
            
            self.cost_tracker.end_phase(
                success=True,
                result={
                    "retrieved_count": len(validated_results),
                    "search_terms": search_terms,
                    "filters_applied": filters
                }
            )
            
            return True, {
                "status": "success",
                "results": validated_results,
                "search_metadata": {
                    "query": query,
                    "terms": search_terms,
                    "filters": filters,
                    "initial_count": len(initial_results),
                    "final_count": len(validated_results)
                }
            }
            
        except Exception as e:
            self.cost_tracker.end_phase(success=False, feedback=str(e))
            return False, {
                "status": "error",
                "error": str(e),
                "query": query
            }
    
    def _analyze_query(self, query: str) -> List[str]:
        """Analyze query to extract search terms and concepts"""
        prompt = f"""
        Analyze this query and extract key search terms:
        Query: {query}
        
        Extract:
        1. Main concepts
        2. Technical terms
        3. Framework/library names
        4. Version requirements
        
        Return as a JSON list of search terms.
        """
        
        response = self.reasoning_agent.run(prompt)
        # Parse response to extract terms
        terms = self._parse_search_terms(response.content)
        return terms
    
    def _initial_retrieval(
        self,
        search_terms: List[str],
        filters: Optional[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform initial retrieval using hybrid search"""
        # Combine search terms
        combined_query = " ".join(search_terms)
        
        # Execute search with filters
        results = self.vector_db.search(
            query=combined_query,
            filters=filters,
            limit=limit,
            include_metadata=True
        )
        
        return results
    
    def _rerank_results(
        self,
        original_query: str,
        results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Re-rank results using advanced scoring"""
        if not self.reranker:
            # Simple scoring based on metadata
            scored_results = []
            for result in results:
                score = self._calculate_relevance_score(original_query, result)
                result['relevance_score'] = score
                scored_results.append(result)
            
            # Sort by score
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return scored_results[:limit]
        
        # Use provided reranker
        reranked = self.reranker.rerank(original_query, results)
        return reranked[:limit]
    
    def _calculate_relevance_score(
        self,
        query: str,
        result: Dict[str, Any]
    ) -> float:
        """Calculate relevance score based on multiple factors"""
        score = 0.0
        
        # Base similarity score
        if 'score' in result:
            score += result['score'] * 0.5
        
        # Boost for exact matches
        content = result.get('content', '').lower()
        query_terms = query.lower().split()
        for term in query_terms:
            if term in content:
                score += 0.1
        
        # Boost for recent documents
        metadata = result.get('metadata', {})
        if 'last_updated' in metadata:
            # Implement recency boost
            score += 0.1
        
        # Boost for document type relevance
        if metadata.get('document_type') == 'api_documentation':
            score += 0.2
        
        return score
    
    def _validate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean up results"""
        validated = []
        for result in results:
            # Add validation logic here
            if self._is_valid_result(result):
                validated.append(result)
        return validated
    
    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """Check if result meets quality criteria"""
        # Implement validation logic
        return True