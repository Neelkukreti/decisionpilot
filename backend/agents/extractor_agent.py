"""
Extractor Agent - Extracts structured data with evidence citations
"""

from typing import Dict, Any
from .base_agent import BaseAgent, AgentResponse


class ExtractorAgent(BaseAgent):
    """Extracts decisions, actions, risks from evidence"""
    
    def __init__(self):
        super().__init__(agent_name="Extractor", model_id='amazon.nova-lite-v1:0')
        
    def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Extract structured information from evidence
        
        Args:
            context: {
                'evidence_chunks': List[Dict] - Evidence with citations
            }
        """
        
        evidence = context.get('evidence_chunks', [])
        
        system_prompt = """You are a precise meeting action-item extraction agent.

CRITICAL RULES:
1. Output ONLY valid JSON — no markdown, no preamble
2. EVERY action item must cite evidence using [citation_id]
3. NO hallucination — if not explicitly stated, leave field null
4. SPEAKER ATTRIBUTION: When a speaker says "I will X" or "I'll X", the OWNER is that speaker's name.
   - "Sarah Chen: I will deploy..." → owner = "Sarah Chen"
   - "John: I'll update..." → owner = "John"
   - "Someone should..." → owner = null (unresolvable)
5. DEADLINE extraction: Convert "this Friday", "by March 7th", "end of next week" to ISO dates when possible.
   Today is 2026-03-04.
6. Only extract COMMITMENTS — things someone said they WILL do, not suggestions or wishes.

Output schema:
{
  "summary": "1-sentence summary [1]",
  "decisions": [
    {
      "decision_id": "DEC-001",
      "description": "What was decided [citation]",
      "decision_maker": "Name or group",
      "rationale": "Why [citation]",
      "citations": ["[1]"],
      "confidence": 0.95
    }
  ],
  "action_items": [
    {
      "action_id": "ACT-001",
      "description": "Imperative verb + specific task — NO citation markers in description",
      "owner": "Full name of person who committed (or null if unresolvable)",
      "deadline": "YYYY-MM-DD or relative string or null",
      "priority": "high|medium|low",
      "context": "Why this task matters [citation]",
      "citations": ["[1]"],
      "clarity_score": 0.8,
      "evidence_score": 0.9,
      "confidence": 0.85
    }
  ],
  "risks": [
    {
      "risk_id": "RISK-001",
      "description": "Risk description [citation]",
      "severity": "high|medium|low",
      "mitigation": "Suggested mitigation or null",
      "owner": "Name or null",
      "citations": ["[1]"],
      "confidence": 0.8
    }
  ],
  "open_questions": [
    {
      "question_id": "Q-001",
      "question": "Unresolved question [citation]",
      "asker": "Name or null",
      "requires_followup": true,
      "citations": ["[1]"]
    }
  ]
}"""

        # Format evidence for prompt
        evidence_text = "\n\n".join([
            f"{e.get('citation_id', '[?]')} [{e.get('source', 'unknown')}]: {e.get('content', '')}"
            for e in evidence
        ])
        
        user_prompt = f"""Extract structured information from this evidence.

Evidence:
{evidence_text}

Output ONLY the JSON object:"""

        return self.invoke(user_prompt, system_prompt, temperature=0.0, max_tokens=3000)
    
    def _generate_mock_output(self, prompt: str) -> Dict[str, Any]:
        """Generate mock extraction for testing"""
        return {
            "summary": "Team discussed API authentication and deployment timeline [1][2]",
            "decisions": [
                {
                    "decision_id": "DEC-001",
                    "description": "Use Auth0 for OAuth2 implementation [1]",
                    "decision_maker": "Sarah",
                    "rationale": "Auth0 provides enterprise features and compliance [1]",
                    "citations": ["[1]"],
                    "confidence": 0.95
                }
            ],
            "action_items": [
                {
                    "action_id": "ACT-001",
                    "description": "Deploy authentication service to production [2]",
                    "owner": "Mike",
                    "deadline": "2026-03-05",
                    "priority": "high",
                    "context": "Required for security audit completion [2]",
                    "citations": ["[2]"],
                    "clarity_score": 0.85,
                    "evidence_score": 0.75,
                    "confidence": 0.90
                },
                {
                    "action_id": "ACT-002",
                    "description": "Update API documentation with Auth0 integration [3]",
                    "owner": "Sarah",
                    "deadline": None,
                    "priority": "medium",
                    "context": "Help developers integrate with new auth [3]",
                    "citations": ["[3]"],
                    "clarity_score": 0.70,
                    "evidence_score": 0.60,
                    "confidence": 0.75
                }
            ],
            "risks": [
                {
                    "risk_id": "RISK-001",
                    "description": "Auth0 migration may cause downtime [4]",
                    "severity": "medium",
                    "mitigation": "Deploy during maintenance window",
                    "owner": "Mike",
                    "citations": ["[4]"],
                    "confidence": 0.80
                }
            ],
            "open_questions": [
                {
                    "question_id": "Q-001",
                    "question": "Which Auth0 pricing tier should we choose? [5]",
                    "asker": "John",
                    "requires_followup": True,
                    "citations": ["[5]"]
                }
            ]
        }
