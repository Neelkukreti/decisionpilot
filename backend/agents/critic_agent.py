"""
Critic Agent - Quality Validation & Health Scoring

Validates extracted decisions and action items for:
- Evidence quality (citations present and relevant)
- Clarity (unambiguous, actionable language)
- Completeness (all required fields present)
- Risk assessment (blockers, dependencies identified)

Returns:
- Quality scores (0-100)
- Validation feedback
- Execution health prediction
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import os

from .base_agent import BaseAgent
from schemas.meeting_schemas import (
    ActionItem,
    Decision,
    MeetingAnalysis,
    QualityScore,
    ValidationFeedback
)


class CriticAgent(BaseAgent):
    """Agent that validates and scores meeting outputs"""
    
    def __init__(
        self,
        model: str = "amazon.nova-lite-v1:0",
        mock_mode: bool = None
    ):
        super().__init__(
            agent_name="Critic",
            model_id=model
        )
        
        # Quality thresholds
        self.min_clarity_score = 70
        self.min_evidence_score = 60
        self.min_health_score = 50
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute critic validation on provided context"""
        # If analysis provided, score it
        if 'analysis' in context:
            return self.score_meeting_analysis(context['analysis'])
        
        # If action provided, validate it
        if 'action' in context:
            return self.validate_action_item(context['action'])
        
        # If decision provided, validate it
        if 'decision' in context:
            return self.validate_decision(context['decision'])
        
        return {"error": "No valid input provided to Critic"}
    
    def _generate_mock_output(self, prompt: str) -> Dict[str, Any]:
        """Generate mock output for testing"""
        return {
            "quality_score": 85.0,
            "validation_passed": True,
            "mock": True
        }
    
    def validate_action_item(
        self,
        action: ActionItem,
        context: Optional[str] = None
    ) -> ValidationFeedback:
        """
        Validate a single action item
        
        Returns validation feedback with scores and suggestions
        """
        if self.mock_mode:
            return self._mock_validate_action(action)
        
        # Real validation logic (would use Nova Lite)
        prompt = self._build_validation_prompt(action, context)
        response = self._call_nova(prompt)
        
        return self._parse_validation_response(response, action)
    
    def validate_decision(
        self,
        decision: Decision,
        context: Optional[str] = None
    ) -> ValidationFeedback:
        """
        Validate a single decision
        
        Checks for rationale, alternatives considered, and evidence
        """
        if self.mock_mode:
            return self._mock_validate_decision(decision)
        
        prompt = self._build_decision_validation_prompt(decision, context)
        response = self._call_nova(prompt)
        
        return self._parse_validation_response(response, decision)
    
    def score_meeting_analysis(
        self,
        analysis: MeetingAnalysis
    ) -> Dict[str, Any]:
        """
        Score entire meeting analysis
        
        Returns:
        - Overall health score
        - Per-action scores
        - Per-decision scores
        - Risk flags
        - Execution recommendations
        """
        if self.mock_mode:
            return self._mock_score_analysis(analysis)
        
        # Validate all actions
        action_validations = [
            self.validate_action_item(action)
            for action in analysis.action_items
        ]
        
        # Validate all decisions
        decision_validations = [
            self.validate_decision(decision)
            for decision in analysis.decisions
        ]
        
        # Calculate aggregate scores
        avg_action_score = sum(
            v.quality_score.overall for v in action_validations
        ) / len(action_validations) if action_validations else 0
        
        avg_decision_score = sum(
            v.quality_score.overall for v in decision_validations
        ) / len(decision_validations) if decision_validations else 0
        
        # Calculate execution health
        health_score = self._calculate_health_score(
            action_validations,
            decision_validations,
            analysis.risks
        )
        
        return {
            "health_score": health_score,
            "action_quality": avg_action_score,
            "decision_quality": avg_decision_score,
            "action_validations": action_validations,
            "decision_validations": decision_validations,
            "risk_count": len(analysis.risks),
            "execution_ready": health_score >= self.min_health_score,
            "recommendations": self._generate_recommendations(
                health_score,
                action_validations,
                decision_validations
            )
        }
    
    def _calculate_health_score(
        self,
        action_validations: List[ValidationFeedback],
        decision_validations: List[ValidationFeedback],
        risks: List[str]
    ) -> float:
        """
        Calculate execution health score (0-100)
        
        Factors:
        - Action item quality (40%)
        - Decision quality (30%)
        - Risk exposure (20%)
        - Completeness (10%)
        """
        # Action quality (40%)
        action_score = sum(
            v.quality_score.overall for v in action_validations
        ) / len(action_validations) if action_validations else 0
        action_weight = action_score * 0.4
        
        # Decision quality (30%)
        decision_score = sum(
            v.quality_score.overall for v in decision_validations
        ) / len(decision_validations) if decision_validations else 0
        decision_weight = decision_score * 0.3
        
        # Risk exposure (20%) - penalize high risk count
        risk_penalty = min(len(risks) * 5, 20)  # -5 points per risk, max -20
        risk_weight = (20 - risk_penalty)
        
        # Completeness (10%) - check for missing owners, dates, etc.
        completeness = self._check_completeness(action_validations)
        completeness_weight = completeness * 0.1
        
        total = action_weight + decision_weight + risk_weight + completeness_weight
        
        return round(total, 2)
    
    def _check_completeness(
        self,
        validations: List[ValidationFeedback]
    ) -> float:
        """Check if action items have all required fields"""
        if not validations:
            return 0
        
        complete_count = sum(
            1 for v in validations
            if not any([
                "missing owner" in issue.lower()
                or "missing deadline" in issue.lower()
                for issue in v.issues
            ])
        )
        
        return (complete_count / len(validations)) * 100
    
    def _generate_recommendations(
        self,
        health_score: float,
        action_validations: List[ValidationFeedback],
        decision_validations: List[ValidationFeedback]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if health_score < self.min_health_score:
            recommendations.append(
                f"⚠️ Execution health below threshold ({health_score:.1f}/100). "
                "Review action items before creating tickets."
            )
        
        # Check for low-quality actions
        low_quality_actions = [
            v for v in action_validations
            if v.quality_score.overall < self.min_clarity_score
        ]
        
        if low_quality_actions:
            recommendations.append(
                f"📝 {len(low_quality_actions)} action item(s) need clarity improvements. "
                "Review suggestions below."
            )
        
        # Check for missing evidence
        weak_evidence = [
            v for v in action_validations + decision_validations
            if v.quality_score.evidence_quality < self.min_evidence_score
        ]
        
        if weak_evidence:
            recommendations.append(
                f"🔍 {len(weak_evidence)} item(s) lack strong evidence. "
                "Consider adding citations from meeting transcript."
            )
        
        if health_score >= 80:
            recommendations.append(
                "✅ High execution health. Ready for automated ticket creation."
            )
        
        return recommendations
    
    def _build_validation_prompt(
        self,
        action: ActionItem,
        context: Optional[str]
    ) -> str:
        """Build validation prompt for Nova Lite"""
        return f"""Validate this action item for quality and clarity:

ACTION ITEM:
- ID: {action.id}
- Title: {action.title}
- Description: {action.description}
- Owner: {action.owner or 'Not assigned'}
- Deadline: {action.deadline or 'Not set'}
- Citations: {len(action.citations)} source(s)

CONTEXT:
{context or 'No additional context'}

EVALUATE:
1. Clarity (0-100): Is the action unambiguous and specific?
2. Evidence (0-100): Are there sufficient citations from the meeting?
3. Actionability (0-100): Can this be executed immediately?
4. Completeness: Are owner and deadline specified?

OUTPUT (JSON):
{{
    "clarity_score": <int>,
    "evidence_score": <int>,
    "actionability_score": <int>,
    "overall_score": <int>,
    "issues": [<list of specific problems>],
    "suggestions": [<list of improvements>]
}}
"""
    
    def _build_decision_validation_prompt(
        self,
        decision: Decision,
        context: Optional[str]
    ) -> str:
        """Build validation prompt for decisions"""
        return f"""Validate this decision for quality:

DECISION:
- ID: {decision.id}
- Title: {decision.title}
- Description: {decision.description}
- Rationale: {decision.rationale or 'Not provided'}
- Owner: {decision.owner or 'Not assigned'}
- Citations: {len(decision.citations)} source(s)

CONTEXT:
{context or 'No additional context'}

EVALUATE:
1. Clarity: Is the decision clear and unambiguous?
2. Rationale: Is there a clear explanation of why?
3. Evidence: Are there meeting citations supporting this?
4. Impact: Are alternatives or tradeoffs mentioned?

OUTPUT (JSON):
{{
    "clarity_score": <int>,
    "evidence_score": <int>,
    "rationale_quality": <int>,
    "overall_score": <int>,
    "issues": [<list of problems>],
    "suggestions": [<list of improvements>]
}}
"""
    
    def _mock_validate_action(self, action: ActionItem) -> ValidationFeedback:
        """Mock validation for testing"""
        # Simulate quality scoring
        clarity = 85 if action.description else 50
        evidence = len(action.citations) * 20  # 20 points per citation
        evidence = min(evidence, 100)
        
        issues = []
        suggestions = []
        
        if not action.owner:
            issues.append("Missing owner assignment")
            suggestions.append("Assign a specific team member")
            clarity -= 10
        
        if not action.deadline:
            issues.append("No deadline specified")
            suggestions.append("Add target completion date")
            clarity -= 10
        
        if len(action.citations) < 2:
            issues.append("Weak evidence (fewer than 2 citations)")
            suggestions.append("Link to specific meeting moments")
        
        overall = (clarity + evidence) / 2
        
        return ValidationFeedback(
            item_id=action.id,
            item_type="action",
            quality_score=QualityScore(
                clarity=clarity,
                evidence_quality=evidence,
                overall=round(overall, 2)
            ),
            issues=issues,
            suggestions=suggestions,
            validated_at=datetime.now().isoformat()
        )
    
    def _mock_validate_decision(self, decision: Decision) -> ValidationFeedback:
        """Mock decision validation"""
        clarity = 80 if decision.description else 40
        evidence = len(decision.citations) * 25
        evidence = min(evidence, 100)
        
        rationale_score = 90 if decision.rationale else 30
        
        issues = []
        suggestions = []
        
        if not decision.rationale:
            issues.append("Missing decision rationale")
            suggestions.append("Explain why this decision was made")
            clarity -= 20
        
        if not decision.owner:
            issues.append("No decision owner assigned")
            suggestions.append("Assign someone accountable")
        
        if len(decision.citations) == 0:
            issues.append("No meeting citations")
            suggestions.append("Link to discussion in meeting")
        
        overall = (clarity + evidence + rationale_score) / 3
        
        return ValidationFeedback(
            item_id=decision.id,
            item_type="decision",
            quality_score=QualityScore(
                clarity=clarity,
                evidence_quality=evidence,
                overall=round(overall, 2)
            ),
            issues=issues,
            suggestions=suggestions,
            validated_at=datetime.now().isoformat()
        )
    
    def _mock_score_analysis(
        self,
        analysis: MeetingAnalysis
    ) -> Dict[str, Any]:
        """Mock scoring for entire analysis"""
        # Validate all items
        action_validations = [
            self._mock_validate_action(action)
            for action in analysis.action_items
        ]
        
        decision_validations = [
            self._mock_validate_decision(decision)
            for decision in analysis.decisions
        ]
        
        # Calculate scores
        avg_action = sum(
            v.quality_score.overall for v in action_validations
        ) / len(action_validations) if action_validations else 0
        
        avg_decision = sum(
            v.quality_score.overall for v in decision_validations
        ) / len(decision_validations) if decision_validations else 0
        
        health = self._calculate_health_score(
            action_validations,
            decision_validations,
            analysis.risks
        )
        
        return {
            "health_score": health,
            "action_quality": round(avg_action, 2),
            "decision_quality": round(avg_decision, 2),
            "action_validations": action_validations,
            "decision_validations": decision_validations,
            "risk_count": len(analysis.risks),
            "execution_ready": health >= self.min_health_score,
            "recommendations": self._generate_recommendations(
                health,
                action_validations,
                decision_validations
            )
        }
