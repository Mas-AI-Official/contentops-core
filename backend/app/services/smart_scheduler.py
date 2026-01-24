"""
Smart Scheduler Service
Determines optimal posting times based on platform analytics and audience engagement patterns.
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
import random
from dataclasses import dataclass
import json

from loguru import logger


@dataclass
class PostingTime:
    """Represents an optimal posting time."""
    hour: int
    minute: int
    platform: str
    score: float  # 0-1, higher is better
    reason: str

    def to_datetime(self, base_date: datetime) -> datetime:
        """Convert to datetime for the given date."""
        return base_date.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)


class SmartScheduler:
    """Intelligent scheduling based on platform analytics."""

    def __init__(self):
        # Default optimal posting times for different platforms
        # These are based on general social media analytics
        self.platform_optimal_times = {
            "youtube": [
                # Weekdays: 2-4 PM, 7-9 PM
                (14, 0, 0.9, "Peak afternoon viewing"),
                (15, 30, 0.85, "High engagement time"),
                (16, 0, 0.8, "Good afternoon slot"),
                (19, 0, 0.95, "Prime evening time"),
                (20, 30, 0.9, "Peak evening viewing"),
                (21, 0, 0.85, "Late evening engagement"),
                # Weekends: 10 AM - 2 PM
                (10, 0, 0.8, "Weekend morning"),
                (11, 30, 0.85, "Weekend mid-morning"),
                (13, 0, 0.9, "Weekend early afternoon"),
                (14, 30, 0.85, "Weekend afternoon")
            ],
            "instagram": [
                # Weekdays: 11 AM - 1 PM, 7-9 PM
                (11, 0, 0.9, "Morning peak"),
                (12, 30, 0.95, "Midday high engagement"),
                (13, 0, 0.85, "Early afternoon"),
                (19, 0, 0.9, "Evening peak"),
                (20, 30, 0.85, "Late evening"),
                # Weekends: 10 AM - 3 PM
                (10, 0, 0.85, "Weekend morning"),
                (11, 30, 0.9, "Weekend mid-morning"),
                (14, 0, 0.9, "Weekend afternoon"),
                (15, 30, 0.85, "Weekend late afternoon")
            ],
            "tiktok": [
                # Best times: 6-10 AM, 7-9 PM
                (6, 30, 0.9, "Early morning peak"),
                (8, 0, 0.95, "Morning viral time"),
                (9, 30, 0.9, "Late morning"),
                (19, 0, 0.95, "Evening peak"),
                (20, 30, 0.9, "Late evening"),
                (21, 30, 0.85, "Night time"),
                # Weekends: 9 AM - 12 PM
                (9, 0, 0.85, "Weekend morning"),
                (10, 30, 0.9, "Weekend mid-morning"),
                (11, 30, 0.85, "Weekend late morning")
            ]
        }

    def get_optimal_posting_times(
        self,
        platform: str,
        date: datetime,
        count: int = 3,
        avoid_conflicts: Optional[List[datetime]] = None
    ) -> List[PostingTime]:
        """
        Get optimal posting times for a specific platform and date.

        Args:
            platform: Platform name (youtube, instagram, tiktok)
            date: Date to schedule for
            count: Number of optimal times to return
            avoid_conflicts: List of existing scheduled times to avoid

        Returns:
            List of optimal PostingTime objects
        """
        if platform not in self.platform_optimal_times:
            # Default times if platform not recognized
            times = [
                (12, 0, 0.7, "Default midday"),
                (18, 0, 0.7, "Default evening"),
                (20, 0, 0.7, "Default night")
            ]
        else:
            times = self.platform_optimal_times[platform]

        # Create PostingTime objects
        posting_times = []
        for hour, minute, score, reason in times:
            posting_time = PostingTime(
                hour=hour,
                minute=minute,
                platform=platform,
                score=score,
                reason=reason
            )
            posting_times.append(posting_time)

        # Adjust scores based on day of week
        day_of_week = date.weekday()  # 0=Monday, 6=Sunday

        for pt in posting_times:
            # Weekend bonus for instagram and tiktok
            if day_of_week >= 5 and platform in ["instagram", "tiktok"]:
                pt.score = min(1.0, pt.score * 1.2)
            # Weekend penalty for youtube (more professional content)
            elif day_of_week >= 5 and platform == "youtube":
                pt.score *= 0.9

        # Avoid conflicts - reduce score for times too close to existing posts
        if avoid_conflicts:
            for pt in posting_times:
                pt_datetime = pt.to_datetime(date)
                for conflict in avoid_conflicts:
                    time_diff = abs((pt_datetime - conflict).total_seconds())
                    if time_diff < 3600:  # Within 1 hour
                        pt.score *= 0.3  # Heavy penalty
                    elif time_diff < 7200:  # Within 2 hours
                        pt.score *= 0.7  # Moderate penalty

        # Sort by score and return top count
        posting_times.sort(key=lambda x: x.score, reverse=True)
        return posting_times[:count]

    def schedule_content_for_day(
        self,
        platforms: List[str],
        date: datetime,
        existing_schedules: Optional[Dict[str, List[datetime]]] = None
    ) -> Dict[str, List[PostingTime]]:
        """
        Schedule content for multiple platforms for a given day.

        Args:
            platforms: List of platform names
            date: Date to schedule for
            existing_schedules: Dict of platform -> list of existing scheduled times

        Returns:
            Dict of platform -> list of PostingTime objects
        """
        schedule = {}

        for platform in platforms:
            # Get existing times for this platform
            existing_times = existing_schedules.get(platform, []) if existing_schedules else []

            # Get optimal times, avoiding conflicts
            optimal_times = self.get_optimal_posting_times(
                platform=platform,
                date=date,
                count=2,  # 2 posts per platform per day max
                avoid_conflicts=existing_times
            )

            schedule[platform] = optimal_times

        return schedule

    def get_next_optimal_time(
        self,
        platform: str,
        current_time: Optional[datetime] = None
    ) -> PostingTime:
        """
        Get the next optimal posting time from now.

        Args:
            platform: Platform name
            current_time: Current time (defaults to now)

        Returns:
            Next optimal PostingTime
        """
        if current_time is None:
            current_time = datetime.now()

        # Try today first
        today_times = self.get_optimal_posting_times(platform, current_time, count=5)

        # Find the next time today that's in the future
        for pt in today_times:
            scheduled_time = pt.to_datetime(current_time)
            if scheduled_time > current_time:
                return pt

        # If no times today, get tomorrow's best time
        tomorrow = current_time + timedelta(days=1)
        tomorrow_times = self.get_optimal_posting_times(platform, tomorrow, count=1)
        return tomorrow_times[0] if tomorrow_times else PostingTime(
            hour=12, minute=0, platform=platform, score=0.5, reason="Default time"
        )


# Global instance
smart_scheduler = SmartScheduler()