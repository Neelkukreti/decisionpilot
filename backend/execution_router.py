"""
Execution Router — Routes scored items to AUTO / REVIEW / CLARIFY.

AUTO   (≥ 0.80): Execute immediately → Jira REST API
REVIEW (0.65–0.79): Human 1-click approval queue
CLARIFY (< 0.65): Generate clarifying question, block execution

Each routed item carries:
  - routing_band
  - routing_justification (shown to user)
  - clarifying_question (for CLARIFY items)
  - suggested_edits (for REVIEW items)
  - undo_window_seconds (for AUTO items)
"""

import time
import random
import string
import os
from typing import Dict, List, Any, Optional

try:
    import requests
    from requests.auth import HTTPBasicAuth
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


AUTO_THRESHOLD    = 0.80   # lowered from 0.85 to populate REVIEW band
REVIEW_THRESHOLD  = 0.65


def _jira_priority(priority: str) -> str:
    """Map internal priority to Jira priority name."""
    return {"high": "High", "medium": "Medium", "low": "Low"}.get(priority, "Medium")


class JiraClient:
    """Thin wrapper around the Jira REST API v3."""

    def __init__(self, base_url: str, email: str, api_token: str, project_key: str):
        self.base_url    = base_url.rstrip("/")
        self.auth        = HTTPBasicAuth(email, api_token)
        self.project_key = project_key
        self.headers     = {"Accept": "application/json", "Content-Type": "application/json"}

    def create_issue(self, title: str, description: str, owner: Optional[str],
                     deadline: Optional[str], priority: str = "Medium") -> Dict:
        """
        Create a Jira issue and return {ticket_id, ticket_url, status}.
        Raises on HTTP error.
        """
        body = {
            "fields": {
                "project":   {"key": self.project_key},
                "summary":   title,
                "issuetype": {"name": "Task"},
                "priority":  {"name": priority},
                "description": {
                    "type":    "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                }
            }
        }

        # Add due date if we have one (Jira format: YYYY-MM-DD)
        if deadline and len(deadline) == 10 and deadline[4] == "-":
            body["fields"]["duedate"] = deadline

        url = f"{self.base_url}/rest/api/3/issue"
        resp = requests.post(url, json=body, auth=self.auth, headers=self.headers, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        issue_key = data["key"]
        return {
            "ticket_id":  issue_key,
            "ticket_url": f"{self.base_url}/browse/{issue_key}",
            "status":     "created",
        }

    def health_check(self) -> bool:
        """Returns True if Jira credentials are valid."""
        try:
            url = f"{self.base_url}/rest/api/3/myself"
            resp = requests.get(url, auth=self.auth, headers=self.headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False


class ExecutionRouter:
    """
    Routes action items to execution bands and handles Jira ticket creation.
    Falls back to mock mode if Jira env vars are missing.
    """

    def __init__(self, jira_config: Optional[Dict] = None):
        # Build Jira client from env vars (preferred) or explicit config
        jira_url    = os.getenv("JIRA_URL")    or (jira_config or {}).get("base_url")
        jira_email  = os.getenv("JIRA_EMAIL")  or (jira_config or {}).get("email")
        jira_token  = os.getenv("JIRA_API_TOKEN") or (jira_config or {}).get("api_token")
        project_key = os.getenv("JIRA_PROJECT_KEY") or (jira_config or {}).get("project_key", "DP")

        self._mock = True
        self._jira: Optional[JiraClient] = None
        self._project_key = project_key

        if _REQUESTS_AVAILABLE and jira_url and jira_email and jira_token:
            client = JiraClient(jira_url, jira_email, jira_token, project_key)
            if client.health_check():
                self._jira = client
                self._mock = False
                print(f"✓ Jira connected: {jira_url} (project: {project_key})")
            else:
                print(f"⚠️  Jira credentials invalid — falling back to mock tickets")
        else:
            missing = []
            if not jira_url:    missing.append("JIRA_URL")
            if not jira_email:  missing.append("JIRA_EMAIL")
            if not jira_token:  missing.append("JIRA_API_TOKEN")
            if missing:
                print(f"⚠️  Jira mock mode — missing env vars: {', '.join(missing)}")

    @property
    def is_live(self) -> bool:
        return not self._mock

    def route_batch(self, scored_items: List[Dict]) -> Dict[str, Any]:
        routed = []
        for item in scored_items:
            routed_item = self._route_item(item)
            routed.append(routed_item)

        auto_items    = [i for i in routed if i["routing"]["band"] == "AUTO"]
        review_items  = [i for i in routed if i["routing"]["band"] == "REVIEW"]
        clarify_items = [i for i in routed if i["routing"]["band"] == "CLARIFY"]

        return {
            "routed_items": routed,
            "summary": {
                "auto":    len(auto_items),
                "review":  len(review_items),
                "clarify": len(clarify_items),
                "total":   len(routed),
            },
            "jira_live": self.is_live,
        }

    def _route_item(self, item: Dict) -> Dict:
        scoring    = item.get("scoring", {})
        gate       = item.get("gate", {})
        confidence = scoring.get("confidence_adjusted", 0.0)
        band       = scoring.get("routing_band", "CLARIFY")

        # Re-compute band using updated thresholds
        if confidence >= AUTO_THRESHOLD:
            band = "AUTO"
        elif confidence >= REVIEW_THRESHOLD:
            band = "REVIEW"
        else:
            band = "CLARIFY"

        justification = scoring.get("routing_justification", "")

        routing = {
            "band":       band,
            "confidence": confidence,
            "justification": justification,
            "timestamp":  time.time(),
        }

        if band == "AUTO":
            ticket = self._execute_auto(item)
            return {
                **item,
                "routing": {
                    **routing,
                    "undo_window_seconds": 30,
                    "auto_executed": True,
                    "jira_live": self.is_live,
                },
                "ticket": ticket,
            }

        elif band == "REVIEW":
            suggested_edits = self._generate_suggested_edits(item, gate)
            return {
                **item,
                "routing": {
                    **routing,
                    "auto_executed": False,
                    "requires_approval": True,
                    "suggested_edits": suggested_edits,
                },
                "ticket": None,
            }

        else:  # CLARIFY
            clarifying_question = self._generate_clarifying_question(item, gate)
            return {
                **item,
                "routing": {
                    **routing,
                    "auto_executed": False,
                    "requires_approval": False,
                    "clarifying_question": clarifying_question,
                    "blocked_reasons": gate.get("failure_reasons", []),
                },
                "ticket": None,
            }

    def _build_description(self, item: Dict) -> str:
        parts = []
        if item.get("verbatim_quote"):
            parts.append(f'Source quote: "{item["verbatim_quote"]}"')
        if item.get("citation"):
            parts.append(f"Citation: {item['citation']}")
        if item.get("routing_justification"):
            parts.append(f"Confidence: {item.get('routing_confidence', 0):.0%} — {item['routing_justification']}")
        parts.append("Created automatically by DecisionPilot.")
        return "\n\n".join(parts)

    def _execute_auto(self, item: Dict) -> Dict:
        """Create Jira ticket — real API if configured, mock otherwise."""
        start = time.time()

        if self._jira:
            try:
                desc   = self._build_description(item)
                result = self._jira.create_issue(
                    title       = item.get("title", "Untitled action item"),
                    description = desc,
                    owner       = item.get("owner"),
                    deadline    = item.get("deadline"),
                    priority    = _jira_priority(item.get("priority", "medium")),
                )
                elapsed = int((time.time() - start) * 1000)
                return {
                    **result,
                    "execution_method":  "jira_rest_api",
                    "execution_time_ms": elapsed,
                    "created_at":        time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "mock": False,
                }
            except Exception as e:
                print(f"⚠️  Jira API error for '{item.get('title')}': {e} — falling back to mock")

        # Mock fallback
        time.sleep(random.uniform(0.10, 0.25))
        elapsed = int((time.time() - start) * 1000)
        ticket_id = f"{self._project_key}-{random.randint(200, 999)}"
        return {
            "ticket_id":          ticket_id,
            "ticket_url":         f"https://jira.example.com/browse/{ticket_id}",
            "status":             "created",
            "execution_method":   "mock",
            "execution_time_ms":  elapsed,
            "created_at":         time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mock": True,
        }

    def _generate_suggested_edits(self, item: Dict, gate: Dict) -> List[Dict]:
        edits = []
        checks = gate.get("checks", {})

        if not checks.get("has_deadline", {}).get("pass"):
            edits.append({
                "field":      "deadline",
                "current":    item.get("deadline"),
                "suggestion": "Add a specific date (e.g., 2026-03-20)",
                "reason":     "No deadline — high risk of non-completion"
            })

        if not checks.get("has_resolved_owner", {}).get("pass"):
            edits.append({
                "field":      "owner",
                "current":    item.get("owner"),
                "suggestion": "Assign to a specific person",
                "reason":     "Ownership ambiguity — ticket may sit unworked"
            })

        if not checks.get("has_action_verb", {}).get("pass"):
            original = item.get("title", "")
            edits.append({
                "field":      "title",
                "current":    original,
                "suggestion": f"Deploy/Update/Create {original.lower()}",
                "reason":     "No imperative verb — Jira titles should start with an action"
            })

        return edits

    def _generate_clarifying_question(self, item: Dict, gate: Dict) -> str:
        checks          = gate.get("checks", {})
        failure_reasons = gate.get("failure_reasons", [])
        title           = item.get("title", "this action")

        if not checks.get("has_resolved_owner", {}).get("pass"):
            owner_text = item.get("owner") or "someone"
            return f"Who specifically is responsible for '{title}'? ('{owner_text}' is too ambiguous to assign a ticket.)"

        if not checks.get("has_evidence_citation", {}).get("pass"):
            return f"Was '{title}' actually committed to in this meeting, or is it a suggestion? No direct quote was found."

        cond = checks.get("no_conditional_language", {})
        if not cond.get("pass") and cond.get("phrases_found"):
            phrase = cond["phrases_found"][0]
            return f"The commitment '{title}' depends on '{phrase}'. Has that condition been resolved?"

        hedge = checks.get("no_hedge_words", {})
        if not hedge.get("pass") and hedge.get("words_found"):
            word = hedge["words_found"][0]
            return f"'{title}' uses '{word}' — is this a confirmed commitment or just a possibility?"

        if failure_reasons:
            return f"Before creating a ticket: {failure_reasons[0]}"

        return f"Can you confirm '{title}' was an explicit commitment, not a discussion point?"
