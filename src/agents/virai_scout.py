"""
VirAI Scout — Intelligence Gathering & Viral Pattern Analysis.

Scrapes top influencers, downloads/transcribes their viral videos,
reverse-engineers what made them viral, and stores patterns in Hook Vault.

Also scans trending topics from free sources (RSS feeds, no API keys needed).
"""
import json
import asyncio
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("contentops.virai_scout")


@dataclass
class TrendItem:
    title: str
    source: str
    url: str
    category: str
    relevance_score: float = 0.0
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class VideoAnalysis:
    video_url: str
    influencer: str
    platform: str
    hook_text: str
    hook_type: str
    script_structure: str
    emotional_triggers: list[str]
    viral_score: float
    transcript: str
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())


class VirAIScout:
    """Scrapes and analyzes viral content. Feeds Hook Vault."""

    # Free RSS/API sources for trend scanning (no API keys needed)
    TREND_SOURCES = {
        "hackernews": "https://hnrss.org/newest?q=AI+artificial+intelligence&count=20",
        "reddit_ai": "https://www.reddit.com/r/artificial/.rss?limit=20",
        "reddit_llm": "https://www.reddit.com/r/LocalLLaMA/.rss?limit=20",
        "arxiv_ai": "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=10",
        "google_news_ai": "https://news.google.com/rss/search?q=artificial+intelligence+startup&hl=en-US",
        "google_news_claude": "https://news.google.com/rss/search?q=Claude+AI+Anthropic&hl=en-US",
    }

    def __init__(self, ollama_host: str = "http://localhost:11434", ollama_model: str = "gemma3:4b"):
        self.ollama_host = ollama_host
        self.ollama_model = ollama_model
        self.data_dir = Path("data")
        self.scraped_dir = self.data_dir / "scraped"
        self.transcripts_dir = self.data_dir / "transcripts"
        self.scraped_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)

    async def scan_trends(self, sources: list[str] = None) -> list[TrendItem]:
        """Scan free RSS/API sources for trending AI topics."""
        if sources is None:
            sources = list(self.TREND_SOURCES.keys())

        all_trends = []
        for source_name in sources:
            url = self.TREND_SOURCES.get(source_name)
            if not url:
                continue
            try:
                trends = await self._fetch_rss(url, source_name)
                all_trends.extend(trends)
                logger.info(f"Scanned {source_name}: {len(trends)} items")
            except Exception as e:
                logger.warning(f"Failed to scan {source_name}: {e}")

        # Deduplicate by title similarity
        seen_titles = set()
        unique = []
        for t in all_trends:
            title_key = t.title.lower()[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(t)

        # Score relevance using Ollama
        if unique:
            unique = await self._score_relevance(unique)

        # Save to cache
        cache_path = Path("src/intelligence/trend_cache.json")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump({
                "scanned_at": datetime.now().isoformat(),
                "source_count": len(sources),
                "trends": [{"title": t.title, "source": t.source, "url": t.url, "category": t.category, "relevance_score": t.relevance_score} for t in unique[:50]]
            }, f, indent=2)

        logger.info(f"Total unique trends: {len(unique)}")
        return sorted(unique, key=lambda t: t.relevance_score, reverse=True)

    async def _fetch_rss(self, url: str, source_name: str) -> list[TrendItem]:
        """Fetch and parse RSS feed."""
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            headers = {"User-Agent": "ContentOps/1.0 (AI Media Agency)"}
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            content = response.text

        # Simple XML parsing for RSS items
        items = []
        import re

        if "arxiv" in source_name:
            # ArXiv Atom format
            entries = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)
            for entry in entries[:10]:
                title = re.search(r'<title[^>]*>(.*?)</title>', entry, re.DOTALL)
                link = re.search(r'<id>(.*?)</id>', entry)
                if title:
                    items.append(TrendItem(
                        title=title.group(1).strip().replace('\n', ' '),
                        source=source_name,
                        url=link.group(1) if link else "",
                        category="research"
                    ))
        else:
            # Standard RSS format
            rss_items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
            if not rss_items:
                rss_items = re.findall(r'<entry>(.*?)</entry>', content, re.DOTALL)

            for item in rss_items[:15]:
                title = re.search(r'<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item, re.DOTALL)
                link = re.search(r'<link[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>', item)
                if not link:
                    link = re.search(r'<link[^>]*href="([^"]*)"', item)

                if title:
                    items.append(TrendItem(
                        title=title.group(1).strip(),
                        source=source_name,
                        url=link.group(1).strip() if link else "",
                        category="news" if "news" in source_name else "community"
                    ))

        return items

    async def _score_relevance(self, trends: list[TrendItem]) -> list[TrendItem]:
        """Score trend relevance for AI/tech content creation using Ollama."""
        titles = "\n".join([f"- {t.title}" for t in trends[:30]])
        prompt = f"""Rate each topic's potential as a viral AI/tech social media video (1-10).
Consider: Is it surprising? Will AI builders care? Can it be explained in 60 seconds?

Topics:
{titles}

Output ONLY a JSON array of scores in order, e.g. [8, 5, 9, ...]"""

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={"model": self.ollama_model, "prompt": prompt, "stream": False, "options": {"temperature": 0.3}},
                )
                result = response.json().get("response", "")

                start = result.find("[")
                end = result.rfind("]") + 1
                if start >= 0 and end > start:
                    scores = json.loads(result[start:end])
                    for i, score in enumerate(scores):
                        if i < len(trends):
                            trends[i].relevance_score = float(score)
        except Exception as e:
            logger.warning(f"Relevance scoring failed: {e}")
            for t in trends:
                t.relevance_score = 5.0

        return trends

    async def fetch_video_metadata(self, url: str) -> dict:
        """Get video metadata using yt-dlp without downloading."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-download", url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"yt-dlp metadata failed: {e}")
        return {}

    async def download_and_transcribe(self, url: str, niche: str = "ai-tech") -> Optional[str]:
        """Download video audio and transcribe with faster-whisper."""
        output_dir = self.scraped_dir / niche
        output_dir.mkdir(parents=True, exist_ok=True)

        audio_path = output_dir / f"temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

        # Download audio only
        try:
            subprocess.run([
                "yt-dlp", "-x", "--audio-format", "wav",
                "--audio-quality", "0",
                "-o", str(audio_path),
                "--no-playlist",
                url
            ], capture_output=True, timeout=120)
        except Exception as e:
            logger.error(f"yt-dlp download failed: {e}")
            return None

        if not audio_path.exists():
            # yt-dlp may add extension
            for f in output_dir.glob("temp_audio_*.wav"):
                audio_path = f
                break

        if not audio_path.exists():
            return None

        # Transcribe
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(str(audio_path), word_timestamps=True)
            transcript = " ".join([seg.text for seg in segments])

            # Save transcript
            transcript_path = self.transcripts_dir / f"{audio_path.stem}.json"
            with open(transcript_path, "w") as f:
                json.dump({"url": url, "transcript": transcript, "language": info.language}, f, indent=2)

            # Cleanup audio
            audio_path.unlink(missing_ok=True)

            return transcript
        except ImportError:
            logger.warning("faster-whisper not installed. pip install faster-whisper")
            return None
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    async def analyze_viral_patterns(self, transcript: str, metadata: dict = None) -> Optional[dict]:
        """Analyze a video transcript for viral patterns using Ollama."""
        views = metadata.get("view_count", "unknown") if metadata else "unknown"
        title = metadata.get("title", "unknown") if metadata else "unknown"

        prompt = f"""Analyze this viral video transcript and extract patterns.

VIDEO: {title}
VIEWS: {views}

TRANSCRIPT:
{transcript[:2000]}

Extract as JSON:
{{
  "hook_text": "exact opening line/phrase",
  "hook_type": "curiosity_gap|bold_claim|shocking_stat|relatable_problem|pattern_interrupt|tutorial",
  "emotional_triggers": ["list of triggers used"],
  "script_structure": "5-act breakdown summary",
  "cta_type": "follow|save|share|comment",
  "pacing": "slow|medium|fast",
  "visual_style": "talking_head|broll|screenshare|text_only|mixed",
  "key_phrases": ["top 3 memorable lines"],
  "viral_score_estimate": 7.5
}}"""

        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={"model": self.ollama_model, "prompt": prompt, "stream": False},
                )
                result = response.json().get("response", "")

                start = result.find("{")
                end = result.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(result[start:end])
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
        return None

    def update_hook_vault(self, analysis: dict, source_url: str = "", influencer: str = ""):
        """Add a new entry to the Hook Vault from analysis results."""
        vault_path = Path("src/intelligence/hook_vault.json")

        if vault_path.exists():
            with open(vault_path) as f:
                vault = json.load(f)
        else:
            vault = {"hooks": [], "patterns": []}

        hook_id = f"hook_{len(vault['hooks']) + 1:03d}"
        new_hook = {
            "id": hook_id,
            "category": analysis.get("hook_type", "unknown"),
            "template": analysis.get("hook_text", ""),
            "example": analysis.get("hook_text", ""),
            "viral_score_avg": analysis.get("viral_score_estimate", 5.0),
            "best_platforms": ["tiktok", "youtube"],
            "source_url": source_url,
            "influencer": influencer,
            "emotional_triggers": analysis.get("emotional_triggers", []),
            "added_at": datetime.now().isoformat(),
        }

        vault["hooks"].append(new_hook)

        with open(vault_path, "w") as f:
            json.dump(vault, f, indent=2)

        logger.info(f"Added hook {hook_id} to vault: {analysis.get('hook_type', 'unknown')}")
        return hook_id

    async def scout_topic(self, topic: str, max_videos: int = 3) -> list[dict]:
        """Scout a specific topic: find videos, analyze, update vault."""
        logger.info(f"Scouting topic: {topic}")

        # Search YouTube for the topic
        search_url = f"ytsearch{max_videos}:{topic}"

        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-download", "--flat-playlist", search_url],
                capture_output=True, text=True, timeout=60
            )

            analyses = []
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        try:
                            metadata = json.loads(line)
                            video_url = metadata.get("url") or metadata.get("webpage_url", "")
                            if video_url and not video_url.startswith("http"):
                                video_url = f"https://www.youtube.com/watch?v={video_url}"

                            # Get full metadata
                            full_meta = await self.fetch_video_metadata(video_url)

                            # Transcribe
                            transcript = await self.download_and_transcribe(video_url)

                            if transcript:
                                analysis = await self.analyze_viral_patterns(transcript, full_meta)
                                if analysis:
                                    self.update_hook_vault(analysis, video_url)
                                    analyses.append(analysis)
                        except json.JSONDecodeError:
                            continue

            return analyses
        except Exception as e:
            logger.error(f"Scout failed: {e}")
            return []

    async def run(self, tenant: str = "mas-ai", mode: str = "trends") -> dict:
        """Main entry point. mode='trends' for RSS scan, mode='scout' for video analysis."""
        if mode == "trends":
            trends = await self.scan_trends()
            top_5 = trends[:5]
            return {
                "mode": "trends",
                "total_scanned": len(trends),
                "top_trends": [{"title": t.title, "source": t.source, "score": t.relevance_score} for t in top_5],
            }
        elif mode == "scout":
            # Load influencers for tenant
            influencers_path = Path(f"tenants/{tenant}/influencers.json")
            if influencers_path.exists():
                with open(influencers_path) as f:
                    data = json.load(f)
                # Scout each influencer's content
                results = []
                for inf in data.get("influencers", [])[:3]:
                    analyses = await self.scout_topic(f"{inf['handle']} {data.get('niche', 'AI')}", max_videos=2)
                    results.extend(analyses)
                return {"mode": "scout", "analyses": len(results)}

        return {"mode": mode, "error": "Unknown mode"}


if __name__ == "__main__":
    async def test():
        scout = VirAIScout()
        print("Scanning trends from free sources...")
        result = await scout.run(mode="trends")
        print(json.dumps(result, indent=2))

    asyncio.run(test())
