"""
Quick test script for embedding service
Run: python scripts/test_embedding.py
"""

import sys
sys.path.append('./backend')

from services.embedding_service import NovaEmbeddingService

def test_embedding():
    print("=" * 60)
    print("Testing Nova Embedding Service")
    print("=" * 60)
    
    service = NovaEmbeddingService()
    
    # Test case 1: Transcript chunk
    print("\n📝 Test 1: Embedding transcript chunk...")
    
    chunk = service.embed_transcript_chunk(
        text="Sarah: We need to deploy the authentication service by Friday using Auth0.",
        timestamp=34.5,
        speaker="Sarah",
        meeting_id="test-meeting-001"
    )
    
    print(f"✓ Chunk ID: {chunk.chunk_id}")
    print(f"✓ Topic: {chunk.topic_cluster}")
    print(f"✓ Embedding dimensions: {len(chunk.embedding)}")
    print(f"✓ Speaker: {chunk.participant}")
    print(f"✓ Timestamp: {chunk.timestamp}s")
    
    # Verify embedding is not all zeros
    if sum(chunk.embedding) == 0:
        print("⚠️  WARNING: Embedding is all zeros (likely using fallback mode)")
        print("   This means AWS Bedrock is not configured or failed.")
    else:
        print(f"✓ Embedding has values (first 5: {chunk.embedding[:5]})")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_embedding()
