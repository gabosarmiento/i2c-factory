from typing import Dict, List, Any
# Try to import the canvas for visual logging - fallback to simple print if not available
try:
    from i2c.cli.controller import canvas
except ImportError:
    class DummyCanvas:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    canvas = DummyCanvas()
# ---------------------------------------------------------------------------
# RAG Integration Utilities - Knowledge Retrieval
# ---------------------------------------------------------------------------

class RagContextBuilder:
    """
    Utility class for building rich context from knowledge base with multiple retrieval strategies.
    
    This class provides methods to:
    1. Retrieve basic context based on a single query
    2. Perform multi-step/chained retrieval for complex tasks
    3. Synthesize and deduplicate knowledge chunks
    4. Adapt retrieval to different model context sizes
    """
    
    def __init__(self, knowledge_base=None, default_chunk_count=5, max_tokens=6000):
        """
        Initialize the RAG context builder.
        
        Args:
            knowledge_base: The knowledge base to retrieve from
            default_chunk_count: Default number of chunks to retrieve
            max_tokens: Maximum tokens for context (default 6000)
        """
        self.knowledge_base = knowledge_base
        self.default_chunk_count = default_chunk_count
        self.max_tokens = max_tokens
        
    def retrieve_context(self, query: str, chunk_count: int = None) -> str:
        """Retrieve context from knowledge base for a query"""
        if not self.knowledge_base:
            return ""
                
        chunks_to_retrieve = chunk_count or self.default_chunk_count
        
        try:
            # Log the retrieval operation
            canvas.info(f"[RAG] Retrieving {chunks_to_retrieve} chunks for query: {query[:100]}...")
            
            # Use the existing retrieve_knowledge method 
            chunks = self.knowledge_base.retrieve_knowledge(
                query=query,
                limit=chunks_to_retrieve
            )
            
            if not chunks:
                canvas.info("[RAG] No relevant chunks found")
                return ""
                
            # Format and return the context
            context_text = self._format_chunks(chunks)
            
            # Log stats about retrieved context
            canvas.info(f"[RAG] Retrieved {len(chunks)} chunks ({len(context_text)} chars)")
            
            return context_text
        except Exception as e:
            canvas.warning(f"[RAG] Error retrieving context: {e}")
            return ""
        
    def retrieve_composite_context(self, 
                                  main_query: str, 
                                  sub_queries: List[str] = None,
                                  main_chunk_count: int = None,
                                  sub_chunk_count: int = 2) -> str:
        """
        Retrieve composite context from multiple queries for complex tasks.
        
        This performs a primary retrieval on the main query, then additional 
        retrievals on sub-queries, and combines the results with deduplication.
        
        Args:
            main_query: The primary query
            sub_queries: List of secondary queries for additional context
            main_chunk_count: Number of chunks for main query
            sub_chunk_count: Number of chunks for each sub-query
            
        Returns:
            Combined context as a formatted string
        """
        if not self.knowledge_base:
            return ""
            
        try:
            all_chunks = []
            seen_content = set()  # For deduplication
            
            # Retrieve main context
            main_chunks = self._retrieve_raw_chunks(
                main_query, 
                main_chunk_count or self.default_chunk_count
            )
            
            # Add main chunks first (priority)
            for chunk in main_chunks:
                content = chunk.get("content", "")
                if content and content not in seen_content:
                    all_chunks.append(chunk)
                    seen_content.add(content)
            
            # Process sub-queries if any and if we still have token budget
            if sub_queries:
                # Log the sub-queries
                canvas.info(f"[RAG] Processing {len(sub_queries)} sub-queries for composite context")
                
                for sub_query in sub_queries:
                    sub_chunks = self._retrieve_raw_chunks(sub_query, sub_chunk_count)
                    
                    # Add only new, non-duplicate chunks
                    for chunk in sub_chunks:
                        content = chunk.get("content", "")
                        if content and content not in seen_content:
                            all_chunks.append(chunk)
                            seen_content.add(content)
                            
                    # If we've hit our approximate token budget, stop adding chunks
                    if self._estimate_tokens(all_chunks) >= self.max_tokens:
                        canvas.info(f"[RAG] Reached token budget with {len(all_chunks)} chunks")
                        break
            
            # Format the combined chunks
            if not all_chunks:
                return ""
                
            combined_context = self._format_chunks(all_chunks)
            
            # Log stats about composite context
            canvas.info(f"[RAG] Composite context: {len(all_chunks)} chunks from {1 + (len(sub_queries) if sub_queries else 0)} queries")
            canvas.info(f"[RAG] Approximate tokens: ~{len(combined_context)//4}")
            
            return combined_context
            
        except Exception as e:
            canvas.warning(f"[RAG] Error retrieving composite context: {e}")
            return ""
    
    def _retrieve_raw_chunks(self, query: str, chunk_count: int) -> List[Dict[str, Any]]:
        """Retrieve raw chunks from knowledge base without formatting"""
        try:
            chunks = self.knowledge_base.search(
                query=query,
                limit=chunk_count
            )
            return chunks or []
        except Exception:
            return []
            
    def _format_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """Format chunks into a readable context string"""
        formatted_chunks = []
        
        for i, chunk in enumerate(chunks):
            source = chunk.get("source", "Unknown source")
            content = chunk.get("content", "").strip()
            
            if content:
                formatted_chunks.append(f"[KNOWLEDGE {i+1}] SOURCE: {source}\n{content}")
        
        return "\n\n".join(formatted_chunks)
        
    def _estimate_tokens(self, chunks: List[Dict[str, Any]]) -> int:
        """Roughly estimate token count for a list of chunks"""
        total_chars = sum(len(chunk.get("content", "")) for chunk in chunks)
        # Very rough estimate: ~4 chars per token for English text
        return total_chars // 4

    def synthesize_context(self, 
                          query: str,
                          chunks: List[Dict[str, Any]],
                          synthesizer_model=None) -> str:
        """
        Synthesize chunks into a coherent summary using an LLM.
        
        This is an advanced feature for when raw chunks need consolidation.
        
        Args:
            query: The original query for context
            chunks: List of chunks to synthesize
            synthesizer_model: Optional LLM to use for synthesis
            
        Returns:
            Synthesized context as a string
        """
        # Fallback to basic formatting if no synthesizer model
        if not synthesizer_model:
            return self._format_chunks(chunks)
            
        try:
            # Simple implementation - can be expanded
            content_text = "\n\n".join([
                f"CHUNK {i+1} ({chunk.get('source', 'unknown')}):\n{chunk.get('content', '')}"
                for i, chunk in enumerate(chunks)
            ])
            
            # Use the model to synthesize the context
            prompt = f"""
            Below are chunks of knowledge relevant to the query: "{query}"
            
            {content_text}
            
            Synthesize these chunks into a coherent, non-redundant summary that includes all key 
            information relevant to the query. Focus on maintaining technical accuracy and details.
            """
            
            response = synthesizer_model.run(prompt)
            synthesis = getattr(response, 'content', str(response)).strip()
            
            if synthesis:
                canvas.info(f"[RAG] Successfully synthesized {len(chunks)} chunks into {len(synthesis)} chars")
                return synthesis
            else:
                return self._format_chunks(chunks)
                
        except Exception as e:
            canvas.warning(f"[RAG] Error synthesizing context: {e}")
            return self._format_chunks(chunks)
    