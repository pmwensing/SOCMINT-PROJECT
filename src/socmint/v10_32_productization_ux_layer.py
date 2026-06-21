# v10.32 Productization / UX Layer

"""
This module adds the first set of UX improvements and productization helpers over v10.31:
- Enhanced case/dashboard summaries
- Operator hints for next actions
- Navigation helpers
- Minor dashboard polish
"""

from copy import deepcopy


class ProductizationUX:
    def __init__(self, case_id: str, registry: dict):
        self.case_id = case_id
        self.registry = deepcopy(registry or {})

    def enhanced_summary(self) -> dict:
        deliveries = self.registry.get("deliveries", [])
        return {
            "case_id": self.case_id,
            "delivery_count": len(deliveries),
            "latest_delivery_id": self.registry.get("latest_delivery_id"),
            "latest_readiness": self.registry.get("latest_readiness"),
            "navigation_hints": self._navigation_hints(),
        }

    def _navigation_hints(self) -> list[str]:
        readiness = self.registry.get("latest_readiness", "unknown")
        hints = []
        if readiness == "ready":
            hints.append("Proceed to human approval")
        elif readiness == "review_required":
            hints.append("Review flagged items")
        else:
            hints.append("Investigate blocked deliveries")
        return hints

    def ui_polish(self) -> dict:
        return {
            "highlighted_actions": self._navigation_hints(),
            "summary_card_color": "green"
            if self.registry.get("latest_readiness") == "ready"
            else "yellow",
        }
