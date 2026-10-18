"""Compatibility boundary for the retired password-based LinkedIn publisher.

Use a supported, authenticated social connector or official OAuth adapter.
Keeping these public method signatures makes an old caller fail explicitly
instead of logging in with a password or reporting publication without a post ID.
"""


class LinkedInPublisher:
    def __init__(self, account_id: str = "masoud"):
        self.account_id = account_id

    def is_configured(self) -> bool:
        return False

    def _blocked(self) -> dict:
        return {
            "status": "blocked",
            "platform": "linkedin",
            "account": self.account_id,
            "error": "supported_connection_required",
            "detail": "Use an authenticated supported connector or official OAuth adapter; "
                      "password publication is retired. No post was submitted.",
        }

    def publish_text_post(self, text: str, visibility: str = "PUBLIC") -> dict:
        return self._blocked()

    def publish_image_post(self, text: str, image_path: str, title: str = "") -> dict:
        return self._blocked()

    def publish_video_post(self, text: str, video_path: str, title: str = "") -> dict:
        return self._blocked()

    def get_profile(self) -> dict:
        return self._blocked()
