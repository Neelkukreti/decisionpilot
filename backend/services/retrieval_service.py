"""
Retrieval Service - Semantic Search over Meeting Memory

Provides evidence retrieval via:
- Vector similarity search (Pinecone)
- Keyword search (BM25)
- Hybrid ranking (semantic + keyword)
- Citation tracking

Mock mode: Uses in-memory vectors for testing without Pinecone
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime
import os

from config import get_config


class RetrievalService:
    """Semantic search over embedded meeting content"""
    
    def __init__(self, mock_mode: bool = None):
        config = get_config()
        
        self.mock_mode = mock_mode if mock_mode is not None else config.MOCK_MODE
        self.embedding_dim = 1024  # Nova embeddings dimension
        
        # Mock mode: In-memory store
        if self.mock_mode:
            self.memory_store = []  # List of (id, vector, metadata)
            self.keyword_index = {}  # Keyword -> doc IDs
        else:
            # Real mode: Pinecone client
            import pinecone
            
            pinecone.init(
                api_key=config.PINECONE_API_KEY,
                environment=config.PINECONE_ENV
            )
            
            self.index = pinecone.Index(config.PINECONE_INDEX)
    
    def index_meeting_content(
        self,
        meeting_id: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Index meeting content for retrieval
        
        Args:
            meeting_id: Unique meeting identifier
            chunks: List of content chunks with embeddings
                    Format: [{
                        "id": "chunk_001",
                        "embedding": [1024-dim vector],
                        "content": "text content",
                        "metadata": {...}
                    }]
        
        Returns:
            Indexing stats
        """
        if self.mock_mode:
            return self._mock_index(meeting_id, chunks)
        
        # Real Pinecone indexing
        vectors = [
            (
                f"{meeting_id}_{chunk['id']}",
                chunk['embedding'],
                {
                    "meeting_id": meeting_id,
                    "content": chunk['content'],
                    **chunk.get('metadata', {})
                }
            )
            for chunk in chunks
        ]
        
        self.index.upsert(vectors=vectors)
        
        return {
            "meeting_id": meeting_id,
            "chunks_indexed": len(chunks),
            "index_name": self.index._index_name,
            "timestamp": datetime.now().isoformat()
        }
    
    def retrieve(
        self,
        query: str,
        query_embedding: np.ndarray,
        meeting_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks via semantic search
        
        Args:
            query: Text query
            query_embedding: Query vector (1024-dim)
            meeting_id: Filter to specific meeting (optional)
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
        
        Returns:
            List of matching chunks with scores
        """
        if self.mock_mode:
            return self._mock_retrieve(
                query,
                query_embedding,
                meeting_id,
                top_k,
                min_score
            )
        
        # Real Pinecone query
        filters = {"meeting_id": meeting_id} if meeting_id else None
        
        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            filter=filters,
            include_metadata=True
        )
        
        # Filter by score and format
        matches = []
        for match in results.matches:
            if match.score >= min_score:
                matches.append({
                    "id": match.id,
                    "score": match.score,
                    "content": match.metadata.get("content", ""),
                    "metadata": match.metadata
                })
        
        return matches
    
    def hybrid_search(
        self,
        query: str,
        query_embedding: np.ndarray,
        meeting_id: Optional[str] = None,
        top_k: int = 5,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and keyword matching
        
        Args:
            query: Text query
            query_embedding: Query vector
            meeting_id: Optional meeting filter
            top_k: Number of results
            semantic_weight: Weight for semantic score (0-1)
            keyword_weight: Weight for keyword score (0-1)
        
        Returns:
            Ranked results combining both signals
        """
        # Get semantic results
        semantic_results = self.retrieve(
            query,
            query_embedding,
            meeting_id,
            top_k=top_k * 2  # Get more candidates
        )
        
        # Get keyword results
        keyword_results = self._keyword_search(
            query,
            meeting_id,
            top_k=top_k * 2
        )
        
        # Combine and re-rank
        combined = self._merge_results(
            semantic_results,
            keyword_results,
            semantic_weight,
            keyword_weight
        )
        
        return combined[:top_k]
    
    def get_context_window(
        self,
        chunk_id: str,
        window_size: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get surrounding chunks for context
        
        Args:
            chunk_id: ID of target chunk
            window_size: Number of chunks before/after
        
        Returns:
            List of chunks in temporal order
        """
        if self.mock_mode:
            return self._mock_context_window(chunk_id, window_size)
        
        # In real mode, would query Pinecone with timestamp filters
        # For now, return placeholder
        return []
    
    def _keyword_search(
        self,
        query: str,
        meeting_id: Optional[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Simple keyword matching (BM25-like)"""
        if self.mock_mode:
            return self._mock_keyword_search(query, meeting_id, top_k)
        
        # In real mode, would use Elasticsearch or similar
        return []
    
    def _merge_results(
        self,
        semantic: List[Dict],
        keyword: List[Dict],
        semantic_weight: float,
        keyword_weight: float
    ) -> List[Dict]:
        """Merge and re-rank results from both sources"""
        # Create score map
        scores = {}
        
        # Add semantic scores
        for i, result in enumerate(semantic):
            doc_id = result['id']
            # Decay by rank
            rank_score = 1.0 / (i + 1)
            scores[doc_id] = {
                'semantic': result['score'] * rank_score * semantic_weight,
                'keyword': 0,
                'data': result
            }
        
        # Add keyword scores
        for i, result in enumerate(keyword):
            doc_id = result['id']
            rank_score = 1.0 / (i + 1)
            
            if doc_id in scores:
                scores[doc_id]['keyword'] = result['score'] * rank_score * keyword_weight
            else:
                scores[doc_id] = {
                    'semantic': 0,
                    'keyword': result['score'] * rank_score * keyword_weight,
                    'data': result
                }
        
        # Combine and sort
        ranked = []
        for doc_id, data in scores.items():
            total_score = data['semantic'] + data['keyword']
            result = data['data'].copy()
            result['combined_score'] = total_score
            ranked.append(result)
        
        ranked.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return ranked
    
    # Mock mode implementations
    
    def _mock_index(
        self,
        meeting_id: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Mock indexing - store in memory"""
        for chunk in chunks:
            chunk_id = f"{meeting_id}_{chunk['id']}"
            vector = chunk.get('embedding', np.zeros(self.embedding_dim))
            
            metadata = {
                "meeting_id": meeting_id,
                "content": chunk.get('content', ''),
                "chunk_id": chunk['id'],
                **chunk.get('metadata', {})
            }
            
            self.memory_store.append((chunk_id, vector, metadata))
            
            # Build keyword index
            words = chunk.get('content', '').lower().split()
            for word in words:
                if word not in self.keyword_index:
                    self.keyword_index[word] = []
                self.keyword_index[word].append(chunk_id)
        
        return {
            "meeting_id": meeting_id,
            "chunks_indexed": len(chunks),
            "total_indexed": len(self.memory_store),
            "mock_mode": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def _mock_retrieve(
        self,
        query: str,
        query_embedding: np.ndarray,
        meeting_id: Optional[str],
        top_k: int,
        min_score: float
    ) -> List[Dict[str, Any]]:
        """Mock retrieval - cosine similarity search"""
        if len(self.memory_store) == 0:
            # Return placeholder results for testing
            return [
                {
                    "id": f"mock_chunk_{i}",
                    "score": 0.85 - (i * 0.1),
                    "content": f"Mock evidence chunk {i+1} related to: {query}",
                    "metadata": {
                        "timestamp": 120.5 + (i * 30),
                        "speaker": "Mock Speaker",
                        "source_type": "transcript"
                    }
                }
                for i in range(min(top_k, 3))
            ]
        
        # Calculate similarities
        results = []
        
        for chunk_id, vector, metadata in self.memory_store:
            # Filter by meeting_id if specified
            if meeting_id and metadata.get('meeting_id') != meeting_id:
                continue
            
            # Cosine similarity
            if isinstance(query_embedding, np.ndarray):
                similarity = self._cosine_similarity(query_embedding, vector)
            else:
                # If embedding is zeros, use mock score
                similarity = 0.75
            
            if similarity >= min_score:
                results.append({
                    "id": chunk_id,
                    "score": float(similarity),
                    "content": metadata.get('content', ''),
                    "metadata": metadata
                })
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_k]
    
    def _mock_keyword_search(
        self,
        query: str,
        meeting_id: Optional[str],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Mock keyword search"""
        query_words = set(query.lower().split())
        
        # Count matches
        doc_scores = {}
        
        for word in query_words:
            if word in self.keyword_index:
                for doc_id in self.keyword_index[word]:
                    doc_scores[doc_id] = doc_scores.get(doc_id, 0) + 1
        
        # Get top docs
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        # Format results
        results = []
        for doc_id, count in sorted_docs:
            # Find in memory store
            for chunk_id, vector, metadata in self.memory_store:
                if chunk_id == doc_id:
                    if meeting_id and metadata.get('meeting_id') != meeting_id:
                        continue
                    
                    results.append({
                        "id": doc_id,
                        "score": count / len(query_words),  # Normalized
                        "content": metadata.get('content', ''),
                        "metadata": metadata
                    })
                    break
        
        return results
    
    def _mock_context_window(
        self,
        chunk_id: str,
        window_size: int
    ) -> List[Dict[str, Any]]:
        """Mock context window retrieval"""
        # Find chunk index
        target_idx = None
        for i, (cid, _, _) in enumerate(self.memory_store):
            if cid == chunk_id:
                target_idx = i
                break
        
        if target_idx is None:
            return []
        
        # Get surrounding chunks
        start = max(0, target_idx - window_size)
        end = min(len(self.memory_store), target_idx + window_size + 1)
        
        results = []
        for i in range(start, end):
            chunk_id, vector, metadata = self.memory_store[i]
            results.append({
                "id": chunk_id,
                "content": metadata.get('content', ''),
                "metadata": metadata,
                "is_target": i == target_idx
            })
        
        return results
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between vectors"""
        if isinstance(b, list):
            b = np.array(b)
        
        # Handle zero vectors
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
