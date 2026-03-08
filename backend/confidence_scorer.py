"""
Confidence Scorer — 5-dimension weighted scoring per action item.

Dimensions (must sum to 1.0):
  action_clarity      0.25
  ownership_certainty 0.25
  evidence_strength   0.20
  deadline_clarity    0.15
  ambiguity_penalty   0.15

Composite = weighted sum, then damped by gate_score:
  confidence_adjusted = composite * (0.5 + 0.5 * gate_score)

This means a perfect-gate item keeps full confidence;
a failed-gate (score 0.43) pulls the composite down by ~28%.
"""

import re
from typing import Dict, List, Any, Optional


WEIGHT_ACTION_CLARITY      = 0.25
WEIGHT_OWNERSHIP_CERTAINTY = 0.25
WEIGHT_EVIDENCE_STRENGTH   = 0.20
WEIGHT_DEADLINE_CLARITY    = 0.15
WEIGHT_AMBIGUITY_PENALTY   = 0.15

ACTION_VERBS_STRONG = [
    "deploy", "ship", "build", "implement", "create", "fix", "launch",
    "release", "submit", "finalize", "approve", "migrate", "configure"
]
ACTION_VERBS_MODERATE = [
    "update", "write", "review", "test", "schedule", "notify", "send",
    "complete", "document", "present", "coordinate", "confirm", "validate",
    "define", "prepare", "integrate", "refactor", "setup", "publish"
]

HEDGE_WORDS = [
    "maybe", "perhaps", "probably", "might", "could", "possibly",
    "sort of", "kind of", "i think", "we should consider",
    "might want to", "could potentially", "would be nice",
    "at some point", "eventually", "hopefully", "ideally"
]


class ConfidenceScorer:
    """
    Computes a 5-dimension confidence score for each action item.
    Uses only the extracted item data + gate result — no LLM calls.
    """

    def score(self, item: Dict[str, Any], gate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score a single item. Returns full scoring breakdown + composite.

        Args:
            item: Extracted action item dict
            gate: Gate result dict from QualityGateAgent.evaluate()

        Returns:
            {
              dimensions: {name: {score, weight, weighted, rationale}},
              composite: float,
              gate_score: float,
              confidence_adjusted: float,
              routing_band: "AUTO" | "REVIEW" | "CLARIFY",
              routing_justification: str
            }
        """
        title       = item.get("title", "") or ""
        description = item.get("description", title) or ""
        owner       = (item.get("owner") or "").strip()
        deadline    = item.get("deadline")
        citations   = item.get("citations") or item.get("citation") or []
        if isinstance(citations, str):
            citations = [citations] if citations else []
        owner_confidence = float(item.get("owner_confidence", 0.5))
        gate_score = gate.get("gate_score", 0.5)
        checks = gate.get("checks", {})

        # ── Dimension 1: Action Clarity ───────────────────────────────────
        ac = self._score_action_clarity(title, description, checks)

        # ── Dimension 2: Ownership Certainty ─────────────────────────────
        oc = self._score_ownership_certainty(owner, owner_confidence, checks)

        # ── Dimension 3: Evidence Strength ────────────────────────────────
        ev = self._score_evidence_strength(citations, item)

        # ── Dimension 4: Deadline Clarity ─────────────────────────────────
        dl = self._score_deadline_clarity(deadline, checks)

        # ── Dimension 5: Ambiguity Penalty ────────────────────────────────
        ap = self._score_ambiguity_penalty(title, description, checks)

        dimensions = {
            "action_clarity":      {**ac, "weight": WEIGHT_ACTION_CLARITY,      "weighted": round(ac["score"] * WEIGHT_ACTION_CLARITY, 4)},
            "ownership_certainty": {**oc, "weight": WEIGHT_OWNERSHIP_CERTAINTY, "weighted": round(oc["score"] * WEIGHT_OWNERSHIP_CERTAINTY, 4)},
            "evidence_strength":   {**ev, "weight": WEIGHT_EVIDENCE_STRENGTH,   "weighted": round(ev["score"] * WEIGHT_EVIDENCE_STRENGTH, 4)},
            "deadline_clarity":    {**dl, "weight": WEIGHT_DEADLINE_CLARITY,     "weighted": round(dl["score"] * WEIGHT_DEADLINE_CLARITY, 4)},
            "ambiguity_penalty":   {**ap, "weight": WEIGHT_AMBIGUITY_PENALTY,   "weighted": round(ap["score"] * WEIGHT_AMBIGUITY_PENALTY, 4)},
        }

        composite = sum(d["weighted"] for d in dimensions.values())
        composite = round(min(1.0, max(0.0, composite)), 4)

        # Gate damping: perfect gate (1.0) = no change; zero gate = 50% reduction
        gate_damping = 0.5 + 0.5 * gate_score
        confidence_adjusted = round(composite * gate_damping, 4)

        # Override: if gate has a routing_override, respect it
        routing_override = gate.get("routing_override")

        if routing_override == "CLARIFY":
            routing_band = "CLARIFY"
        elif routing_override == "REVIEW":
            routing_band = "REVIEW"
        elif confidence_adjusted >= 0.85:
            routing_band = "AUTO"
        elif confidence_adjusted >= 0.65:
            routing_band = "REVIEW"
        else:
            routing_band = "CLARIFY"

        routing_justification = self._build_justification(
            routing_band, confidence_adjusted, dimensions, gate
        )

        return {
            "dimensions": dimensions,
            "composite": composite,
            "gate_score": gate_score,
            "confidence_adjusted": confidence_adjusted,
            "routing_band": routing_band,
            "routing_justification": routing_justification,
        }

    # ── Dimension scorers ─────────────────────────────────────────────────

    def _score_action_clarity(self, title: str, description: str, checks: Dict) -> Dict:
        text = (title + " " + description).lower()

        if not checks.get("has_action_verb", {}).get("pass"):
            return {"score": 0.2, "rationale": "No imperative action verb found — statement is not directive"}

        verb = checks.get("has_action_verb", {}).get("value", "")
        if verb in ACTION_VERBS_STRONG:
            # Strong verb + specific object = high clarity
            word_count = len(title.split())
            if word_count >= 5:
                return {"score": 0.95, "rationale": f"Strong imperative verb '{verb}' with specific object"}
            return {"score": 0.85, "rationale": f"Strong verb '{verb}', object could be more specific"}
        elif verb in ACTION_VERBS_MODERATE:
            word_count = len(title.split())
            score = 0.78 if word_count >= 5 else 0.65
            return {"score": score, "rationale": f"Moderate verb '{verb}' — clear direction"}
        else:
            return {"score": 0.55, "rationale": f"Weak or passive phrasing near verb '{verb}'"}

    def _score_ownership_certainty(self, owner: str, owner_confidence: float, checks: Dict) -> Dict:
        if not checks.get("has_resolved_owner", {}).get("pass"):
            if not owner or owner.lower() in ("", "tbd", "team", "everyone", "we", "someone"):
                return {"score": 0.0, "rationale": f"Owner '{owner}' is unresolvable"}
            return {"score": 0.3, "rationale": f"Owner name present but confidence low ({owner_confidence:.0%})"}

        # Resolved owner
        if owner_confidence >= 0.9:
            return {"score": 0.98, "rationale": f"Owner '{owner}' confirmed by speaker diarization"}
        elif owner_confidence >= 0.75:
            return {"score": 0.85, "rationale": f"Owner '{owner}' resolved (confidence {owner_confidence:.0%})"}
        else:
            return {"score": 0.70, "rationale": f"Owner '{owner}' resolved with moderate confidence ({owner_confidence:.0%})"}

    def _score_evidence_strength(self, citations: List, item: Dict) -> Dict:
        corroborating = item.get("corroborating_citations", [])
        n_citations = len([c for c in citations if c])
        n_corroborating = len(corroborating)

        if n_citations == 0:
            return {"score": 0.1, "rationale": "No evidence citations — cannot verify commitment was made"}
        elif n_citations >= 1 and n_corroborating >= 1:
            return {"score": 0.95, "rationale": f"Primary citation + {n_corroborating} corroborating source(s)"}
        elif n_citations >= 2:
            return {"score": 0.80, "rationale": f"{n_citations} citations from same source type"}
        else:
            return {"score": 0.65, "rationale": "Single citation — no cross-source verification"}

    def _score_deadline_clarity(self, deadline, checks: Dict) -> Dict:
        if not checks.get("has_deadline", {}).get("pass"):
            return {"score": 0.05, "rationale": "No deadline — untracked commitments fail 70% of the time"}

        deadline_str = str(deadline).strip().lower()

        # Absolute date pattern: YYYY-MM-DD or "March 7" style
        if re.search(r'\d{4}-\d{2}-\d{2}', deadline_str):
            return {"score": 1.0, "rationale": f"Absolute date: {deadline}"}
        elif re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d+', deadline_str):
            return {"score": 0.92, "rationale": f"Near-absolute date: {deadline}"}
        elif any(w in deadline_str for w in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            return {"score": 0.80, "rationale": f"Day-of-week deadline (resolvable): {deadline}"}
        elif any(w in deadline_str for w in ["eow", "end of week", "this week", "next week", "eom", "end of month"]):
            return {"score": 0.72, "rationale": f"Relative but resolvable: {deadline}"}
        elif any(w in deadline_str for w in ["q1", "q2", "q3", "q4", "sprint", "next sprint"]):
            return {"score": 0.58, "rationale": f"Sprint/quarter deadline — broad range: {deadline}"}
        else:
            return {"score": 0.35, "rationale": f"Vague deadline: '{deadline}'"}

    def _score_ambiguity_penalty(self, title: str, description: str, checks: Dict) -> Dict:
        text = (title + " " + description).lower()
        hedge_check = checks.get("no_hedge_words", {})
        cond_check  = checks.get("no_conditional_language", {})
        sarc_check  = checks.get("no_sarcasm_signal", {})

        penalties = []

        if not hedge_check.get("pass"):
            words = hedge_check.get("words_found", [])
            penalties.append(("hedge", len(words) * 0.12, f"hedge words: {words[:2]}"))

        if not cond_check.get("pass"):
            phrases = cond_check.get("phrases_found", [])
            penalties.append(("conditional", 0.20, f"conditional: '{phrases[0]}'"))

        if not sarc_check.get("pass"):
            penalties.append(("sarcasm", 0.25, "possible sarcasm"))

        total_penalty = min(0.95, sum(p[1] for p in penalties))
        score = max(0.05, 1.0 - total_penalty)

        if not penalties:
            return {"score": 1.0, "rationale": "No ambiguity signals — clean, direct statement"}
        else:
            details = "; ".join(p[2] for p in penalties)
            return {"score": round(score, 3), "rationale": f"Ambiguity detected: {details}"}

    # ── Routing justification ─────────────────────────────────────────────

    def _build_justification(
        self,
        band: str,
        confidence: float,
        dimensions: Dict,
        gate: Dict
    ) -> str:
        weak_dims = sorted(
            [(k, v["score"]) for k, v in dimensions.items()],
            key=lambda x: x[1]
        )[:2]
        weak_names = [d[0].replace("_", " ") for d in weak_dims if d[1] < 0.75]

        failure_reasons = gate.get("failure_reasons", [])

        if band == "AUTO":
            strong = [k for k, v in dimensions.items() if v["score"] >= 0.85]
            return (
                f"Confidence {confidence:.0%}: "
                + ", ".join(d.replace("_", " ") for d in strong[:3])
                + " all strong. Creating ticket now."
            )
        elif band == "REVIEW":
            issues = weak_names or ["one dimension below threshold"]
            return (
                f"Confidence {confidence:.0%}: "
                + f"Weak on {' and '.join(issues)}. "
                + "Review before creating ticket."
            )
        else:
            if failure_reasons:
                return f"Cannot execute: {failure_reasons[0]}"
            return (
                f"Confidence {confidence:.0%} below threshold. "
                + "Clarification required before this can become a ticket."
            )

    def score_batch(self, gated_items: List[Dict]) -> List[Dict]:
        """Score all gated items. Expects items already enriched with 'gate' key."""
        results = []
        for item in gated_items:
            gate = item.get("gate", {})
            scoring = self.score(item, gate)
            results.append({**item, "scoring": scoring})
        return results
