"""
Pipeline Orchestrator — Wires all agents into the complete production loop.

DISCOVER → ANALYZE → SCRIPT → VOICE → ANIMATE → COMPOSE → DISTRIBUTE → MONITOR → OPTIMIZE

Each stage:
1. Activates required tools via ToolManager
2. Runs the agent
3. Deactivates tools
4. Verifies output before proceeding
"""
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("contentops.pipeline")


@dataclass
class PipelineResult:
    pipeline_id: str
    tenant: str
    platform: str
    stages_completed: list[str] = field(default_factory=list)
    stages_failed: list[str] = field(default_factory=list)
    script_id: Optional[str] = None
    script_score: Optional[float] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    post_results: list[dict] = field(default_factory=list)
    total_api_cost: float = 0.0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    status: str = "running"  # running | completed | failed | partial

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "tenant": self.tenant,
            "platform": self.platform,
            "stages_completed": self.stages_completed,
            "stages_failed": self.stages_failed,
            "script_id": self.script_id,
            "script_score": self.script_score,
            "audio_path": self.audio_path,
            "video_path": self.video_path,
            "post_results": self.post_results,
            "total_api_cost": self.total_api_cost,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
        }


class ContentOpsPipeline:
    """Master pipeline orchestrator."""

    def __init__(self):
        from src.agents.tool_manager import tool_manager
        self.tool_manager = tool_manager

    async def run_full(self, source_material: str, platform: str = "tiktok",
                       tenant: str = "mas-ai", mode: str = "test",
                       skip_video: bool = False, skip_distribute: bool = False) -> PipelineResult:
        """
        Run the complete pipeline from source material to published post.

        Args:
            source_material: Topic or raw content to create video from
            platform: Target platform (tiktok, youtube_short, instagram_reel, etc.)
            tenant: Tenant ID
            mode: 'test' (Kokoro TTS) or 'production' (ElevenLabs)
            skip_video: Skip video composition (script + audio only)
            skip_distribute: Skip distribution (render only)
        """
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = PipelineResult(pipeline_id=pipeline_id, tenant=tenant, platform=platform)

        logger.info(f"[{pipeline_id}] Starting full pipeline: {platform} / {tenant} / {mode}")

        # Estimate cost
        stages = ["script", f"voice_{mode}"]
        if not skip_video:
            stages.append("compose")
        if not skip_distribute:
            stages.append("distribute")
        estimate = self.tool_manager.estimate_pipeline_cost(stages)
        logger.info(f"[{pipeline_id}] Estimated cost: {estimate['estimated_api_cost']}")

        try:
            # === STAGE 1: SCRIPT ===
            script = await self._stage_script(source_material, platform, tenant, result)
            if not script or script.production_status != "approved":
                result.status = "failed"
                result.stages_failed.append("script")
                result.completed_at = datetime.now().isoformat()
                self._save_result(result)
                return result

            # === STAGE 2: VOICE ===
            audio_path = await self._stage_voice(script, mode, result)
            if not audio_path:
                result.status = "partial"
                result.stages_failed.append("voice")
                result.completed_at = datetime.now().isoformat()
                self._save_result(result)
                return result

            # === STAGE 3: VIDEO (optional) ===
            video_path = None
            if not skip_video:
                video_path = await self._stage_compose(script, audio_path, platform, tenant, result)
                if not video_path:
                    result.stages_failed.append("compose")
                    # Continue without video — script + audio is still valuable

            # === STAGE 4: DISTRIBUTE (optional) ===
            if not skip_distribute and (video_path or audio_path):
                await self._stage_distribute(script, video_path or audio_path, platform, tenant, result)

            # === STAGE 5: RECORD FOR ANALYTICS ===
            await self._stage_record(script, result)

            result.status = "completed" if not result.stages_failed else "partial"
            result.completed_at = datetime.now().isoformat()
            result.total_api_cost = self.tool_manager._total_api_cost

        except Exception as e:
            logger.error(f"[{pipeline_id}] Pipeline error: {e}")
            result.status = "failed"
            result.completed_at = datetime.now().isoformat()
        finally:
            self.tool_manager.deactivate_all()

        self._save_result(result)
        logger.info(f"[{pipeline_id}] Pipeline {result.status}. Stages: {result.stages_completed}")
        return result

    async def _stage_script(self, source_material, platform, tenant, result):
        """Stage 1: Generate script."""
        logger.info("=== STAGE 1: SCRIPT ===")
        self.tool_manager.activate(self.tool_manager.for_stage("script"))

        try:
            from src.agents.script_maestro import ScriptMaestro
            sm = ScriptMaestro()
            script = await sm.create_script(source_material, platform, tenant)

            result.script_id = script.script_id
            result.script_score = script.quality_score

            if script.production_status == "approved":
                sm.save_script(script)
                result.stages_completed.append("script")
                logger.info(f"Script approved: {script.script_id} (score: {script.quality_score})")
            else:
                logger.warning(f"Script {script.production_status}: score {script.quality_score}")

            return script
        except Exception as e:
            logger.error(f"Script stage failed: {e}")
            return None
        finally:
            self.tool_manager.deactivate_all()

    async def _stage_voice(self, script, mode, result):
        """Stage 2: Generate voice."""
        logger.info("=== STAGE 2: VOICE ===")
        voice_stage = f"voice_{mode}"
        self.tool_manager.activate(self.tool_manager.for_stage(voice_stage))

        try:
            from src.agents.avatar_engine import AvatarEngine
            ae = AvatarEngine()
            audio_path = await ae.generate_voice(script.full_voiceover_text, script.script_id, mode)

            if audio_path and Path(audio_path).exists():
                result.audio_path = audio_path
                result.stages_completed.append("voice")
                logger.info(f"Audio generated: {audio_path}")
                return audio_path
            return None
        except Exception as e:
            logger.error(f"Voice stage failed: {e}")
            return None
        finally:
            self.tool_manager.deactivate_all()

    async def _stage_compose(self, script, audio_path, platform, tenant, result):
        """Stage 3: Compose video."""
        logger.info("=== STAGE 3: COMPOSE ===")
        self.tool_manager.activate(self.tool_manager.for_stage("compose"))

        try:
            from src.agents.video_composer import VideoComposer
            vc = VideoComposer()
            video_path = await vc.compose(script.to_dict(), audio_path, platform, tenant=tenant)

            if video_path and Path(video_path).exists():
                result.video_path = video_path
                result.stages_completed.append("compose")
                logger.info(f"Video composed: {video_path}")
                return video_path
            return None
        except Exception as e:
            logger.error(f"Compose stage failed: {e}")
            return None
        finally:
            self.tool_manager.deactivate_all()

    async def _stage_distribute(self, script, media_path, platform, tenant, result):
        """Stage 4: Distribute to platforms."""
        logger.info("=== STAGE 4: DISTRIBUTE ===")
        self.tool_manager.activate(self.tool_manager.for_stage("distribute"))

        try:
            from src.agents.distributor import DistributionEngine
            de = DistributionEngine()
            post = de.format_post(script.to_dict(), media_path, platform, tenant)
            post_result = await de.publish(post)

            result.post_results.append({
                "platform": post_result.platform,
                "status": post_result.status,
                "post_id": post_result.post_id,
            })
            result.stages_completed.append("distribute")
        except Exception as e:
            logger.error(f"Distribute stage failed: {e}")
        finally:
            self.tool_manager.deactivate_all()

    async def _stage_record(self, script, result):
        """Stage 5: Record in analytics DB."""
        try:
            from src.agents.analytics_hawk import AnalyticsHawk
            hawk = AnalyticsHawk()
            hawk.record_post(
                post_id=result.pipeline_id,
                tenant=result.tenant,
                platform=result.platform,
                script_id=script.script_id,
                method_tag=script.method_tag,
                hook_type=script.hook_type,
            )
            result.stages_completed.append("record")
        except Exception as e:
            logger.warning(f"Analytics recording failed (non-critical): {e}")

    def _save_result(self, result: PipelineResult):
        """Save pipeline result to disk."""
        output_dir = Path("data/outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path = output_dir / f"{result.pipeline_id}.json"
        with open(result_path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)

    async def run_batch(self, topics: list[str], platform: str = "tiktok",
                        tenant: str = "mas-ai", mode: str = "test") -> list[PipelineResult]:
        """Run pipeline for multiple topics sequentially."""
        results = []
        for i, topic in enumerate(topics):
            logger.info(f"Batch [{i+1}/{len(topics)}]: {topic[:50]}...")
            result = await self.run_full(topic, platform, tenant, mode)
            results.append(result)
        return results


# Convenience function
async def run_pipeline(source: str, platform: str = "tiktok", tenant: str = "mas-ai",
                       mode: str = "test", skip_video: bool = False) -> PipelineResult:
    """Quick pipeline runner."""
    pipeline = ContentOpsPipeline()
    return await pipeline.run_full(source, platform, tenant, mode, skip_video=skip_video)


if __name__ == "__main__":
    import sys

    async def main():
        topic = sys.argv[1] if len(sys.argv) > 1 else "AI agents are replacing entire dev teams in 2026"
        platform = sys.argv[2] if len(sys.argv) > 2 else "tiktok"

        result = await run_pipeline(topic, platform, skip_video=True)
        print(json.dumps(result.to_dict(), indent=2))

    asyncio.run(main())
