"""
Script service - generates video scripts using Ollama LLM.
Supports per-niche model configuration.
"""
import httpx
from typing import Optional
from loguru import logger
from dataclasses import dataclass

from app.core.config import settings
from app.services.mcp_service import mcp_service


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
        style: str = "narrator_broll",
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> VideoScript:
        """
        Generate a complete video script.
        
        Args:
            topic: The topic to generate content about
            prompt_hook: Template for the hook section
            prompt_body: Template for the body section
            prompt_cta: Template for the CTA section
            target_duration: Target video duration in seconds
            style: Video style (narrator_broll, stick_caption, etc.)
            model: Ollama model to use (defaults to global setting)
            temperature: LLM temperature (0.0-2.0)
        """
        # Use provided model or fall back to global default
        llm_model = model or settings.ollama_model
        
        # Format prompts with topic
        hook_prompt = prompt_hook.format(topic=topic)
        body_prompt = prompt_body.format(topic=topic)
        cta_prompt = prompt_cta.format(topic=topic)
        
        # Generate each section
        hook = await self._generate_section(hook_prompt, "hook", 5, llm_model, temperature)
        body = await self._generate_section(body_prompt, "body", target_duration - 15, llm_model, temperature)
        cta = await self._generate_section(cta_prompt, "cta", 10, llm_model, temperature)
        
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
        target_seconds: int,
        model: str,
        temperature: float = 0.7
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
            if settings.llm_provider == "hf_router":
                text = await self._generate_section_via_hf_router(
                    prompt=full_prompt,
                    model=model,
                    temperature=temperature
                )
            elif settings.llm_provider == "mcp" and settings.mcp_enabled and settings.mcp_llm_connector:
                text = await self._generate_section_via_mcp(
                    prompt=full_prompt,
                    model=model,
                    temperature=temperature
                )
            else:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        self.ollama_url,
                        json={
                            "model": model,
                            "prompt": full_prompt,
                            "stream": False,
                            "options": {
                                "temperature": temperature
                            }
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    text = data.get("response", "").strip()

            # Clean up the response
            text = self._clean_script(text)

            logger.info(f"Generated {section_type} using {settings.llm_provider}: {len(text)} chars, ~{len(text.split())} words")
            return text

        except Exception as e:
            logger.error(f"Failed to generate {section_type} with {settings.llm_provider}: {e}")
            raise

    async def _generate_section_via_mcp(self, prompt: str, model: str, temperature: float) -> str:
        """Generate a section using MCP (OpenAI-compatible)."""
        mcp_model = settings.mcp_llm_model or model
        payload = {
            "model": mcp_model,
            "messages": [
                {"role": "system", "content": "You are a concise video script writer."},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        result = await mcp_service.forward_request(
            connector_name=settings.mcp_llm_connector,
            method="POST",
            path=settings.mcp_llm_path,
            json_body=payload
        )
        if result.get("error"):
            raise RuntimeError(result)

        data = result.get("data", {})
        try:
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return str(data).strip()
    
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
    
    async def improve_script(
        self, 
        script: str, 
        feedback: str,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Improve a script based on feedback."""
        # Use appropriate model based on provider
        if settings.llm_provider == "hf_router":
            llm_model = model or settings.hf_router_model
        elif settings.llm_provider == "mcp":
            llm_model = model or settings.mcp_llm_model
        else:
            llm_model = model or settings.ollama_model
        
        prompt = f"""You are a video script editor.

Original script:
{script}

Feedback:
{feedback}

Rewrite the script incorporating the feedback. Keep the same structure (hook, body, CTA).
Return ONLY the improved script, nothing else.

Improved script:"""
        
        try:
            if settings.llm_provider == "hf_router":
                text = await self._generate_section_via_hf_router(prompt, llm_model, temperature)
                return self._clean_script(text)
            elif settings.llm_provider == "mcp" and settings.mcp_enabled and settings.mcp_llm_connector:
                text = await self._generate_section_via_mcp(prompt, llm_model, temperature)
                return self._clean_script(text)

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                return self._clean_script(data.get("response", "").strip())

        except Exception as e:
            logger.error(f"Failed to improve script with {llm_model}: {e}")
            raise
    
    async def generate_with_niche_config(
        self,
        topic: str,
        niche,
        target_duration: Optional[int] = None
    ) -> VideoScript:
        """
        Generate a script using niche-specific configuration.
        
        Args:
            topic: The topic to generate content about
            niche: Niche object with configuration
            target_duration: Override for target duration
        """
        from app.models.niche import NicheModelConfig
        
        config = NicheModelConfig.from_niche(niche, settings)
        
        duration = target_duration or niche.max_duration_seconds
        
        return await self.generate_script(
            topic=topic,
            prompt_hook=niche.prompt_hook,
            prompt_body=niche.prompt_body,
            prompt_cta=niche.prompt_cta,
            target_duration=duration,
            style=niche.style,
            model=config.llm_model,
            temperature=config.llm_temperature
        )


script_service = ScriptService()
