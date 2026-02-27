import json
import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
from app.core.config import settings
from app.models.prompt_intelligence import (
    PromptBundle, ScriptPrompt, Storyboard, StoryboardScene, 
    VisualPrompts, VoiceSpec, EditRecipe
)
from app.models.niche import Niche

class PromptIntelligenceService:
    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"

    async def _call_llm(self, model: str, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        """Generic LLM caller."""
        full_prompt = prompt
        if system:
            full_prompt = f"System: {system}\n\nUser: {prompt}"
            
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                payload = {
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7
                    }
                }
                if json_mode:
                    payload["format"] = "json"
                
                response = await client.post(self.ollama_url, json=payload)
                response.raise_for_status()
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"LLM call failed ({model}): {e}")
            raise

    async def build_bundle(self, job_id: int, niche: Niche, topic: str, pattern: Optional[Dict] = None) -> PromptBundle:
        """
        Generate all prompt artifacts for a job.
        Uses specific models as requested:
        - DeepSeek-R1 = reasoning (script structure)
        - Qwen2.5 = JSON formatting (storyboard, specs)
        - Llama3.1 = copy/captions
        """
        
        # 1. Reasoning (DeepSeek-R1) - Plan the video
        reasoning_prompt = f"""
        Analyze this topic for a viral short-form video: "{topic}"
        Niche: {niche.name}
        Target Audience: {niche.description}
        
        Determine the best angle, hook, and structure.
        Output a plan with:
        - Hook concept
        - Key points
        - Visual style
        - Tone
        """
        plan = await self._call_llm(settings.ollama_reasoning_model, reasoning_prompt)
        
        # 2. Script Prompt (Qwen2.5) - structured for the script generator
        script_prompt_json = await self._call_llm(
            settings.ollama_fast_model,
            f"Convert this plan into a JSON object for a script writer.\nPlan: {plan}",
            system="You are a JSON converter. Output valid JSON only.",
            json_mode=True
        )
        
        # 3. Storyboard (Qwen2.5)
        storyboard_prompt = f"""
        Create a scene-by-scene storyboard for this video plan.
        Plan: {plan}
        
        Output JSON with list of scenes: {{ "scenes": [ {{ "scene_number": 1, "description": "...", "duration": 3, "visual_prompt": "...", "audio_cue": "..." }} ], "total_duration": 60 }}
        """
        storyboard_json = await self._call_llm(
            settings.ollama_fast_model,
            storyboard_prompt,
            system="You are a storyboard artist. Output valid JSON only.",
            json_mode=True
        )
        
        # 4. Voice Spec (Qwen2.5)
        voice_spec_json = await self._call_llm(
            settings.ollama_fast_model,
            f"Determine the best voice settings for this plan: {plan}\nOutput JSON: {{ 'provider': 'xtts', 'voice_id': '...', 'stability': 0.5, 'similarity_boost': 0.75, 'speed': 1.0, 'tone': '...' }}",
            system="Output valid JSON only.",
            json_mode=True
        )
        
        # 5. Edit Recipe (Qwen2.5)
        edit_recipe_json = await self._call_llm(
            settings.ollama_fast_model,
            f"Determine editing style for: {plan}\nOutput JSON: {{ 'captions_enabled': true, 'caption_style': 'karaoke', 'transition_style': 'zoom', 'bg_music_genre': 'lofi', 'beat_markers': [] }}",
            system="Output valid JSON only.",
            json_mode=True
        )
        
        # 6. Copy/Captions (Llama3.1)
        caption_text = await self._call_llm(
            settings.ollama_copy_model,
            f"Write a short, engaging social media caption for this video topic: {topic}. Include a question.",
            system="You are a social media manager."
        )
        
        # 7. Hashtags (Qwen2.5)
        hashtags_json = await self._call_llm(
            settings.ollama_fast_model,
            f"Generate 10 viral hashtags for: {topic} in niche {niche.name}. Output JSON list: ['tag1', 'tag2']",
            system="Output valid JSON only.",
            json_mode=True
        )
        
        # Create Bundle
        bundle = PromptBundle(
            job_id=job_id,
            script_prompt_json=script_prompt_json,
            storyboard_json=storyboard_json,
            visual_prompts_json=storyboard_json, # derived from storyboard
            voice_spec_json=voice_spec_json,
            edit_recipe_json=edit_recipe_json,
            hashtags_json=hashtags_json,
            caption_text=caption_text
        )
        
        # Save to DB (caller handles session)
        return bundle

prompt_intelligence_service = PromptIntelligenceService()
