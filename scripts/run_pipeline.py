"""Run a full ContentOps pipeline from command line."""
import sys
import os
import asyncio
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    parser = argparse.ArgumentParser(description="ContentOps Pipeline Runner")
    parser.add_argument("topic", help="Topic or source material for content")
    parser.add_argument("--platform", default="tiktok", choices=["tiktok", "youtube_short", "instagram_reel", "linkedin", "twitter"])
    parser.add_argument("--tenant", default="mas-ai")
    parser.add_argument("--mode", default="test", choices=["test", "production"])
    args = parser.parse_args()

    from src.agents.tool_manager import tool_manager
    from src.agents.script_maestro import ScriptMaestro
    from src.agents.avatar_engine import AvatarEngine

    print("=" * 60)
    print("ContentOps Pipeline Runner")
    print("=" * 60)

    # Estimate cost
    stages = ["script", f"voice_{args.mode}"]
    estimate = tool_manager.estimate_pipeline_cost(stages)
    print(f"\nEstimated cost: {estimate['estimated_api_cost']}")
    print(f"Estimated time: {estimate['estimated_time_min']} min\n")

    # Stage 1: Script
    print("[1/2] Generating script...")
    tool_manager.activate(tool_manager.for_stage("script"))
    sm = ScriptMaestro()
    script = await sm.create_script(args.topic, args.platform, args.tenant)
    tool_manager.deactivate_all()

    if script.production_status != "approved":
        print(f"\nScript {script.production_status}. Score: {script.quality_score}")
        print("Escalate to operator for manual review.")
        return

    script_path = sm.save_script(script)
    print(f"Script approved! Score: {script.quality_score}")
    print(f"   Saved: {script_path}")
    print(f"   Hook type: {script.hook_type}")
    print(f"   Duration: {script.estimated_duration}")
    print(f"   Words: {script.word_count}")

    # Stage 2: Voice
    print(f"\n[2/2] Generating voice ({args.mode} mode)...")
    voice_stage = f"voice_{args.mode}"
    tool_manager.activate(tool_manager.for_stage(voice_stage))
    ae = AvatarEngine()
    audio_path = await ae.generate_voice(script.full_voiceover_text, script.script_id, args.mode)
    tool_manager.deactivate_all()

    print(f"Audio generated: {audio_path}")

    # Summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Script: {script_path}")
    print(f"Audio:  {audio_path}")
    print(f"Cost:   {estimate['estimated_api_cost']}")
    print(f"\nTool status: {json.dumps(tool_manager.status(), indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
