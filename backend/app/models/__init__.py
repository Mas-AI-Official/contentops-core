"""
Database models and schemas.
Import order matters for SQLAlchemy: referenced tables (e.g. accounts) must be imported before tables that FK to them (e.g. NicheTarget).
"""
from .niche import (
    Niche, NicheCreate, NicheUpdate, NicheRead, VideoStyle
)
from .account import (
    Account, AccountCreate, AccountUpdate, AccountRead,
    AccountStatus, AccountStatusCheck, Platform
)
from .job import (
    Job, JobCreate, JobUpdate, JobRead, JobLog, JobLogCreate,
    JobStatus, JobType
)
from .video import (
    Video, VideoCreate, VideoRead, VideoPublish
)
from .analytics import (
    VideoMetrics, DailyNicheStats, VideoScore, AnalyticsSummary
)
# NicheTarget references accounts.id — import after Account
from .niche_target import NicheTarget
from .trends import (
    TrendCandidate, PatternAnalysis, PromptPack, Artifact, ComplianceEvent
)
from .memory import MemoryIndex
from .voice import (
    VoiceProfile, VoiceProfileBase,
    NicheVoiceRule, NicheVoiceRuleBase,
    AccountVoiceRule, AccountVoiceRuleBase,
    SceneSpeakerMap, SceneSpeakerMapBase,
    VoiceStyle,
)

__all__ = [
    # Niche
    "Niche", "NicheCreate", "NicheUpdate", "NicheRead", "VideoStyle",
    # Account
    "Account", "AccountCreate", "AccountUpdate", "AccountRead",
    "AccountStatus", "AccountStatusCheck", "Platform",
    # Job
    "Job", "JobCreate", "JobUpdate", "JobRead", "JobLog", "JobLogCreate",
    "JobStatus", "JobType",
    # Video
    "Video", "VideoCreate", "VideoRead", "VideoPublish",
    # Analytics
    "VideoMetrics", "DailyNicheStats", "VideoScore", "AnalyticsSummary",
    # NicheTarget
    "NicheTarget",
    # Trends
    "TrendCandidate", "PatternAnalysis", "PromptPack", "Artifact", "ComplianceEvent",
    # Memory
    "MemoryIndex",
    # Voice
    "VoiceProfile", "VoiceProfileBase",
    "NicheVoiceRule", "NicheVoiceRuleBase",
    "AccountVoiceRule", "AccountVoiceRuleBase",
    "SceneSpeakerMap", "SceneSpeakerMapBase",
    "VoiceStyle",
]
