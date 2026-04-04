# ANALYTICS_SYSTEM.md — Performance Intelligence

---

## WHAT WE TRACK

Every published post is tagged with:
1. **Method tag** — which hook type, script structure, CTA style was used
2. **Platform** — where it was posted
3. **Tenant** — whose content it is
4. **Production metadata** — which models/tools were used

This lets us answer: *"When I use a curiosity_gap hook with a shocking_stat in act 3 on TikTok, what's the average completion rate?"*

---

## DATABASE SCHEMA (SQLite)

```sql
-- Posts table
CREATE TABLE posts (
  id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  external_post_id TEXT,
  script_id TEXT,
  method_tag TEXT,
  hook_type TEXT,
  published_at DATETIME,
  status TEXT DEFAULT 'published'
);

-- Metrics table (updated over time)
CREATE TABLE post_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id TEXT REFERENCES posts(id),
  collected_at DATETIME,
  views INTEGER DEFAULT 0,
  watch_time_seconds REAL DEFAULT 0,
  completion_rate REAL DEFAULT 0,
  rewatches INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  likes INTEGER DEFAULT 0,
  follows_gained INTEGER DEFAULT 0,
  viral_signal_triggered BOOLEAN DEFAULT FALSE
);

-- Method scores (aggregated)
CREATE TABLE method_scores (
  method_tag TEXT PRIMARY KEY,
  sample_count INTEGER DEFAULT 0,
  avg_completion_rate REAL,
  avg_share_rate REAL,
  avg_save_rate REAL,
  composite_virality_score REAL,
  status TEXT DEFAULT 'testing',  -- testing | active | promoted | retired
  last_updated DATETIME
);

-- Viral signals
CREATE TABLE viral_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id TEXT REFERENCES posts(id),
  signal_type TEXT,  -- rapid_growth | share_spike | save_spike
  detected_at DATETIME,
  views_at_detection INTEGER,
  action_taken TEXT  -- created_variations | escalated_to_operator
);
```

---

## VIRALITY COMPOSITE SCORE

```python
def calculate_virality_score(metrics: dict) -> float:
    """
    Weighted composite score based on 2026 algorithm weights.
    Range: 0.0 - 10.0
    """
    rewatch_rate = metrics.get("rewatches", 0) / max(metrics.get("views", 1), 1)
    completion_rate = metrics.get("completion_rate", 0)
    share_rate = metrics.get("shares", 0) / max(metrics.get("views", 1), 1)
    save_rate = metrics.get("saves", 0) / max(metrics.get("views", 1), 1)
    comment_rate = metrics.get("comments", 0) / max(metrics.get("views", 1), 1)
    like_rate = metrics.get("likes", 0) / max(metrics.get("views", 1), 1)
    
    score = (
        min(rewatch_rate * 100, 10) * 0.25 +   # Rewatch: 25% weight
        min(completion_rate * 10, 10) * 0.25 +  # Completion: 25%  
        min(share_rate * 200, 10) * 0.20 +      # Shares: 20%
        min(save_rate * 200, 10) * 0.15 +       # Saves: 15%
        min(comment_rate * 100, 10) * 0.10 +    # Comments: 10%
        min(like_rate * 20, 10) * 0.05          # Likes: 5%
    )
    
    return round(score, 2)
```

---

## VIRAL SIGNAL DETECTION

```python
async def check_viral_signals(post_id: str):
    """
    Called by Analytics Hawk every 6 hours for first 48h.
    """
    post = get_post(post_id)
    current_metrics = await fetch_platform_metrics(post)
    
    # Signal 1: Rapid growth (>10K views in 6h)
    if current_metrics["views"] > 10000 and post.age_hours < 6:
        await escalate_viral_signal(post, "rapid_growth", current_metrics)
        await create_variation_videos(post, count=3)
    
    # Signal 2: High share rate (>5%)
    share_rate = current_metrics["shares"] / max(current_metrics["views"], 1)
    if share_rate > 0.05:
        await escalate_viral_signal(post, "share_spike", current_metrics)
        mark_method_as_winner(post.method_tag)
    
    # Signal 3: High save rate (>3%)
    save_rate = current_metrics["saves"] / max(current_metrics["views"], 1)
    if save_rate > 0.03:
        await escalate_viral_signal(post, "save_spike", current_metrics)
```

---

## PLATFORM API CONNECTIONS

```python
# YouTube Analytics (requires OAuth — for Daena's channel)
from googleapiclient.discovery import build

def get_youtube_metrics(video_id: str) -> dict:
    youtube = build("youtubeAnalytics", "v2", credentials=get_credentials())
    response = youtube.reports().query(
        ids=f"channel=={CHANNEL_ID}",
        startDate="2026-01-01",
        endDate=datetime.today().strftime("%Y-%m-%d"),
        metrics="views,estimatedWatchTime,averageViewDuration,shares,likes,comments",
        filters=f"video=={video_id}"
    ).execute()
    return response

# TikTok Research API (requires Business account verification)
# Note: TikTok's official API is restricted. Use unofficial scraping as fallback.

# Instagram Graph API (requires Business/Creator account)
def get_instagram_metrics(media_id: str) -> dict:
    url = f"https://graph.instagram.com/v19.0/{media_id}/insights"
    params = {
        "metric": "impressions,reach,likes,comments,shares,saves,video_views",
        "access_token": os.environ["INSTAGRAM_ACCESS_TOKEN"]
    }
    return requests.get(url, params=params).json()
```

---

## DAILY ANALYTICS REPORT FORMAT

```markdown
# ContentOps Daily Report — {date}

## TODAY'S PERFORMANCE

| Post | Platform | Views | Completion | Shares | Score |
|------|----------|-------|------------|--------|-------|
| [script_title] | TikTok | 12,400 | 72% | 340 | 8.1 |

## TOP METHOD THIS WEEK
Method: curiosity_gap_product_reveal
Average virality score: 8.4
Posts using this method: 5
Recommendation: PROMOTED — use for 70% of next week's content

## VIRAL SIGNALS
- 🔥 [post_id] hit 15K views in 4 hours on TikTok (share_spike)
  → 3 variation videos queued

## UNDERPERFORMERS
- Method: shocking_stat_without_context — score 3.2 (5 samples)
  → RETIRING this method

## NEXT 7 DAYS QUEUE
[auto-generated content calendar]

## RECOMMENDED ADJUSTMENTS
- Increase posting frequency on TikTok (currently 3/week → try 5/week)
- Add progress bar to all videos (missing in last 3 posts)
- Hook text needs to appear faster (currently 1.5s in — should be 0s)
```
