"""
Nova Multimodal Embedding Service
Handles embedding of audio transcripts, slides, and whiteboard images
"""

from typing import List, Dict, Optional
import boto3
import json
import hashlib
import base64
from dataclasses import dataclass, asdict
import os


@dataclass
class EmbeddingChunk:
    """Represents a single embedded chunk of meeting content"""
    chunk_id: str
    meeting_id: str
    source_type: str  # 'transcript' | 'slide' | 'whiteboard' | 'screenshot'
    content: str  # Text or image description
    content_hash: str
    timestamp: float  # For audio chunks (-1 for non-temporal content)
    page_number: int  # For slides (-1 for non-paged content)
    participant: str  # Speaker name (empty if not applicable)
    topic_cluster: str  # Auto-detected topic
    embedding: List[float]  # Nova multimodal embedding (1024-dim)
    metadata: Dict

    def to_dict(self):
        """Convert to dictionary for storage"""
        return asdict(self)


class NovaEmbeddingService:
    """Service for creating multimodal embeddings using Amazon Nova"""
    
    def __init__(self):
        self.bedrock = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.model_id = os.getenv('NOVA_EMBED_MODEL_ID', 'amazon.nova-embed-multimodal-v1')
        print(f"✓ NovaEmbeddingService initialized with model: {self.model_id}")
        
    def embed_transcript_chunk(
        self, 
        text: str, 
        timestamp: float,
        speaker: str,
        meeting_id: str
    ) -> EmbeddingChunk:
        """
        Embed transcript chunk with timestamp preservation
        
        Args:
            text: Transcript text (30-60 second chunk)
            timestamp: Start time in seconds
            speaker: Speaker name
            meeting_id: Unique meeting identifier
            
        Returns:
            EmbeddingChunk with populated embedding
        """
        
        # Invoke Nova multimodal embedding (text mode)
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputText": text,
                    "embeddingConfig": {
                        "outputEmbeddingLength": 1024
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            embedding = result['embedding']
            
        except Exception as e:
            print(f"✗ Embedding failed: {e}")
            # Return zero vector as fallback
            embedding = [0.0] * 1024
        
        # Auto-detect topic (placeholder - will implement with Nova Lite later)
        topic = self._detect_topic_simple(text)
        
        return EmbeddingChunk(
            chunk_id=self._generate_id(meeting_id, timestamp),
            meeting_id=meeting_id,
            source_type='transcript',
            content=text,
            content_hash=hashlib.sha256(text.encode()).hexdigest(),
            timestamp=timestamp,
            page_number=-1,
            participant=speaker,
            topic_cluster=topic,
            embedding=embedding,
            metadata={
                'duration_sec': 30,  # Fixed chunk size for now
                'word_count': len(text.split())
            }
        )
    
    def embed_slide_image(
        self,
        image_bytes: bytes,
        page_number: int,
        meeting_id: str
    ) -> EmbeddingChunk:
        """
        Embed slide image using multimodal Nova
        
        Args:
            image_bytes: Raw image bytes (PNG, JPEG)
            page_number: Slide page number
            meeting_id: Meeting identifier
            
        Returns:
            EmbeddingChunk with image embedding
        """
        
        # Convert image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # TODO: Extract text from slide using OCR (placeholder for now)
        slide_text = f"Slide {page_number} content"
        
        try:
            # Nova multimodal embedding (image + text mode)
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputImage": image_b64,
                    "inputText": slide_text,
                    "embeddingConfig": {
                        "outputEmbeddingLength": 1024
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            embedding = result['embedding']
            
        except Exception as e:
            print(f"✗ Image embedding failed: {e}")
            embedding = [0.0] * 1024
        
        return EmbeddingChunk(
            chunk_id=self._generate_id(meeting_id, f"slide_{page_number}"),
            meeting_id=meeting_id,
            source_type='slide',
            content=slide_text,
            content_hash=hashlib.sha256(image_bytes).hexdigest(),
            timestamp=-1,
            page_number=page_number,
            participant='',
            topic_cluster=self._detect_topic_simple(slide_text),
            embedding=embedding,
            metadata={
                'image_size': len(image_bytes),
                'format': 'image/png'  # TODO: Auto-detect
            }
        )
    
    def embed_whiteboard(
        self,
        image_bytes: bytes,
        timestamp: float,
        meeting_id: str
    ) -> EmbeddingChunk:
        """
        Embed whiteboard/screenshot with visual understanding
        
        Args:
            image_bytes: Raw image bytes
            timestamp: When screenshot was taken
            meeting_id: Meeting identifier
            
        Returns:
            EmbeddingChunk with visual embedding
        """
        
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # TODO: Use Nova to describe the image (placeholder for now)
        description = f"Whiteboard at {timestamp}s"
        
        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "inputImage": image_b64,
                    "inputText": description,
                    "embeddingConfig": {
                        "outputEmbeddingLength": 1024
                    }
                })
            )
            
            result = json.loads(response['body'].read())
            embedding = result['embedding']
            
        except Exception as e:
            print(f"✗ Whiteboard embedding failed: {e}")
            embedding = [0.0] * 1024
        
        return EmbeddingChunk(
            chunk_id=self._generate_id(meeting_id, f"visual_{timestamp}"),
            meeting_id=meeting_id,
            source_type='whiteboard',
            content=description,
            content_hash=hashlib.sha256(image_bytes).hexdigest(),
            timestamp=timestamp,
            page_number=-1,
            participant='',
            topic_cluster=self._detect_topic_simple(description),
            embedding=embedding,
            metadata={
                'visual_elements': ['diagram', 'handwriting']  # Placeholder
            }
        )
    
    def _generate_id(self, meeting_id: str, suffix: any) -> str:
        """Generate unique chunk ID"""
        return f"{meeting_id}_{suffix}".replace('.', '_')
    
    def _detect_topic_simple(self, text: str) -> str:
        """
        Simple keyword-based topic detection
        TODO: Replace with Nova Lite-based classification
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['decision', 'approve', 'agree']):
            return 'decision'
        elif any(word in text_lower for word in ['task', 'action', 'implement', 'deploy']):
            return 'action'
        elif any(word in text_lower for word in ['risk', 'blocker', 'concern', 'issue']):
            return 'risk'
        elif any(word in text_lower for word in ['api', 'code', 'service', 'database']):
            return 'technical'
        else:
            return 'general'


# Test function
if __name__ == "__main__":
    print("Testing NovaEmbeddingService...")
    
    service = NovaEmbeddingService()
    
    # Test transcript embedding
    chunk = service.embed_transcript_chunk(
        text="We need to deploy the authentication service by Friday.",
        timestamp=34.5,
        speaker="Sarah",
        meeting_id="test-001"
    )
    
    print(f"✓ Created chunk: {chunk.chunk_id}")
    print(f"  Topic: {chunk.topic_cluster}")
    print(f"  Embedding dimensions: {len(chunk.embedding)}")
    print(f"  Content hash: {chunk.content_hash[:16]}...")
