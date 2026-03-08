"""
Slide Analysis Agent — Uses Amazon Nova Lite vision to extract
commitments, decisions, and action items visible on meeting slides.

Inserts results as SLIDE-N evidence chunks before the main extractor runs,
so slide-sourced items appear naturally in the final output with [SLIDE-N] citations.
"""

import os
import base64
import json
from typing import List, Dict
from io import BytesIO


SYSTEM_PROMPT = """You are a visual meeting analyst reviewing presentation slides.

Your job: extract ONLY items explicitly visible as TEXT on the slides.
Do NOT infer or summarize — only extract what is literally written.

Focus on:
- Action items with owners (e.g. "Sarah → deploy by Friday")
- Decisions that were made (e.g. "Decision: use Stripe for payments")
- Deadlines or dates written on slides
- Agenda commitments or next steps listed

Output ONLY valid JSON in this exact schema:
{
  "slide_items": [
    {
      "content": "exact text describing the item",
      "slide_number": 1,
      "item_type": "action|decision|deadline|agenda",
      "owner": "person name or null",
      "deadline": "YYYY-MM-DD or text or null"
    }
  ]
}

If no actionable items are visible, return: {"slide_items": []}
No markdown, no explanation, only JSON."""


def _pdf_to_images(pdf_path: str, max_pages: int = 4) -> List[bytes]:
    """Convert PDF pages to JPEG bytes using pdf2image."""
    try:
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=150, fmt='jpeg',
                                   first_page=1, last_page=max_pages)
        out = []
        for page in pages:
            buf = BytesIO()
            page.save(buf, format='JPEG', quality=85)
            out.append(buf.getvalue())
        return out
    except Exception as e:
        print(f"⚠️  pdf2image failed for {pdf_path}: {e}")
        return []


def _load_image_bytes(path: str) -> bytes:
    """Load image file as raw bytes."""
    try:
        with open(path, 'rb') as f:
            return f.read()
    except Exception:
        return b''


def _find_slide_files(meeting_dir: str) -> List[Dict]:
    """
    Find slide PDFs and screenshot images in the meeting directory.
    Returns list of {"path": ..., "type": "pdf"|"image"}.
    """
    files = []
    try:
        for fname in sorted(os.listdir(meeting_dir)):
            fpath = os.path.join(meeting_dir, fname)
            lower = fname.lower()
            if (fname.startswith('slide_') or fname.startswith('screenshot_')):
                if lower.endswith('.pdf'):
                    files.append({"path": fpath, "type": "pdf"})
                elif any(lower.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp')):
                    files.append({"path": fpath, "type": "image"})
    except Exception:
        pass
    return files


class SlideAnalysisAgent:
    """
    Standalone (non-BaseAgent) agent for multimodal slide analysis.
    Inherits from BaseAgent to reuse Bedrock client + invoke_with_images.
    """

    def __init__(self):
        self.mock_mode = os.getenv('MOCK_MODE', 'false').lower() == 'true'
        self._bedrock = None
        self.model_id = os.getenv('NOVA_LITE_MODEL_ID', 'amazon.nova-lite-v1:0')

        if not self.mock_mode:
            try:
                import boto3
                self._bedrock = boto3.client(
                    'bedrock-runtime',
                    region_name=os.getenv('AWS_REGION', 'us-east-1')
                )
            except Exception as e:
                print(f"⚠️  SlideAnalysisAgent: AWS not available ({e}), using mock")
                self.mock_mode = True

    # ── Public API ───────────────────────────────────────────────────────────

    def analyze(self, meeting_dir: str, transcript_preview: str = '') -> List[Dict]:
        """
        Analyze slides/screenshots in meeting_dir.
        Returns evidence chunks ready to inject into the main pipeline:
        [{"citation_id": "SLIDE-1", "content": ..., "source": "slide", ...}]
        """
        slide_files = _find_slide_files(meeting_dir)
        if not slide_files:
            return []

        print(f"  📊 SlideAnalysisAgent: found {len(slide_files)} file(s)")

        if self.mock_mode:
            return self._mock_items()

        # Build image list for Nova
        images = []
        for sf in slide_files[:4]:  # cap at 4 files
            if sf["type"] == "pdf":
                page_bytes_list = _pdf_to_images(sf["path"], max_pages=3)
                for page_bytes in page_bytes_list[:3]:
                    images.append({"format": "jpeg", "data": base64.b64encode(page_bytes).decode()})
            else:
                raw = _load_image_bytes(sf["path"])
                if raw:
                    fmt = "jpeg" if sf["path"].lower().endswith(('.jpg', '.jpeg')) else "png"
                    images.append({"format": fmt, "data": base64.b64encode(raw).decode()})

        if not images:
            return []

        # Trim transcript context to 300 chars
        ctx = (transcript_preview or '')[:300].strip()
        prompt = (
            f"Meeting transcript context (for reference only): {ctx}\n\n"
            "Extract all action items, decisions, and commitments visible as text on these slides."
        )

        raw_items = self._call_nova(images, prompt)
        return self._to_evidence_chunks(raw_items)

    # ── Nova call ────────────────────────────────────────────────────────────

    def _call_nova(self, images: List[Dict], prompt: str) -> List[Dict]:
        try:
            content = []
            for img in images:
                content.append({
                    "image": {
                        "format": img["format"],
                        "source": {"bytes": img["data"]}
                    }
                })
            content.append({"text": prompt})

            body = {
                "messages": [{"role": "user", "content": content}],
                "system": [{"text": SYSTEM_PROMPT}],
                "inferenceConfig": {
                    "temperature": 0.0,
                    "maxTokens": 1500,
                    "topP": 0.9
                }
            }

            import json as _json
            response = self._bedrock.invoke_model(
                modelId=self.model_id,
                body=_json.dumps(body)
            )
            result = _json.loads(response['body'].read())
            output_text = result['output']['message']['content'][0]['text']
            print(f"  📊 Nova slide response: {output_text[:200]}")

            parsed = self._parse_json(output_text)
            return parsed.get('slide_items', [])

        except Exception as e:
            print(f"⚠️  SlideAnalysisAgent Nova call failed: {e}")
            return []

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_json(self, text: str) -> Dict:
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > 0:
                return json.loads(text[start:end])
        except Exception:
            pass
        return {"slide_items": []}

    def _to_evidence_chunks(self, raw_items: List[Dict]) -> List[Dict]:
        """Convert Nova output to evidence chunk format."""
        chunks = []
        for i, item in enumerate(raw_items):
            content = item.get('content', '').strip()
            if not content:
                continue
            owner = item.get('owner')
            deadline = item.get('deadline')
            # Enrich content with owner/deadline if present
            detail_parts = []
            if owner:
                detail_parts.append(f"Owner: {owner}")
            if deadline:
                detail_parts.append(f"Deadline: {deadline}")
            if detail_parts:
                content = f"{content} ({', '.join(detail_parts)})"

            chunks.append({
                "citation_id": f"SLIDE-{i+1}",
                "content": content,
                "source": "slide",
                "timestamp": "00:00",
                "speaker": "Slide",
                "slide_number": item.get('slide_number', 1),
                "item_type": item.get('item_type', 'action'),
            })
        print(f"  📊 Extracted {len(chunks)} items from slides")
        return chunks

    def _mock_items(self) -> List[Dict]:
        """Return hardcoded demo items for mock/dev mode."""
        return [
            {
                "citation_id": "SLIDE-1",
                "content": "Launch checklist: All payment flows tested before go-live (Owner: QA Lead, Deadline: March 14)",
                "source": "slide",
                "timestamp": "00:00",
                "speaker": "Slide",
                "slide_number": 1,
                "item_type": "action",
            },
            {
                "citation_id": "SLIDE-2",
                "content": "Decision: Stripe selected as primary payment processor — fallback to PayPal",
                "source": "slide",
                "timestamp": "00:00",
                "speaker": "Slide",
                "slide_number": 2,
                "item_type": "decision",
            },
        ]
