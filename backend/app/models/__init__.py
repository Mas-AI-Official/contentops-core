"""
Database models and schemas.
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
from .niche_target import NicheTarget

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
]
