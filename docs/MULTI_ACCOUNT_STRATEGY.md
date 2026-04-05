# Multi-Account Content Strategy

## 3 Personas, 3 Content Tiers

### Persona 1: DAENA (AI Influencer)
- **Voice**: Confident, sharp, slightly witty, data-driven
- **Content**: AI trends, viral hooks, hot takes, behind-the-scenes
- **Platforms**: TikTok, Instagram, X/Twitter
- **Goal**: Audience growth, virality, brand awareness

### Persona 2: MASOUD (Founder)
- **Voice**: Authentic, builder energy, transparent, technical depth
- **Content**: Founder journey, build-in-public, opinions, lessons learned
- **Platforms**: X/Twitter, LinkedIn (personal)
- **Goal**: Personal brand, investor visibility, thought leadership

### Persona 3: MAS-AI (Company)
- **Voice**: Professional, authoritative, product-focused
- **Content**: Product updates, demos, case studies, hiring, partnerships
- **Platforms**: X/Twitter, LinkedIn (company), YouTube, Instagram, Discord, Telegram
- **Goal**: Credibility, leads, community, SEO

---

## Content Flow (One Topic → 11 Channels)

```
[1 TOPIC] → ScriptMaestro generates 3 script variants:

  DAENA script (casual, hook-driven, 60s)
    → TikTok @daena_ai (9:16, 60s)
    → Instagram @daena.ai (9:16, 60s reel)
    → X @daena_ai (16:9 or 1:1, 2:20 max)

  MASOUD script (personal take, 60-90s)
    → X @masoud_personal (16:9, with text thread)
    → LinkedIn Masoud (16:9 or text post with video)

  MAS-AI script (product angle, professional, 60-120s)
    → X @masai_company (16:9 with link)
    → LinkedIn MAS-AI (16:9, company page)
    → YouTube MAS-AI (9:16 Short OR 16:9 longer)
    → Instagram @mas_ai.co (9:16 reel)
    → Discord #announcements (embed + text)
    → Telegram channel (embed + text)
```

---

## Cross-Influence Rules

Each post includes a CTA that drives traffic to another channel:

| From | To | CTA Example |
|------|-----|-------------|
| TikTok (Daena) | YouTube (MAS-AI) | "Full breakdown on our YouTube →" |
| TikTok (Daena) | Instagram (Daena) | "More on my Instagram @daena.ai" |
| Instagram (Daena) | TikTok (Daena) | "Catch the full version on TikTok" |
| X (Daena) | Discord | "Join the conversation in Discord →" |
| X (Masoud) | LinkedIn (Masoud) | "Longer take on LinkedIn →" |
| X (Masoud) | X (Daena) | "My VP @daena_ai broke this down →" |
| X (MAS-AI) | YouTube | "Watch the demo →" |
| LinkedIn (Masoud) | X (Masoud) | "Thread on this on X →" |
| LinkedIn (MAS-AI) | YouTube | "See the full demo →" |
| YouTube (MAS-AI) | Discord | "Discuss this in our Discord →" |
| Discord | All | Hub links to all channels |
| Telegram | YouTube/Discord | "Watch → Join →" |

### Influence Amplification
- Daena REPLIES to Masoud's tweets (and vice versa) — creates engagement
- MAS-AI RETWEETS both Daena and Masoud — distributes reach
- Masoud shares Daena's TikToks on LinkedIn with founder commentary
- All bios link to Discord as the community home base

---

## Posting Schedule (Per Week)

| Platform | Account | Posts/Week | Best Times (ET) |
|----------|---------|-----------|-----------------|
| TikTok | @daena_ai | 5 | 7am, 12pm, 7pm |
| Instagram | @daena.ai | 4 | 8am, 11am, 5pm |
| Instagram | @mas_ai.co | 3 | 8am, 11am, 5pm |
| X/Twitter | @daena_ai | 7 | 8am, 12pm, 5pm, 9pm |
| X/Twitter | @masoud | 5 | 8am, 12pm, 5pm |
| X/Twitter | @masai | 3 | 10am, 2pm |
| LinkedIn | Masoud | 3 | 8am, 10am |
| LinkedIn | MAS-AI | 2 | 8am, 10am |
| YouTube | MAS-AI | 3 | 2pm, 4pm, 8pm |
| Discord | MAS-AI | Daily | When content drops |
| Telegram | MAS-AI | Daily | When content drops |

**Total: ~38 posts/week across 11 channels from ~5 unique topics**

---

## Account Credentials Map

| Account | Auth Method | Config Key |
|---------|------------|------------|
| TikTok @daena_ai | Cookie file | tiktok.daena |
| IG @daena.ai | instagrapi login | instagram.daena |
| IG @mas_ai.co | instagrapi login | instagram.masai |
| X @daena_ai | OAuth 1.0a | twitter.daena |
| X @masoud | OAuth 1.0a | twitter.masoud |
| X @masai | OAuth 1.0a | twitter.masai |
| LinkedIn Masoud | Cookie/API | linkedin.masoud |
| LinkedIn MAS-AI | Cookie/API | linkedin.masai |
| YouTube MAS-AI | OAuth 2.0 | youtube.masai |
| Discord MAS-AI | Bot token | discord.masai |
| Telegram MAS-AI | Bot token | telegram.masai |
