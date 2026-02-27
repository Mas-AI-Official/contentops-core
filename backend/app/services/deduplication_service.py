import httpx
import numpy as np
from typing import List, Optional
from loguru import logger
from sqlmodel import select
from app.core.config import settings
from app.models.scraping import ViralDNA
from app.db.database import async_engine
from sqlalchemy.ext.asyncio import AsyncSession

class DeduplicationService:
    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/embeddings"
        self.model = settings.ollama_embedding_model

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for text using Ollama."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ollama_url,
                    json={"model": self.model, "prompt": text},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    async def check_similarity(self, text: str, threshold: float = 0.85) -> bool:
        """
        Check if text is similar to any existing ViralDNA content.
        Returns True if duplicate/similar found.
        """
        embedding = await self.generate_embedding(text)
        if not embedding:
            return False

        # Naive in-memory comparison (suitable for < 10k items)
        async with AsyncSession(async_engine) as session:
            statement = select(ViralDNA).where(ViralDNA.embedding.is_not(None))
            results = await session.execute(statement)
            existing_items = results.scalars().all()
            
            vec_a = np.array(embedding)
            norm_a = np.linalg.norm(vec_a)
            
            if norm_a == 0:
                return False

            for item in existing_items:
                if not item.embedding:
                    continue
                
                # Convert stored JSON list to numpy array
                vec_b = np.array(item.embedding)
                norm_b = np.linalg.norm(vec_b)
                
                if norm_b == 0:
                    continue
                    
                cosine_sim = np.dot(vec_a, vec_b) / (norm_a * norm_b)
                
                if cosine_sim > threshold:
                    logger.warning(f"Duplicate content detected! Similarity: {cosine_sim:.2f} with ViralDNA ID {item.id}")
                    return True
                    
        return False

deduplication_service = DeduplicationService()
