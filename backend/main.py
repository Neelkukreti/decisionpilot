"""
DecisionPilot FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
import config
import os
from datetime import datetime
import uuid
import json
import re

app = FastAPI(title="DecisionPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOCK_MODE = os.getenv('MOCK_MODE', 'true').lower() == 'true'

if MOCK_MODE:
    print("⚠️  Running in MOCK MODE")
else:
    print("✓ Running in LIVE MODE (AWS Nova)")


# ── Imports ──────────────────────────────────────────────────────────────────
from agents.extractor_agent import ExtractorAgent
from quality_gate import QualityGateAgent
from confidence_scorer import ConfidenceScorer
from health_score_engine import HealthScoreEngine
from execution_router import ExecutionRouter
import time

analysis_results: dict = {}

def _save_result(meeting_id: str, data: dict):
    """Persist result to disk so it survives restarts"""
    try:
        base = config.UPLOAD_DIR if os.path.isabs(config.UPLOAD_DIR) else os.path.join('/Users/macbook/.openclaw/workspace/decisionpilot/backend', config.UPLOAD_DIR)
        meeting_dir = os.path.join(base, meeting_id)
        os.makedirs(meeting_dir, exist_ok=True)
        with open(os.path.join(meeting_dir, 'result.json'), 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f'Warning: could not save result for {meeting_id}: {e}')

def _load_results():
    """Load all persisted results from disk on startup"""
    loaded = 0
    try:
        base = config.UPLOAD_DIR if os.path.isabs(config.UPLOAD_DIR) else os.path.join('/Users/macbook/.openclaw/workspace/decisionpilot/backend', config.UPLOAD_DIR)
        if not os.path.exists(base):
            return
        for mid in os.listdir(base):
            result_path = os.path.join(base, mid, 'result.json')
            if os.path.exists(result_path):
                try:
                    with open(result_path) as f:
                        analysis_results[mid] = json.load(f)
                    loaded += 1
                except Exception:
                    pass
    except Exception as e:
        print(f'Warning: could not load persisted results: {e}')
    if loaded:
        print(f'✓ Loaded {loaded} persisted result(s) from disk')

_load_results()


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"service": "DecisionPilot", "status": "running", "mock_mode": MOCK_MODE}


@app.get("/api/health")
async def health_check():
    status = {
        "status": "healthy",
        "mock_mode": MOCK_MODE,
        "components": {"agents": "ready", "upload_dir": os.path.exists(config.UPLOAD_DIR)},
    }
    if not MOCK_MODE:
        try:
            import boto3
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            status["components"]["aws"] = "connected"
            status["components"]["aws_account"] = identity.get('Account')
        except Exception as e:
            status["components"]["aws"] = f"error: {str(e)}"
    else:
        status["components"]["aws"] = "mock"
    return status


# ── Upload ────────────────────────────────────────────────────────────────────
@app.post("/api/meetings/upload")
async def upload_meeting(
    audio: Optional[UploadFile] = File(default=None),
    slides: List[UploadFile] = File(default=[]),
    screenshots: List[UploadFile] = File(default=[]),
    transcript_text: Optional[str] = Form(default=None),
):
    """Upload meeting files OR paste a raw transcript. Returns meeting_id immediately."""
    meeting_id = f"meeting-{uuid.uuid4().hex[:8]}"
    meeting_dir = os.path.join(config.UPLOAD_DIR, meeting_id)
    os.makedirs(meeting_dir, exist_ok=True)

    audio_path = None

    if audio and audio.filename:
        audio_path = os.path.join(meeting_dir, audio.filename)
        with open(audio_path, "wb") as f:
            f.write(await audio.read())

    for i, slide in enumerate(slides):
        with open(os.path.join(meeting_dir, f"slide_{i}_{slide.filename}"), "wb") as f:
            f.write(await slide.read())

    for i, ss in enumerate(screenshots):
        with open(os.path.join(meeting_dir, f"screenshot_{i}_{ss.filename}"), "wb") as f:
            f.write(await ss.read())

    # Save pasted transcript if provided
    if transcript_text:
        with open(os.path.join(meeting_dir, "transcript.txt"), "w") as f:
            f.write(transcript_text)

    print(f"✓ Saved meeting {meeting_id} | audio={audio_path} | transcript={'yes' if transcript_text else 'no'}")

    return {
        "meeting_id": meeting_id,
        "status": "uploaded",
        "has_audio": audio_path is not None,
        "has_transcript": transcript_text is not None,
        "slides": len(slides),
        "screenshots": len(screenshots),
    }


# ── Analyze ───────────────────────────────────────────────────────────────────
@app.post('/api/meetings/{meeting_id}/analyze')
async def analyze_meeting(meeting_id: str, background_tasks: BackgroundTasks):
    analysis_results[meeting_id] = {
        'status': 'running', 'stage': 'starting', 'progress': 0,
        'started_at': datetime.now().isoformat(),
    }
    background_tasks.add_task(run_analysis_pipeline, meeting_id)
    return {'meeting_id': meeting_id, 'status': 'started'}


# ── Missed Commitment Detection ───────────────────────────────────────────────
# Vague patterns with confidence: phrases that sound like commitments but lack
# the specificity to pass the quality gate.
_VAGUE_PATTERNS = [
    (r"\bI['']ll (?:probably |maybe |try to |just |quickly )?\w+(?:\s+\w+){1,8}", 'medium'),
    (r"\bwe should (?:probably |maybe |try to )?\w+(?:\s+\w+){0,6}", 'low'),
    (r"\bsomeon(?:e|eone) should \w+(?:\s+\w+){0,6}", 'low'),
    (r"\bmaybe we (?:can|could|should|ought to) \w+(?:\s+\w+){0,6}", 'low'),
    (r"\bI['']ll (?:check|look into|follow up|get back|reach out|circle back|ping)\b.{0,60}", 'medium'),
    (r"\bwe(?:'ll| will) figure (?:out|this)\b.{0,50}", 'low'),
    (r"\bwe need to \w+(?:\s+\w+){0,6}", 'medium'),
    (r"\bsomebody (?:should|needs to|has to|ought to) \w+(?:\s+\w+){0,6}", 'low'),
    (r"\bI should (?:probably |maybe )?\w+(?:\s+\w+){0,6}", 'low'),
    (r"\bshould (?:probably|maybe) \w+(?:\s+\w+){0,6}", 'low'),
    (r"\blet'?s (?:try to |maybe |probably )?\w+(?:\s+\w+){0,6}", 'low'),
    (r"\bwe(?:'ll| will) (?:take a look|revisit|discuss|review|check) .{5,60}", 'medium'),
]

def detect_missed_commitments(
    transcript_text: str,
    participants: list,
    action_items: list,
) -> list:
    """Detect vague commitments that didn't pass the quality gate."""
    if not transcript_text:
        return []

    # Titles of real action items — avoid double-counting
    real_titles = {a.get('title', '').lower()[:50] for a in action_items}
    participant_names = [p['name'] for p in participants]

    commitments = []
    seen_sentences: set = set()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', transcript_text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20 or len(sentence) > 250:
            continue
        key = sentence.lower()[:50]
        if key in seen_sentences:
            continue

        for pattern, confidence in _VAGUE_PATTERNS:
            if not re.search(pattern, sentence, re.IGNORECASE):
                continue

            # Skip if it duplicates a real action
            if any(key in t or t in key for t in real_titles if len(t) > 15):
                break

            seen_sentences.add(key)

            # Infer owner: scan for participant names in or near sentence
            owner = None
            ctx = transcript_text
            pos = ctx.lower().find(sentence.lower()[:30])
            surrounding = ctx[max(0, pos - 80):pos + len(sentence) + 10] if pos >= 0 else sentence
            for name in participant_names:
                if name.split()[0].lower() in surrounding.lower():
                    owner = name
                    break
            # If "I'll" → speaker is implicit owner (mark as inferred)
            first_person = bool(re.search(r"\bI[''](?:ll|ve|m)\b|\bI (?:will|should|need)\b", sentence, re.I))
            if first_person and not owner and participant_names:
                owner = participant_names[0]  # best-effort: first participant

            # Determine missing fields
            has_deadline = bool(re.search(
                r'\b(?:by|before|until|on|next|tomorrow|today|this week|end of|Monday|Tuesday|Wednesday|Thursday|Friday|March|April|next month)\b',
                sentence, re.I,
            ))
            missing = []
            if not has_deadline:
                missing.append('deadline')
            if not owner and not first_person:
                missing.append('owner')
            if len(sentence.split()) < 6:
                missing.append('clarity')

            reason_parts = []
            if 'deadline' in missing:
                reason_parts.append('No explicit deadline detected')
            if 'owner' in missing:
                reason_parts.append('No named owner could be identified')
            if 'clarity' in missing:
                reason_parts.append('Action too vague to act on')

            commitments.append({
                'commitment_id': f'MC-{len(commitments)+1:03d}',
                'sentence': sentence[:180],
                'inferred_owner': owner,
                'confidence': confidence,
                'missing_fields': missing,
                'reason': '. '.join(reason_parts) or 'Vague language detected',
            })
            break  # one pattern per sentence

        if len(commitments) >= 6:
            break

    return commitments


async def run_analysis_pipeline(meeting_id: str):
    """
    7-stage pipeline:
      1  Transcription  — AWS Transcribe (or read pasted text)
      2  Extraction     — Nova Lite extracts decisions + action items
      3  Enrichment     — add metadata and evidence links
      4  Quality Gate   — 7-rule deterministic filter
      5  Confidence     — 5-dimension scoring
      6  Health Score   — meeting-level quality prediction
      7  Execution      — AUTO / REVIEW / CLARIFY routing
    """
    result = analysis_results[meeting_id]
    meeting_dir = os.path.join(config.UPLOAD_DIR, meeting_id)

    try:
        # ── Stage 1: Transcription ────────────────────────────────────────
        result.update({'stage': 'transcription', 'progress': 5,
                       'stage_detail': 'Transcribing audio...'})

        transcript_text = None
        chunks = []

        # Check for pasted transcript first (fastest path)
        transcript_file = os.path.join(meeting_dir, "transcript.txt")
        if os.path.exists(transcript_file):
            with open(transcript_file) as f:
                transcript_text = f.read()
            # Treat as single chunk
            chunks = [{"text": transcript_text, "start_time": 0, "end_time": 0,
                       "speaker": "Speaker 1", "citation_id": "[1]"}]
            print(f"  Using pasted transcript ({len(transcript_text)} chars)")
            result.update({'stage_detail': 'Using pasted transcript', 'progress': 20})
        else:
            # Find audio file
            audio_path = None
            for f in os.listdir(meeting_dir):
                if f.lower().endswith(('.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg', '.webm')):
                    audio_path = os.path.join(meeting_dir, f)
                    break

            if audio_path and not MOCK_MODE:
                from transcription_service import TranscriptionService

                def on_progress(stage, pct):
                    result.update({'stage_detail': f'Transcribing... ({pct}%)', 'progress': pct})

                svc = TranscriptionService()
                transcription = svc.transcribe_audio(audio_path, meeting_id, on_progress=on_progress)
                transcript_text = transcription["transcript"]
                from transcription_service import TranscriptionService as _TS
                chunks = svc.chunks_to_evidence(transcription["chunks"])
                result.update({'duration_seconds': transcription['duration_seconds'],
                               'word_count': transcription['word_count']})
            else:
                # Demo fallback — use hardcoded sample
                transcript_text = (
                    "Team meeting March 4. Sarah Chen will deploy the authentication service "
                    "to production by Friday March 7th — she owns the rollout. "
                    "John will update the API documentation with Auth0 integration details by March 12. "
                    "We decided to use Auth0 for OAuth2. Budget approved at $45k. "
                    "Someone should probably look at the rollback plan at some point. "
                    "Sarah: I will run the full QA suite on the release candidate by end of next week."
                )
                chunks = [{"text": transcript_text, "start_time": 0, "end_time": 180,
                           "speaker": "Mixed", "citation_id": "[1]"}]
                result.update({'stage_detail': 'Using demo transcript (no audio uploaded)', 'progress': 20})

        # Consolidate many small chunks into at most 12 for Nova
        if len(chunks) > 12:
            print(f"  Consolidating {len(chunks)} chunks → 12 for Nova")
            chunks = _consolidate_chunks(chunks, max_chunks=12)

        # Build evidence list for extractor
        evidence = []
        for i, chunk in enumerate(chunks):
            ts = chunk.get("start_time", 0)
            mins, secs = int(ts // 60), int(ts % 60)
            evidence.append({
                "citation_id": chunk.get("citation_id") or f"[{i+1}]",
                "content": chunk.get("text") or chunk.get("content", ""),
                "source": "transcript",
                "timestamp": f"{mins:02d}:{secs:02d}",
                "speaker": chunk.get("speaker", "Speaker"),
            })

        # Surface transcript preview immediately so frontend can show it while Nova runs
        if transcript_text:
            result["transcript_preview"] = transcript_text[:800]
            result["word_count"] = result.get("word_count") or len(transcript_text.split())

        # ── Stage 1.5: Slide Analysis (Nova Lite Vision) ──────────────────
        slide_agent_used = False
        try:
            from agents.slide_analysis_agent import SlideAnalysisAgent
            result.update({'stage': 'slide_analysis', 'progress': 25,
                           'stage_detail': 'Nova analyzing slides and screenshots...'})
            _save_result(meeting_id, result)
            slide_agent = SlideAnalysisAgent()
            slide_items = slide_agent.analyze(meeting_dir, transcript_text or '')
            if slide_items:
                evidence.extend(slide_items)
                slide_agent_used = True
                print(f"  ✓ Injected {len(slide_items)} slide evidence chunk(s)")
        except Exception as e:
            print(f"⚠️  Slide analysis skipped: {e}")

        # ── Stage 2: Extraction (Nova Lite) ───────────────────────────────
        result.update({'stage': 'extraction', 'progress': 30,
                       'stage_detail': f'Nova extracting decisions from {len(evidence)} chunks...'})

        extractor = ExtractorAgent()
        extraction = extractor.execute({'evidence_chunks': evidence})
        raw_actions   = extraction.output.get('action_items', [])
        raw_decisions = extraction.output.get('decisions', [])
        open_qs       = extraction.output.get('open_questions', [])
        risks         = extraction.output.get('risks', [])
        summary_text  = extraction.output.get('summary', '')

        print(f"  Nova extracted: {len(raw_actions)} actions, {len(raw_decisions)} decisions")
        result.update({'nova_summary': summary_text})

        # ── Stage 3: Enrichment ───────────────────────────────────────────
        result.update({'stage': 'enrichment', 'progress': 42,
                       'stage_detail': f'Enriching {len(raw_actions)} action items...'})

        # Build citation → evidence lookup for verbatim quotes
        citation_map = {e["citation_id"]: e for e in evidence}

        enriched_actions = []
        for idx, action in enumerate(raw_actions):
            # Normalize field names (extractor uses description, UI wants title)
            title = action.get('title') or action.get('description', f'Action {idx+1}')
            owner = action.get('owner', 'Unknown')
            deadline = action.get('deadline')
            citations = action.get('citations', ['[1]'])

            # Find verbatim quote from best citation
            verbatim = None
            timestamp = None
            for cid in citations:
                ev = citation_map.get(cid)
                if ev:
                    # Use first 120 chars of chunk as quote
                    verbatim = ev['content'][:200].strip()
                    timestamp = ev['timestamp']
                    break

            # Strip citation markers from title
            clean_title = re.sub(r'\[\d+\]', '', title).strip()
            enriched_actions.append({
                'action_id':       action.get('action_id') or f'act_{idx+1:03d}',
                'title':           clean_title[:120],
                'description':     action.get('description') or title,
                'owner':           owner,
                'owner_confidence': _owner_confidence(owner),
                'deadline':        deadline,
                'priority':        action.get('priority', 'medium'),
                'citations':       citations,
                'corroborating_citations': [],
                'verbatim_quote':  verbatim,
                'timestamp':       timestamp,
            })

        time.sleep(0.2)

        # ── Stage 4: Quality Gate ─────────────────────────────────────────
        result.update({'stage': 'quality_gate', 'progress': 58,
                       'stage_detail': 'Running 7-rule quality gate...'})
        gate_agent = QualityGateAgent()
        gated_items = gate_agent.evaluate_batch(enriched_actions)
        time.sleep(0.2)

        # ── Stage 5: Confidence ────────────────────────────────────────────
        result.update({'stage': 'confidence', 'progress': 72,
                       'stage_detail': 'Computing 5-dimension confidence scores...'})
        scorer = ConfidenceScorer()
        scored_items = scorer.score_batch(gated_items)
        time.sleep(0.2)

        # ── Stage 6: Health Score ──────────────────────────────────────────
        result.update({'stage': 'health_score', 'progress': 82,
                       'stage_detail': 'Computing meeting health score...'})
        health_engine = HealthScoreEngine()
        health = health_engine.compute(scored_items, open_questions=open_qs, identified_risks=risks)
        time.sleep(0.1)

        # ── Stage 7: Execution Router ──────────────────────────────────────
        result.update({'stage': 'execution', 'progress': 92,
                       'stage_detail': 'Routing AUTO / REVIEW / CLARIFY...'})
        router = ExecutionRouter()
        routed = router.route_batch(scored_items)
        routed_items = routed['routed_items']
        routing_summary = {**routed['summary'], 'jira_live': router.is_live}

        # ── Format decisions ───────────────────────────────────────────────
        decisions_fmt = []
        for d in raw_decisions[:6]:
            decisions_fmt.append({
                'title':      (d.get('description') or d.get('title', ''))[:100],
                'confidence': d.get('confidence', 0.9),
                'citation':   (d.get('citations') or ['[1]'])[0],
            })

        # ── Format action items ────────────────────────────────────────────
        action_items_fmt = []
        for item in routed_items:
            scoring  = item.get('scoring', {})
            gate     = item.get('gate', {})
            ticket   = item.get('ticket') or {}
            routing  = item.get('routing', {})

            action_items_fmt.append({
                'action_id':             item['action_id'],
                'title':                 item['title'],
                'owner':                 item.get('owner'),
                'priority':              item.get('priority', 'medium'),
                'deadline':              item.get('deadline'),
                'citation':              (item.get('citations') or ['[1]'])[0],
                'verbatim_quote':        item.get('verbatim_quote'),
                'timestamp':             item.get('timestamp'),
                'routing_band':          routing.get('band', 'CLARIFY'),
                'routing_confidence':    round(scoring.get('confidence_adjusted', 0), 2),
                'routing_justification': routing.get('justification', ''),
                'gate_result':           gate.get('gate_result', 'FAIL'),
                'gate_checks_passed':    gate.get('checks_passed', 0),
                'gate_failure_reasons':  gate.get('failure_reasons', []),
                'confidence_dimensions': {
                    k: {'score': round(v['score'], 2), 'rationale': v['rationale']}
                    for k, v in scoring.get('dimensions', {}).items()
                },
                'ticket_id':             ticket.get('ticket_id'),
                'ticket_url':            ticket.get('ticket_url'),
                'ticket_status':         ticket.get('status', 'pending'),
                'suggested_edits':       routing.get('suggested_edits', []),
                'clarifying_question':   routing.get('clarifying_question'),
                'blocked_reasons':       routing.get('blocked_reasons', []),
            })

        # ── Missed commitment detection ────────────────────────────────────
        all_participants = _build_participants(action_items_fmt, decisions_fmt, open_qs or [], risks or [])
        missed_commitments = detect_missed_commitments(
            transcript_text or '',
            all_participants,
            action_items_fmt,
        )

        # ── Has audio? ─────────────────────────────────────────────────────
        has_audio = any(
            f.lower().endswith(('.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg', '.webm'))
            for f in os.listdir(meeting_dir)
        )

        # ── Done ──────────────────────────────────────────────────────────
        analysis_results[meeting_id].update({
            'status':            'complete',
            'stage':             'complete',
            'progress':          100,
            'completed_at':      datetime.now().isoformat(),
            'health_score':      health['health_score'],
            'health_grade':      health['grade'],
            'health_breakdown':  health['breakdown'],
            'execution_prediction': health['execution_prediction'],
            'health_strengths':  health['strengths'],
            'health_weaknesses': health['weaknesses'],
            'health_recommendation': health['recommendation'],
            'decisions':         decisions_fmt,
            'action_items':      action_items_fmt,
            'open_questions':    [
                {
                    'question_id': q.get('question_id', f'Q-{i+1:03d}'),
                    'question':    q.get('question', str(q)),
                    'asker':       q.get('asker'),
                    'assignee':    None,
                    'requires_followup': q.get('requires_followup', True),
                    'citations':   q.get('citations', []),
                }
                for i, q in enumerate(open_qs or [])
            ],
            'risks':             [
                {
                    'risk_id':     r.get('risk_id', f'RISK-{i+1:03d}'),
                    'description': r.get('description', ''),
                    'severity':    r.get('severity', 'medium'),
                    'owner':       r.get('owner'),
                    'mitigation':  r.get('mitigation'),
                    'citations':   r.get('citations', []),
                }
                for i, r in enumerate(risks or [])
            ],
            'participants':      all_participants,
            'missed_commitments': missed_commitments,
            'has_audio':         has_audio,
            'routing_summary':   routing_summary,
            'transcript_preview': transcript_text[:500] if transcript_text else None,
            'agents_used':       (
                                  ['Transcription'] +
                                  (['Nova Slide Vision'] if slide_agent_used else []) +
                                  ['Nova Extraction', 'Enrichment',
                                   'Quality Gate', 'Confidence Scorer',
                                   'Health Score', 'Execution Router']
                                 ),
            'summary': (
                f"{len(action_items_fmt)} action items. "
                f"Health {health['health_score']}/100 ({health['grade']}). "
                f"{routing_summary['auto']} auto-executed, "
                f"{routing_summary['review']} review, "
                f"{routing_summary['clarify']} clarify."
            ),
        })

        # Persist completed result to disk
        _save_result(meeting_id, analysis_results[meeting_id])

    except Exception as e:
        import traceback
        analysis_results[meeting_id].update({
            'status': 'error', 'error': str(e), 'traceback': traceback.format_exc(),
        })
        _save_result(meeting_id, analysis_results[meeting_id])


def _consolidate_chunks(chunks: list, max_chunks: int = 12) -> list:
    """Merge many small transcript chunks into at most max_chunks larger ones.
    Nova Lite works best with 8-12 evidence items of ~400 words each.
    """
    if len(chunks) <= max_chunks:
        return chunks

    group_size = max(1, len(chunks) // max_chunks)
    consolidated = []
    for i in range(0, len(chunks), group_size):
        group = chunks[i:i + group_size]
        merged_text = " ".join(c.get("text") or c.get("content", "") for c in group)
        first = group[0]
        last  = group[-1]
        # Collect unique speakers
        speakers = list(dict.fromkeys(
            c.get("speaker", "Speaker") for c in group
            if c.get("speaker")
        ))
        consolidated.append({
            "text":       merged_text,
            "start_time": first.get("start_time", 0),
            "end_time":   last.get("end_time", 0),
            "speaker":    speakers[0] if len(speakers) == 1 else "Multiple speakers",
            "citation_id": f"[{len(consolidated)+1}]",
        })
        if len(consolidated) >= max_chunks:
            break
    return consolidated


def _owner_confidence(owner: str) -> float:
    """Heuristic: how confident are we this is a real person?"""
    if not owner:
        return 0.0
    vague = {'someone', 'anyone', 'everybody', 'everybody', 'team', 'we', 'us', 'they', 'unknown', 'tbd', 'n/a'}
    if owner.lower().strip() in vague:
        return 0.0
    # Has a space (likely first + last name) → high confidence
    if ' ' in owner.strip():
        return 0.9
    return 0.6


# ── Results ───────────────────────────────────────────────────────────────────
@app.get('/api/meetings/{meeting_id}/results')
async def get_analysis_results(meeting_id: str):
    if meeting_id in analysis_results:
        return analysis_results[meeting_id]
    # Fall back to disk (survives server restarts)
    result_path = os.path.join(config.UPLOAD_DIR, meeting_id, 'result.json')
    if os.path.exists(result_path):
        with open(result_path) as f:
            data = json.load(f)
        analysis_results[meeting_id] = data  # cache in memory
        return data
    return {'meeting_id': meeting_id, 'status': 'not_started', 'stage': 'waiting', 'progress': 0}


@app.get('/api/meetings/{meeting_id}/status')
async def get_meeting_status(meeting_id: str):
    if meeting_id in analysis_results:
        r = analysis_results[meeting_id]
        return {'meeting_id': meeting_id, 'stage': r.get('stage', 'unknown'),
                'progress': r.get('progress', 0), 'status': r.get('status')}
    # Fall back to disk
    result_path = os.path.join(config.UPLOAD_DIR, meeting_id, 'result.json')
    if os.path.exists(result_path):
        with open(result_path) as f:
            data = json.load(f)
        analysis_results[meeting_id] = data
        return {'meeting_id': meeting_id, 'stage': data.get('stage', 'complete'),
                'progress': data.get('progress', 100), 'status': data.get('status')}
    return {'meeting_id': meeting_id, 'stage': 'not_started', 'progress': 0}


@app.get('/api/meetings/{meeting_id}/audio')
async def get_meeting_audio(meeting_id: str):
    """Serve the uploaded audio file for a meeting (used by Evidence Playback)."""
    meeting_dir = os.path.join(config.UPLOAD_DIR, meeting_id)
    if not os.path.isdir(meeting_dir):
        raise HTTPException(status_code=404, detail='Meeting not found')
    for fname in os.listdir(meeting_dir):
        if fname.lower().endswith(('.mp3', '.mp4', '.wav', '.m4a', '.flac', '.ogg', '.webm')):
            ext = fname.rsplit('.', 1)[-1].lower()
            mime = {'mp3': 'audio/mpeg', 'mp4': 'video/mp4', 'wav': 'audio/wav',
                    'm4a': 'audio/mp4', 'flac': 'audio/flac', 'ogg': 'audio/ogg',
                    'webm': 'audio/webm'}.get(ext, 'audio/mpeg')
            return FileResponse(os.path.join(meeting_dir, fname), media_type=mime)
    raise HTTPException(status_code=404, detail='No audio file found for this meeting')


def _build_participants(action_items, decisions, open_qs, risks) -> list:
    """Collect all named people from the meeting output, with their roles."""
    from collections import defaultdict
    people: dict = defaultdict(lambda: {'name': '', 'actions': [], 'decisions': [], 'questions': [], 'risks': []})

    vague = {
        'someone', 'anyone', 'everybody', 'team', 'we', 'us', 'they', 'unknown',
        'tbd', 'n/a', 'unassigned', 'null', '???', '', 'selected', 'locked',
        'approved', 'rejected', 'pending', 'all', 'everyone', 'nobody',
        'the team', 'our team', 'management', 'leadership',
        # Transcribe diarization false positives (spoken words mistaken for names)
        'confirmed', 'agreed', 'understood', 'correct', 'right', 'okay', 'yes', 'noted',
        'done', 'sure', 'absolutely', 'exactly', 'perfect', 'great', 'good',
    }
    def clean(name):
        if not name: return None
        n = name.strip()
        if n.lower() in vague: return None
        # Must look like a proper noun: Title case or full name (contains space)
        # Reject single lowercase words and things with no letters
        import re
        if not re.search(r'[A-Za-z]', n): return None
        words = n.split()
        if len(words) == 1 and n[0].islower(): return None  # skip lowercase single words
        if len(n) < 2: return None
        return n

    for a in action_items:
        owner = clean(a.get('owner'))
        if owner:
            people[owner]['name'] = owner
            people[owner]['actions'].append(a.get('action_id', ''))

    for d in decisions:
        maker = clean(d.get('decision_maker') or d.get('title', '').split()[0])
        if maker and len(maker) > 2:
            people[maker]['name'] = maker
            people[maker]['decisions'].append(d.get('title', '')[:60])

    for q in open_qs:
        asker = clean(q.get('asker'))
        if asker:
            people[asker]['name'] = asker
            people[asker]['questions'].append(q.get('question_id', ''))

    for r in risks:
        owner = clean(r.get('owner'))
        if owner:
            people[owner]['name'] = owner
            people[owner]['risks'].append(r.get('risk_id', ''))

    result = []
    for name, data in sorted(people.items(), key=lambda x: -len(x[1]['actions'])):
        result.append({
            'name':      name,
            'initials':  ''.join(w[0].upper() for w in name.split()[:2]),
            'action_count':   len(data['actions']),
            'decision_count': len(data['decisions']),
            'question_count': len(data['questions']),
            'risk_count':     len(data['risks']),
        })
    return result
