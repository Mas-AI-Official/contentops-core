"""
Script service - generates video scripts using Ollama LLM.
"""
import httpx
from typing import Optional
from loguru import logger
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class VideoScript:
    """Generated video script."""
    hook: str
    body: str
    cta: str
    full_script: str
    estimated_duration: int  # seconds


class ScriptService:
    """Service for generating video scripts."""
    
    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"
    
    async def generate_script(
        self,
        topic: str,
        prompt_hook: str,
        prompt_body: str,
        prompt_cta: str,
        target_duration: int = 60,
        style: str = "narrator_broll"
    ) -> VideoScript:
        """Generate a complete video script."""
        
        # Format prompts with topic
        hook_prompt = prompt_hook.format(topic=topic)
        body_prompt = prompt_body.format(topic=topic)
        cta_prompt = prompt_cta.format(topic=topic)
        
        # Generate each section
        hook = await self._generate_section(hook_prompt, "hook", 5)
        body = await self._generate_section(body_prompt, "body", target_duration - 15)
        cta = await self._generate_section(cta_prompt, "cta", 10)
        
        # Combine into full script
        full_script = f"{hook}\n\n{body}\n\n{cta}"
        
        # Estimate duration (roughly 150 words per minute for speech)
        word_count = len(full_script.split())
        estimated_duration = int((word_count / 150) * 60)
        
        return VideoScript(
            hook=hook,
            body=body,
            cta=cta,
            full_script=full_script,
            estimated_duration=estimated_duration
        )
    
    async def _generate_section(
        self, 
        prompt: str, 
        section_type: str,
        target_seconds: int
    ) -> str:
        """Generate a single section of the script."""
        
        # Calculate target word count
        target_words = int((target_seconds / 60) * 150)
        
        full_prompt = f"""{prompt}

Requirements:
- Write for spoken narration (conversational, natural flow)
- Target length: approximately {target_words} words ({target_seconds} seconds when spoken)
- No stage directions or brackets
- No emojis unless natural for the content
- Return ONLY the script text, nothing else

Script:"""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": settings.ollama_model,
                        "prompt": full_prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "").strip()
                
                # Clean up the response
                text = self._clean_script(text)
                
                logger.info(f"Generated {section_type}: {len(text)} chars, ~{len(text.split())} words")
                return text
                
        except Exception as e:
            logger.error(f"Failed to generate {section_type}: {e}")
            raise
    
    def _clean_script(self, text: str) -> str:
        """Clean up generated script text."""
        # Remove common prefixes
        prefixes = ["Script:", "Here's", "Sure,", "Here is"]
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
        
        # Remove quotes if the entire text is quoted
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        
        # Remove stage directions [like this]
        import re
        text = re.sub(r'\[.*?\]', '', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    async def improve_script(self, script: str, feedback: str) -> str:
        """Improve a script based on feedback."""
        prompt = f"""You are a video script editor.

Original script:
{script}

Feedback:
{feedback}

Rewrite the script incorporating the feedback. Keep the same structure (hook, body, CTA).
Return ONLY the improved script, nothing else.

Improved script:"""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                response.raise_for_status()
                data = response.json()
                return self._clean_script(data.get("response", "").strip())
                
        except Exception as e:
            logger.error(f"Failed to improve script: {e}")
            raise


script_service = ScriptService()
