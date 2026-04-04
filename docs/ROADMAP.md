# ContentOps Roadmap — MAS-AI Autonomous Media Agency

## Current: Phase 1 - Foundation (In Progress)
**Goal:** One real video produced end-to-end with Daena avatar.

| Component | Status | Notes |
|---|---|---|
| Tool Manager | Done | VRAM conflict resolution, 14 tools |
| Script Maestro | Done | 4-stage pipeline, persona-driven |
| Avatar Engine (Voice) | Done | Kokoro (free) + ElevenLabs (prod) |
| Avatar Engine (Overlay) | Done | Colorkey bg removal, dynamic sizing |
| Video Creative Director | Done | B-roll + dark overlay + avatar + captions + hook + progress bar |
| VirAI Scout | Done | 6 RSS sources, trend scanning |
| Distribution Engine | Done | 5 platforms, draft + API stubs |
| Analytics Hawk | Done | SQLite, viral signal detection |
| Method Optimizer | Done | Daily scoring, promote/retire |
| Pipeline Orchestrator | Done | Full wiring, batch mode |
| Dashboard API | Done | 30 routes, niche/platform CRUD |
| Dashboard Frontend | Done | React SPA, dark theme |
| Daena Persona System | Done | VP identity, per-act visual direction |

## Phase 2 — Platform Connections (Next)
**Goal:** Actually publish to real platforms.

| Feature | Priority | Notes |
|---|---|---|
| Instagram Graph API integration | P0 | Requires FB developer account + page |
| TikTok Content Posting API | P0 | Requires TikTok developer account |
| YouTube Data API v3 upload | P1 | OAuth2 flow, channel auth |
| LinkedIn API posting | P1 | Company page auth |
| X/Twitter API v2 | P2 | Elevated access needed |
| Threads API | P3 | When available |

## Phase 3 — Intelligence & Optimization
**Goal:** Self-tuning system that gets better automatically.

| Feature | Priority | Notes |
|---|---|---|
| MuseTalk lip sync integration | P1 | Custom lip-sync from PNG avatars |
| Real analytics collection | P1 | Platform API metrics polling |
| A/B method testing | P1 | Test hooks, compare results |
| Influencer tracking automation | P2 | Auto-update influencer DB |
| Trend prediction model | P2 | Predict topics before they peak |

## Phase 4 — Scale & Polish
**Goal:** Multi-tenant with polished operator experience.

| Feature | Priority | Notes |
|---|---|---|
| Multi-tenant onboarding flow | P1 | Self-service tenant creation |
| Custom avatar per tenant | P1 | Upload avatar, auto-crop/colorkey |
| Real-time viral alerts (WebSocket) | P2 | Dashboard push notifications |
| Method scoreboard visualization | P2 | Charts, trends, comparisons |
| Mobile-responsive dashboard | P3 | Operator on the go |

## Future Features (Backlog)

### Ads Maker Module
- Same pipeline but for paid advertising content
- Different script structure: Problem → Solution → CTA → Proof
- Auto-generate multiple ad variants for A/B testing
- Platform ad specs (different from organic specs)
- Budget tracking and ROAS analytics
- Separate dashboard page: /ads

### Manual Topic Queue
- Customer drops a topic → enters content queue
- Bypasses VirAI Scout scraping stage
- Goes directly to Script Maestro S1 (Extract)
- Dashboard: text box + priority selector + platform picker

### Script-to-Video (Direct)
- Customer provides finished script text
- Skips S1-S4 entirely → goes straight to Voice
- Optional: with or without avatar
- Use case: branded content, product announcements, prepared statements

### Customer Analytics Page
- Per-tenant performance dashboard
- Best performing content by niche
- Audience growth charts
- Engagement rate trends
- Posting frequency recommendations
- Revenue attribution (for agency billing)

### Content Calendar View
- Visual calendar showing scheduled posts
- Drag-and-drop rescheduling
- Color-coded by niche/platform
- Conflict detection (too many posts same day)

### Bulk Content Generation
- Upload CSV of topics → batch pipeline
- Progress tracking per item
- Quality gate summary report
- Failed items automatically retried

### White-Label Mode
- Remove MAS-AI branding
- Custom colors, logos, domain
- Tenant-specific dashboards
- API keys per tenant
