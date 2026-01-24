"""
Growth Engine Service - 70/30 Strategy Implementation
70% proven content (highest performing), 30% experiments (new templates)
"""

import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

from app.core.config import settings
from app.db import get_sync_session
from app.models import Niche, Job, JobCreate, JobType
from app.services.topic_service import topic_service


class GrowthEngineService:
    """Implements 70/30 growth strategy for content selection."""

    def __init__(self):
        self.templates_cache = {}
        self.performance_weights = {}

    def get_content_template(self, niche: Niche, experiment_chance: float = 0.3) -> Dict[str, Any]:
        """
        Select content template using 70/30 strategy.

        Args:
            niche: Niche object
            experiment_chance: Probability of selecting experimental template (default 30%)

        Returns:
            Template configuration dict
        """
        # Load niche templates and performance data
        templates = self._load_niche_templates(niche)
        if not templates:
            return self._get_default_template(niche)

        # Calculate weights based on performance
        weighted_templates = self._calculate_template_weights(templates)

        # 70/30 decision: 70% proven, 30% experiment
        if random.random() < experiment_chance:
            # Select experimental template (lower performing or new)
            template = self._select_experimental_template(weighted_templates)
            template['is_experiment'] = True
        else:
            # Select proven template (highest performing)
            template = self._select_proven_template(weighted_templates)
            template['is_experiment'] = False

        return template

    def _load_niche_templates(self, niche: Niche) -> List[Dict[str, Any]]:
        """Load templates for a niche from disk."""
        templates_dir = settings.niches_path / niche.slug / "templates"
        if not templates_dir.exists():
            return []

        templates = []
        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                    template['_file_path'] = template_file
                    templates.append(template)
            except Exception as e:
                print(f"Failed to load template {template_file}: {e}")

        return templates

    def _calculate_template_weights(self, templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate performance weights for templates."""
        weighted_templates = []

        for template in templates:
            # Base weight from performance metrics
            base_weight = template.get('performance_score', 50)  # Default 50

            # Adjust based on recent performance
            recent_views = template.get('recent_views', 0)
            recent_likes = template.get('recent_likes', 0)
            recent_comments = template.get('recent_comments', 0)

            # Calculate engagement score
            engagement_score = 0
            if recent_views > 0:
                engagement_score = ((recent_likes + recent_comments * 2) / recent_views) * 100

            # Combined weight
            final_weight = (base_weight * 0.7) + (engagement_score * 0.3)

            template_copy = template.copy()
            template_copy['weight'] = max(final_weight, 1)  # Minimum weight of 1
            weighted_templates.append(template_copy)

        return weighted_templates

    def _select_proven_template(self, weighted_templates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select highest performing template (70% case)."""
        if not weighted_templates:
            return self._get_default_template()

        # Sort by weight descending and pick top performer
        sorted_templates = sorted(weighted_templates, key=lambda x: x['weight'], reverse=True)
        return sorted_templates[0]

    def _select_experimental_template(self, weighted_templates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select experimental template (30% case)."""
        if not weighted_templates:
            return self._get_default_template()

        # Select from lower 50% performers or completely new templates
        sorted_templates = sorted(weighted_templates, key=lambda x: x['weight'])
        lower_half = sorted_templates[:len(sorted_templates)//2]

        if lower_half:
            return random.choice(lower_half)
        else:
            # If no lower half, pick random
            return random.choice(weighted_templates)

    def _get_default_template(self, niche: Niche = None) -> Dict[str, Any]:
        """Get default template when no custom templates exist."""
        return {
            'name': 'default_listicle',
            'type': 'listicle',
            'hook_style': 'question',
            'body_format': 'numbered_list',
            'cta_style': 'call_to_action',
            'target_length': 60,
            'is_experiment': False,
            'weight': 50,
            'performance_score': 50
        }

    def update_template_performance(self, niche_slug: str, template_name: str,
                                  views: int, likes: int, comments: int):
        """Update template performance metrics."""
        templates_dir = settings.niches_path / niche_slug / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)

        template_file = templates_dir / f"{template_name}.json"

        # Load existing data
        template_data = {}
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
            except:
                pass

        # Update metrics
        template_data['recent_views'] = views
        template_data['recent_likes'] = likes
        template_data['recent_comments'] = comments
        template_data['last_updated'] = datetime.now().isoformat()

        # Recalculate performance score
        engagement_rate = 0
        if views > 0:
            engagement_rate = ((likes + comments * 2) / views) * 100

        old_score = template_data.get('performance_score', 50)
        new_score = (old_score * 0.8) + (engagement_rate * 0.2)  # Weighted average
        template_data['performance_score'] = new_score

        # Save updated data
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)

    def generate_content_idea(self, niche: Niche, template: Dict[str, Any]) -> str:
        """
        Generate content idea using the Notes.txt strategy.
        Based on health niche example: "I'm ginger, if you eat me..." format
        """
        template_type = template.get('type', 'listicle')
        hook_style = template.get('hook_style', 'question')

        if template_type == 'health_tips':
            # Implement the ginger example style: "I'm X, if you Y..."
            foods = [
                "ginger", "turmeric", "garlic", "honey", "lemon", "apple cider vinegar",
                "green tea", "berries", "nuts", "oily fish", "broccoli", "sweet potato"
            ]

            food = random.choice(foods)

            if hook_style == 'question':
                hook = f"What happens if you eat {food} every day?"
            elif hook_style == 'statement':
                hook = f"I'm {food}. If you eat me daily, this happens to your body."
            else:
                hook = f"The surprising benefits of eating {food} every day."

            return hook

        elif template_type == 'listicle':
            # Standard listicle format
            topics = [
                f"5 surprising ways {niche.name.lower()} can change your life",
                f"What nobody tells you about {niche.name.lower()}",
                f"The {niche.name.lower()} secrets that actually work",
                f"Why {niche.name.lower()} is more important than you think"
            ]
            return random.choice(topics)

        else:
            # Generic topic generation
            return f"Everything you need to know about {niche.name.lower()}"

    def create_daily_content_plan(self, niche: Niche, posts_per_day: int = 2) -> List[Dict[str, Any]]:
        """
        Create daily content plan using 70/30 strategy.
        Returns list of content ideas with templates.
        """
        plan = []

        for i in range(posts_per_day):
            # Select template using 70/30 strategy
            template = self.get_content_template(niche)

            # Generate content idea
            idea = self.generate_content_idea(niche, template)

            plan.append({
                'slot': i + 1,
                'template': template,
                'idea': idea,
                'scheduled_time': self._calculate_slot_time(i),
                'is_experiment': template.get('is_experiment', False)
            })

        return plan

    def _calculate_slot_time(self, slot_index: int) -> str:
        """Calculate posting time for slot."""
        # Default schedule: 9 AM, 2 PM, 7 PM UTC
        times = ["09:00", "14:00", "19:00"]
        return times[slot_index % len(times)]


# Global instance
growth_engine = GrowthEngineService()