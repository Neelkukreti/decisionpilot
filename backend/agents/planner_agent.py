"""
Planner Agent - Creates execution plans for meeting analysis
"""

from typing import Dict, Any
from .base_agent import BaseAgent, AgentResponse


class PlannerAgent(BaseAgent):
    """Creates strategic execution plans"""
    
    def __init__(self):
        super().__init__(agent_name="Planner", model_id='amazon.nova-lite-v1')
        
    def execute(self, context: Dict[str, Any]) -> AgentResponse:
        """
        Create execution plan for meeting analysis
        
        Args:
            context: {
                'meeting_summary': str - Brief summary of meeting
                'user_goal': str - What user wants to accomplish
            }
        """
        
        meeting_summary = context.get('meeting_summary', '')
        user_goal = context.get('user_goal', 'Extract and execute action items')
        
        system_prompt = """You are a strategic planning agent for meeting analysis.
Create an optimal execution plan in STRICT JSON format.

Available tools:
- retrieve_decisions: Search for decisions
- retrieve_tasks: Search for action items
- retrieve_risks: Search for blockers/risks
- extract_structured: Parse into JSON
- validate_quality: Check quality
- execute_jira: Create Jira issues

Output ONLY this JSON structure:
{
  "plan_steps": [
    {
      "step_id": 1,
      "action": "tool_name",
      "query": "specific query",
      "reasoning": "why needed",
      "depends_on": [],
      "estimated_duration_sec": 2.0
    }
  ],
  "estimated_total_duration_sec": 10.0,
  "risk_assessment": "low|medium|high",
  "complexity_score": 0.5
}"""

        user_prompt = f"""Meeting Summary: {meeting_summary}
User Goal: {user_goal}

Create execution plan (JSON only):"""

        return self.invoke(user_prompt, system_prompt, temperature=0.2)
    
    def _generate_mock_output(self, prompt: str) -> Dict[str, Any]:
        """Generate mock plan for testing"""
        return {
            "plan_steps": [
                {
                    "step_id": 1,
                    "action": "retrieve_decisions",
                    "query": "What decisions were made?",
                    "reasoning": "Need decision context",
                    "depends_on": [],
                    "estimated_duration_sec": 2.0
                },
                {
                    "step_id": 2,
                    "action": "retrieve_tasks",
                    "query": "What action items were assigned?",
                    "reasoning": "Extract actionable tasks",
                    "depends_on": [1],
                    "estimated_duration_sec": 2.0
                },
                {
                    "step_id": 3,
                    "action": "extract_structured",
                    "query": "",
                    "reasoning": "Convert to structured format",
                    "depends_on": [1, 2],
                    "estimated_duration_sec": 5.0
                },
                {
                    "step_id": 4,
                    "action": "validate_quality",
                    "query": "",
                    "reasoning": "Ensure quality before execution",
                    "depends_on": [3],
                    "estimated_duration_sec": 3.0
                }
            ],
            "estimated_total_duration_sec": 12.0,
            "risk_assessment": "low",
            "complexity_score": 0.6
        }
