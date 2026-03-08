"""
TranscriptionService — AWS Transcribe + S3 pipeline
Converts uploaded audio files to timestamped transcript chunks
"""

import boto3
import json
import os
import time
import uuid
import urllib.request
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class TranscriptionService:
    """Transcribes audio using AWS Transcribe (batch mode)"""

    BUCKET_NAME = "decisionpilot-transcripts"
    REGION = os.getenv("AWS_REGION", "us-east-1")

    def __init__(self):
        kwargs = dict(region_name=self.REGION)
        key = os.getenv("AWS_ACCESS_KEY_ID")
        secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if key and secret:
            kwargs["aws_access_key_id"] = key
            kwargs["aws_secret_access_key"] = secret

        self.s3 = boto3.client("s3", **kwargs)
        self.transcribe = boto3.client("transcribe", **kwargs)
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3.head_bucket(Bucket=self.BUCKET_NAME)
        except Exception:
            try:
                if self.REGION == "us-east-1":
                    self.s3.create_bucket(Bucket=self.BUCKET_NAME)
                else:
                    self.s3.create_bucket(
                        Bucket=self.BUCKET_NAME,
                        CreateBucketConfiguration={"LocationConstraint": self.REGION},
                    )
                # Block all public access
                self.s3.put_public_access_block(
                    Bucket=self.BUCKET_NAME,
                    PublicAccessBlockConfiguration={
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True,
                    },
                )
                print(f"✓ Created S3 bucket: {self.BUCKET_NAME}")
            except Exception as e:
                print(f"⚠️  Bucket creation warning: {e}")

    def transcribe_audio(
        self,
        audio_path: str,
        meeting_id: str,
        language_code: str = "en-US",
        on_progress=None,
    ) -> Dict:
        """
        Full pipeline: upload → transcribe → parse → return chunks

        Returns:
            {
                "transcript": "full text",
                "chunks": [{"text": str, "start_time": float, "end_time": float, "speaker": str}],
                "duration_seconds": float,
                "word_count": int,
            }
        """
        ext = os.path.splitext(audio_path)[1].lower() or ".mp3"
        s3_key = f"audio/{meeting_id}{ext}"

        # 1. Upload to S3
        if on_progress:
            on_progress("uploading_audio", 5)
        print(f"  Uploading {audio_path} → s3://{self.BUCKET_NAME}/{s3_key}")
        self.s3.upload_file(audio_path, self.BUCKET_NAME, s3_key)

        # 2. Start transcription job
        job_name = f"dp-{meeting_id}-{int(time.time())}"
        media_uri = f"s3://{self.BUCKET_NAME}/{s3_key}"

        if on_progress:
            on_progress("transcribing", 10)
        print(f"  Starting transcription job: {job_name}")

        self.transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": media_uri},
            MediaFormat=ext.lstrip("."),
            LanguageCode=language_code,
            Settings={
                "ShowSpeakerLabels": True,
                "MaxSpeakerLabels": 10,
                "ShowAlternatives": False,
            },
        )

        # 3. Poll until complete
        start = time.time()
        timeout = 600  # 10 min max
        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                raise TimeoutError("Transcription timed out after 10 minutes")

            resp = self.transcribe.get_transcription_job(TranscriptionJobName=job_name)
            status = resp["TranscriptionJob"]["TranscriptionJobStatus"]

            if status == "COMPLETED":
                break
            elif status == "FAILED":
                reason = resp["TranscriptionJob"].get("FailureReason", "Unknown")
                raise RuntimeError(f"Transcription failed: {reason}")

            progress = min(int(elapsed / 60 * 40) + 10, 45)
            if on_progress:
                on_progress("transcribing", progress)
            print(f"  Transcription status: {status} ({int(elapsed)}s elapsed)")
            time.sleep(5)

        # 4. Download and parse result
        result_uri = resp["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
        with urllib.request.urlopen(result_uri) as r:
            transcript_json = json.loads(r.read())

        # 5. Clean up S3
        try:
            self.s3.delete_object(Bucket=self.BUCKET_NAME, Key=s3_key)
        except Exception:
            pass

        return self._parse_transcript(transcript_json, job_name)

    def _parse_transcript(self, transcript_json: Dict, job_name: str) -> Dict:
        """Parse AWS Transcribe JSON into usable chunks"""
        results = transcript_json.get("results", {})
        full_text = results.get("transcripts", [{}])[0].get("transcript", "")
        items = results.get("items", [])
        speaker_segments = results.get("speaker_labels", {}).get("segments", [])

        # Build speaker map: start_time → speaker_label
        speaker_map = {}
        for seg in speaker_segments:
            for item in seg.get("items", []):
                speaker_map[item.get("start_time")] = seg.get("speaker_label", "Speaker")

        # Group into ~30s chunks with speaker labels
        chunks = []
        current_chunk = {"words": [], "start_time": None, "end_time": None, "speaker": "Speaker"}

        for item in items:
            if item.get("type") != "pronunciation":
                continue
            start = float(item.get("start_time", 0))
            end = float(item.get("end_time", 0))
            word = item.get("alternatives", [{}])[0].get("content", "")
            speaker = speaker_map.get(item.get("start_time"), current_chunk["speaker"])

            if current_chunk["start_time"] is None:
                current_chunk["start_time"] = start
                current_chunk["speaker"] = speaker

            # New chunk every 30s or on speaker change
            if (end - current_chunk["start_time"] > 30) or (
                speaker != current_chunk["speaker"] and len(current_chunk["words"]) > 10
            ):
                if current_chunk["words"]:
                    current_chunk["text"] = " ".join(current_chunk["words"])
                    chunks.append(current_chunk)
                current_chunk = {
                    "words": [word],
                    "start_time": start,
                    "end_time": end,
                    "speaker": speaker,
                }
            else:
                current_chunk["words"].append(word)
                current_chunk["end_time"] = end

        if current_chunk["words"]:
            current_chunk["text"] = " ".join(current_chunk["words"])
            chunks.append(current_chunk)

        # Clean up temp keys
        for c in chunks:
            c.pop("words", None)

        duration = float(items[-1].get("end_time", 0)) if items else 0
        word_count = len([i for i in items if i.get("type") == "pronunciation"])

        print(f"  ✓ Transcription complete: {word_count} words, {len(chunks)} chunks, {duration:.0f}s")

        return {
            "transcript": full_text,
            "chunks": chunks,
            "duration_seconds": duration,
            "word_count": word_count,
            "job_name": job_name,
        }

    def chunks_to_evidence(self, chunks: List[Dict]) -> List[Dict]:
        """Convert transcript chunks to evidence format for ExtractorAgent"""
        evidence = []
        for i, chunk in enumerate(chunks):
            start = chunk.get("start_time", 0)
            mins = int(start // 60)
            secs = int(start % 60)
            timestamp = f"{mins:02d}:{secs:02d}"
            speaker = chunk.get("speaker", "Speaker").replace("spk_", "Speaker ")

            evidence.append({
                "citation_id": f"[{i+1}]",
                "content": chunk.get("text", ""),
                "source": "transcript",
                "timestamp": timestamp,
                "speaker": speaker,
                "start_time": start,
                "end_time": chunk.get("end_time", 0),
            })
        return evidence
