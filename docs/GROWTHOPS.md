# Claude directing MAS-AI ContentOps

This extension gives Claude project skills and a durable local control plane.
Claude chooses the brief and reviews evidence. The existing renderer, local
models and supported media tools execute production steps. Campaign work and
customer research have separate queues. This does not create a second CRM.

The GitHub checkout used for this change was based on June 2026 code. The
owner's Windows launch work is newer. Review and integrate this bounded change
without resetting that working tree or re-running the old news pipeline.

## Current operating decisions

- Keep the generic news scheduler and global publishing STOP controls stopped.
  No code in this extension changes those files or starts a scheduler.
- Preserve the completed 18-export batch, its actual QA and unfinished
  claims/disclosure review. Do not declare old exports newly verified here.
- Use the approved AI representation of Masoud and his approved voice assets.
  No new founder camera shoot is required. Keep one identity and voice per
  series, record hashes and disclose synthetic presentation. Daena is a
  product/proof, not the founder or the whole MAS-AI business.
- Routine authorized research, drafting, installation and supported organic
  work can proceed. Authentication, an actual new financial commitment and a
  required irreversible-action confirmation remain real boundaries.
- Use current commercial records. Do not invent pricing, guaranteed ROI,
  partnerships, testimonials or measured speed improvements.

## Skills and shared registry

The checked-in `.agents/skills/` directory contains project snapshots of three
personal MAS-AI skills. Their shared entry point is `mas-ai-growth-ops`.

| Skill | Purpose |
|---|---|
| mas-ai-growth-ops | Claude direction, offers, Hormozi value levers, hooks, UGC, motion, QA and tool routing |
| mas-ai-linkedin | Personal/company identity, page audit, historical-post decisions and distinct publication receipts |
| mas-ai-prospecting | Sourced business research, qualification, contact eligibility, outreach and proposals |
| remotion-best-practices | Official motion/render guidance, installed separately from its upstream source |

`skill-registry.json` records source and capability status. Vendor skills remain
vendor-owned. The registry points to Adobe, Higgsfield, Canva, image creation and
Metricool routes rather than copying every vendor skill into a second catalog.
Tool availability does not prove account access or a spendable balance.

To install the three project skills for Claude Code in this checkout:

```bash
python scripts/install_growth_skills.py
```

The installer preserves locally modified skills and unrelated MCP entries. It
reports a conflict before writing anything when reconciliation is needed.
An optional `--remotion-source` argument accepts the upstream
`skills/remotion-best-practices` directory. The reviewed upstream revision is
recorded in `skill-registry.json`. Clone that repository and check out the exact
revision before using the argument. Do not apply guidance for newer Remotion
APIs until the renderer's installed version has been checked.

## Optional Claude MCP bridge

Use an isolated environment so the existing renderer/runtime is not upgraded.
Python 3.10 or newer is required by the selected MCP SDK. On Windows:

```powershell
py -m venv .venv-growth
.\.venv-growth\Scripts\python.exe -m pip install -r requirements-growth.txt
.\.venv-growth\Scripts\python.exe scripts/install_growth_skills.py --configure-mcp
```

The last command adds the local `contentops-growth` stdio server to this
project's `.mcp.json`, using the actual Python executable and checkout path.
It stores no model key or social credential. Reload the project in Claude Code
to discover its project skills and MCP server. Follow Claude's actual project
trust/security controls; this is not a bypass of them.

The official Claude Agent SDK is optional. Existing Claude Code can direct the
tools without buying a second API plan. For SDK automation, first verify the
current SDK interface and the account's actual eligible balance. Load user and
project filesystem settings/skills explicitly, bound turns and concurrency,
and reconcile cost per run. A stated $100 credit is not a verified balance.
No SDK research worker or recurring paid task is started by this extension.

## What the bridge actually does

The 11 MCP tools inspect status, list skills, prepare/list/complete bounded
tasks, stage sourced business research, compare presenter manifests, prepare
distribution and reserve/record research cost. The stdlib CLI provides status,
skills, jobs, enqueue, prospects and save-prospect commands.

```bash
python scripts/growthops.py status
python scripts/growthops.py skills
python scripts/growthops.py jobs
```

Queue state is persisted in `data/growthops/state.sqlite3`, ignored by Git.
Keys are idempotent within a lane; conflicting reuse fails. Completed results
are immutable. A queued or completed draft is not a published post. Claude must
perform each authorized production step using the relevant existing tool and
record its actual artifact/receipt before completing a task. There is no hidden
background execution service.

Business observations are a research staging cache. The existing
`tracker/dashboard.html`, `leads.csv` and other current campaign records remain
the authoritative CRM. Reconcile their schema and suppression records before
updating them or contacting anyone. Do not create another sales dashboard.
Staged contact eligibility defaults to `evidence_review_required`. A model
boolean cannot certify consent. A staged opt-out survives later updates.

## Social connections and historical cleanup

Use a supported authenticated connector or official OAuth adapter. The old
`LinkedInPublisher` password client now returns a clear blocked result and
never submits a post. This is an intentional compatibility change: old callers
must migrate rather than silently reporting a publication without an ID.

Metricool brand 7443431 was connected to the app, but had no social networks
linked when checked on 2026-10-15. Connect the correct personal and company
destinations and re-read their actor IDs before publication. A profile mention
does not publish to a company page. Profile menus and historical native-post
deletion require authenticated LinkedIn admin access; Metricool does not provide
those operations here. A deletion candidate needs its exact URL, evidence and
any required action-time confirmation.

Do not treat low views alone as a reason to remove a post. Review on-message
content, unsupported claims, repetition, privacy, disclosure and actual final
video quality. Keep an archive and a decision record.

## Research cost controls

The media ledger remains separate. The current recorded Higgsfield pilot cap is
US$10 total, US$2 per generation and US$10/day, subject to reconciling earlier
actual charges. Do not replace it with a suggested benchmark budget.

Research reservations are disabled until an actual verified budget is placed
in `data/growthops/research-budget.json`. Example shape, intentionally inactive:

```json
{"currency":"USD","balance_verified":false,"total_cap_usd":0,"max_job_usd":0}
```

Only prospecting jobs can reserve research costs. Reservations are atomic,
include outstanding reservations in the cap and are idempotent per job. Use one
provider-billed unit per job. Actual overruns are recorded rather than hidden and
reduce remaining budget. This ledger is not a provider-side billing limit: the
executor must honor the reservation and the provider's own hard limits. Never
mark a balance verified from an unverified instruction or enable top-ups.

## Quality and monitoring

Preserve the existing caption fixes: lower safe band, rightward word growth,
no overlap through the full animation and readable crops. Keep a shared motion
token source, semantic transitions, subject/tool/problem covers, final-file
speech/loudness and hold-aware freeze QA. An identity/voice manifest check
helps consistency but does not replace watching the final render.

Use queue age/status, failed attempts, actual costs, asset hashes, actor IDs,
published IDs, enquiries and booked calls. Unknown analytics stay unknown.
Live social monitoring cannot be enabled until an authenticated read succeeds
on the connected network. No recurring monitoring was scheduled here while
Metricool's networks were unlinked.

## Validation

```bash
python -m unittest discover -s tests -v
```

The optional stdio integration test runs when `mcp` is installed. It launches
the actual server and exercises tool discovery and durable idempotent queueing.
Other tests cover STOP preservation, competing budget reservations, actual
overages, opt-out persistence, destination isolation, presenter mismatches and
installation conflicts. No live social or paid-generation test is part of this
suite.
