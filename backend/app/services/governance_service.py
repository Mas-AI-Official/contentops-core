from typing import List, Optional, Dict, Any
from sqlmodel import select, Session
from app.db import sync_engine as engine
from app.models.governance import Policy, AuditLog, ComplianceCheck

class GovernanceService:
    def check_compliance(self, content: str, entity_type: str, entity_id: str) -> ComplianceCheck:
        # Mock compliance check
        # In real impl, check against active policies using LLM or regex
        passed = True
        issues = []
        
        # Example rule: No profanity (mock)
        if "badword" in content.lower():
            passed = False
            issues.append("Contains profanity")

        check = ComplianceCheck(
            entity_type=entity_type,
            entity_id=entity_id,
            passed=passed,
            issues_json=str(issues) if issues else None,
            score=1.0 if passed else 0.0
        )
        
        with Session(engine) as session:
            session.add(check)
            session.commit()
            session.refresh(check)
            
        return check

    def log_action(self, action: str, entity_type: str, entity_id: str, user_id: str = "system", details: Optional[Dict] = None):
        log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            details_json=str(details) if details else None
        )
        with Session(engine) as session:
            session.add(log)
            session.commit()

governance_service = GovernanceService()
