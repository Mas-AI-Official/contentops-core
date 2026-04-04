# VIRAL_INTELLIGENCE.md — How to Study and Replicate Viral Content

---

## THE VIRAL FORMULA (2026 Data)

Based on reverse-engineering thousands of viral videos across TikTok, YouTube Shorts, and Reels:

### THE SCORING MATRIX
```
Signal          Weight    Target
─────────────────────────────────────────
Rewatch rate    10pts     > 15–20%
Completion rate  8pts     > 70% (TikTok 2026)
Shares           6pts     > 3% of views
Saves            5pts     > 2% of views  
Comments         4pts     > 1% of views
Likes            2pts     > 5% of views (weakest signal)
```

### HOOK TAXONOMY (classify every viral video into these)

```
Type 1: CURIOSITY GAP
"Most people don't know this about GPT-4..."
"ChatGPT just quietly changed something important..."
Formula: Implies hidden knowledge that only continued watching reveals
Virality driver: Completion rate (they HAVE to see the payoff)

Type 2: BOLD CLAIM / CONTRARIAN TAKE
"AI will not replace programmers — it'll make bad ones invisible"
"Stop using LangChain. Here's why."
Formula: State a strong, potentially controversial opinion immediately
Virality driver: Comments (agree/disagree debate = algorithm gold)

Type 3: SHOCKING STAT / DATA REVEAL
"87% of AI startups fail in their first year. Here's the pattern."
"This 2-person AI startup makes $4M/year with zero employees."
Formula: Lead with a number that seems impossible or surprising
Virality driver: Shares (people send to friends who "need to see this")

Type 4: RELATABLE PROBLEM / IDENTITY TRIGGER
"If you've been building AI agents for more than 6 months, you know this feeling..."
"Every developer who's used Claude has hit this exact wall."
Formula: Make a specific group feel SEEN and understood
Virality driver: Saves + shares within community (identity = community signal)

Type 5: PATTERN INTERRUPT
[Video starts mid-sentence, or with unexpected visual]
"—which is why I deleted 2 years of code. Let me explain."
Formula: Start in the middle of something surprising. Force them to piece it together.
Virality driver: Rewatch rate (they rewatch to understand from the beginning)

Type 6: TUTORIAL / HIGH UTILITY
"How to build a Claude agent in 60 seconds that actually works"
"The ONLY way to structure AI memory that doesn't break"
Formula: Promise a specific, useful skill deliverable
Virality driver: Saves (bookmarked for later = strong algorithm signal)
```

---

## THE 5-ACT STRUCTURE (MANDATORY FOR ALL SCRIPTS)

```
ACT 1 — THE HOOK (0–3 seconds)
Purpose: Stop the scroll. Create an immediate reason to stay.
Technique: Visual + audio simultaneously. Don't rely on just text.
Rule: Never start with "Hey guys" or "So today we're going to..."
Target: Completion rate boost through initial engagement

ACT 2 — CURIOSITY BUILD (3–15 seconds)
Purpose: Make staying uncomfortable — they need to know the payoff.
Technique: Open a loop. Hint at what's coming without delivering it.
Rule: No payoff yet. Tension only.
Example: "And the reason this matters to you specifically is..."

ACT 3 — VALUE DELIVERY (15–45 seconds)
Purpose: Pay off the hook. Give genuine value.
Technique: Specific, not generic. Data, story, or demonstration.
Rule: Every sentence removes one layer of the onion. Don't give everything at once.
Target: Completion rate + shares (they share because of the value in this section)

ACT 4 — EMOTIONAL PEAK (45–55 seconds)
Purpose: Create an emotional reaction that triggers sharing.
Technique: Identity statement, surprising twist, or moment of recognition.
Examples: "This is why I quit my $300K job", "I tried this for 30 days and...", "And this is why most people stay stuck"
Target: Shares + saves

ACT 5 — CTA (55–60 seconds)
Purpose: Tell them exactly what to do next.
Technique: One action only. Match to platform and content type.
TikTok: "Follow Daena for tomorrow's drop" / "Save this, you'll need it"
YouTube: "Subscribe — there's a Part 2 coming"
LinkedIn: "Share this if your team needs to hear it"
```

---

## INFLUENCER ANALYSIS PROTOCOL

When VirAI Scout runs on an influencer:

### Step 1: Select videos
```
Criteria for analysis selection:
- Must have >100K views (meaningful sample)
- Published in last 90 days (algorithm hasn't changed for older content)
- Minimum 3 videos per influencer
- Mix of viral (>500K) and average performers (50–150K) — learn the delta
```

### Step 2: Download + transcribe
```bash
# Get video metadata first
yt-dlp --dump-json --no-download {url} > metadata.json

# Download if selected
yt-dlp --write-info-json -f "bestvideo[height<=720]+bestaudio/best[height<=720]" \
  -o "data/scraped/{niche}/{creator}/%(upload_date)s_%(id)s.%(ext)s" {url}

# Transcribe
python -c "
import whisper, json
model = whisper.load_model('base')
result = model.transcribe('video.mp4', word_timestamps=True)
print(json.dumps(result))
" > transcript.json
```

### Step 3: Analyze with Gemini CLI
```bash
gemini -p "
You are a viral content analyst. Analyze this transcript and metadata.

VIDEO STATS:
Views: {views}
Likes: {likes}  
Comments: {comments}
Upload Date: {date}

TRANSCRIPT:
{transcript}

Provide a JSON analysis with these exact keys:
{
  hook_text: first sentence/phrase verbatim,
  hook_type: one of [curiosity_gap, bold_claim, shocking_stat, relatable_problem, pattern_interrupt, tutorial],
  acts: [{act: 1, timestamp_start: X, timestamp_end: Y, summary: text},...],
  emotional_triggers: [],
  virality_drivers: [explanation of why this likely performed well],
  cta_type: follow/save/share/comment/link,
  pacing: slow/medium/fast/variable,
  visual_style: talking_head/broll_heavy/screenshare/text_only/mixed,
  key_phrases: [top 5 most memorable lines],
  weakness: [what could be improved],
  viral_score_estimate: 1-10
}
"
```

### Step 4: Extract patterns
After analyzing 5+ videos from same creator:
- What hook TYPE do they use 80% of the time?
- What emotional triggers appear in ALL their viral hits?
- What's their average hook-to-value delivery timing?
- What CTAs correlate with their highest engagement?

---

## THE HOOK VAULT DATABASE SCHEMA

```json
{
  "hooks": [
    {
      "id": "hook_001",
      "category": "curiosity_gap",
      "template": "Most [AUDIENCE] don't know [SHOCKING_FACT_ABOUT_TOPIC]...",
      "example": "Most AI engineers don't know ChatGPT's hidden memory mode...",
      "viral_score_avg": 8.7,
      "sample_count": 12,
      "best_platforms": ["tiktok", "instagram"],
      "best_niches": ["ai-tools", "tech-education"],
      "notes": "Works best when the 'hidden fact' is genuinely surprising to the target audience"
    }
  ],
  "patterns": [
    {
      "name": "curiosity_gap_product_reveal",
      "description": "Start with a feature/change most don't know about, then reveal it step by step",
      "hook_type": "curiosity_gap",
      "viral_score": 9.1,
      "template_script": "...",
      "successful_examples": ["url1", "url2"]
    }
  ]
}
```

---

## TREND DETECTION

### Daily trend scan (Gemini CLI):
```bash
# Run every morning at 06:00
gemini -p "
What are the top 5 trending AI/tech topics on TikTok and Twitter/X right now?
For each topic:
1. What's the hook people are using?
2. Why is it resonating (psychological trigger)?
3. How can an AI startup influencer add their perspective?
Output as JSON array.
"
```

### Platform trend sources:
```
TikTok:    TikTok Creative Center (free) → trending topics, sounds, hashtags
YouTube:   YouTube Trending + Keywords Everywhere
Twitter/X: Twitter Trends API (free tier) + Grok search
LinkedIn:  LinkedIn hashtag analytics
Reddit:    r/artificial, r/MachineLearning, r/LocalLLaMA (via Reddit API)
```

---

## CONTENT CALENDAR INTELLIGENCE

### Optimal posting cadence (2026 data):
```
Platform     Posts/week    Best days           Best time (local)
──────────────────────────────────────────────────────────────────
TikTok       3-5           Tue, Thu, Fri, Sat  7am, 12pm, 7pm
Instagram    3-4           Mon, Wed, Fri       8am, 11am, 5pm
YouTube      2-3           Mon, Wed, Fri       2pm, 4pm, 8pm
LinkedIn     2-3           Tue, Wed, Thu       8am, 10am, 12pm
X/Twitter    5-7           Mon-Fri             8am, 12pm, 5pm, 9pm
```

### Content mix (AI niche, Daena):
```
40% Educational/Tutorial    ("How to build X", "Stop doing Y")
25% Opinion/Contrarian      ("Hot take:", "Unpopular opinion:")  
20% Behind the scenes       ("Building Daena taught me...", "Day in the life of")
10% News commentary         ("What OpenAI just announced means...")
5%  Community/Engagement    (Polls, questions, "Tell me which one")
```
