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
    parser.add_argument("--platform", default="tiktok",
                        choices=["tiktok", "youtube_short", "instagram_reel", "linkedin", "twitter"])
    parser.add_argument("--tenant", default="mas-ai")
    parser.add_argument("--mode", default="test", choices=["test", "production"])
    parser.add_argument("--skip-video", action="store_true", help="Skip video composition")
    parser.add_argument("--skip-distribute", action="store_true", help="Skip distribution")
    parser.add_argument("--batch", nargs="+", help="Multiple topics for batch processing")
    args = parser.parse_args()

    from src.agents.pipeline import ContentOpsPipeline

    pipeline = ContentOpsPipeline()

    print("=" * 60)
    print("ContentOps Pipeline Runner v2")
    print("=" * 60)

    if args.batch:
        print(f"Batch mode: {len(args.batch)} topics")
        results = await pipeline.run_batch(args.batch, args.platform, args.tenant, args.mode)
        for r in results:
            status_icon = "OK" if r.status == "completed" else "PARTIAL" if r.status == "partial" else "FAIL"
            print(f"  [{status_icon}] {r.script_id}: score={r.script_score}")
    else:
        print(f"Topic: {args.topic[:80]}")
        print(f"Platform: {args.platform} | Tenant: {args.tenant} | Mode: {args.mode}")
        print(f"Video: {'skip' if args.skip_video else 'yes'} | Distribute: {'skip' if args.skip_distribute else 'yes'}")
        print()

        result = await pipeline.run_full(
            args.topic, args.platform, args.tenant, args.mode,
            skip_video=args.skip_video, skip_distribute=args.skip_distribute
        )

        print()
        print("=" * 60)
        print(f"RESULT: {result.status.upper()}")
        print("=" * 60)
        print(f"Pipeline ID: {result.pipeline_id}")
        print(f"Stages completed: {', '.join(result.stages_completed)}")
        if result.stages_failed:
            print(f"Stages failed: {', '.join(result.stages_failed)}")
        print(f"Script: {result.script_id} (score: {result.script_score})")
        if result.audio_path:
            print(f"Audio: {result.audio_path}")
        if result.video_path:
            print(f"Video: {result.video_path}")
        if result.post_results:
            for pr in result.post_results:
                print(f"Post [{pr['platform']}]: {pr['status']}")
        print(f"API cost: ${result.total_api_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
