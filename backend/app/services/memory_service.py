import httpx
import json
from typing import List, Dict, Any, Optional
from loguru import logger
from sqlmodel import Session, select
from sqlalchemy import func
from app.core.config import settings
from app.models.memory import MemoryIndex
from app.models.trends import PromptPack
import numpy as np
import hashlib

class MemoryService:
    def __init__(self):
        self.ollama_base_url = settings.ollama_base_url
        self.embedding_model = settings.ollama_embedding_model
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Ollama."""
        url = f"{self.ollama_base_url}/api/embeddings"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={
                        "model": self.embedding_model,
                        "prompt": text
                    }
                )
                if response.status_code == 404:
                    # Model not found, try pulling it? Or fallback?
                    logger.warning(f"Embedding model {self.embedding_model} not found.")
                    return []
                
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return []

    async def check_duplicate(self, session: Session, account_id: int, niche_id: int, text: str, threshold: float = 0.85) -> Dict[str, Any]:
        """Check for duplicates using embeddings."""
        embedding = await self.get_embedding(text)
        if not embedding:
            return {"is_duplicate": False, "reason": "embedding_failed"}
        
        # Fetch recent memories for this niche/account
        statement = select(MemoryIndex).where(
            MemoryIndex.account_id == account_id,
            MemoryIndex.niche_id == niche_id
        ).order_by(MemoryIndex.created_at.desc()).limit(100)
        
        memories = session.exec(statement).all()
        
        vec_a = np.array(embedding)
        norm_a = np.linalg.norm(vec_a)
        
        for mem in memories:
            if not mem.embedding:
                continue
            
            vec_b = np.array(mem.embedding)
            norm_b = np.linalg.norm(vec_b)
            
            if norm_a == 0 or norm_b == 0:
                continue
                
            similarity = np.dot(vec_a, vec_b) / (norm_a * norm_b)
            
            if similarity > threshold:
                return {
                    "is_duplicate": True,
                    "similarity": float(similarity),
                    "similar_to_id": mem.promptpack_id,
                    "reason": "semantic_similarity"
                }
                
        return {"is_duplicate": False}

    async def save_memory(self, session: Session, account_id: int, niche_id: int, promptpack_id: int, text: str):
        """Save prompt pack to memory."""
        embedding = await self.get_embedding(text)
        if not embedding:
            return
            
        memory = MemoryIndex(
            account_id=account_id,
            niche_id=niche_id,
            promptpack_id=promptpack_id,
            embedding=embedding,
            fingerprint=self._compute_fingerprint(text)
        )
        session.add(memory)
        await session.commit()
        
    def _compute_fingerprint(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

memory_service = MemoryService()
