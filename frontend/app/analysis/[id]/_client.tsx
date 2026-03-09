'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import {
  CheckCircle, CheckCircle2, Clock, Loader2, AlertCircle, ExternalLink,
  Zap, ChevronRight, X, ArrowLeft, ChevronDown,
  Eye, AlertTriangle, Download, User, Calendar, HelpCircle, BarChart3,
  Shield, UserCheck, MessageCircle, Users,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────
interface ConfidenceDimension { score: number; rationale: string; }
interface ActionItem {
  action_id: string; title: string; owner: string;
  priority: 'high' | 'medium' | 'low'; deadline: string | null;
  citation: string; verbatim_quote: string | null; timestamp: string | null;
  routing_band: 'AUTO' | 'REVIEW' | 'CLARIFY';
  routing_confidence: number; routing_justification: string;
  gate_result: string; gate_checks_passed: number; gate_failure_reasons: string[];
  confidence_dimensions: Record<string, ConfidenceDimension>;
  ticket_id: string | null; ticket_url: string | null; ticket_status: string;
  execution_time_ms: number | null;
  suggested_edits: Array<{ field: string; current: string; suggestion: string; reason: string }>;
  clarifying_question: string | null; blocked_reasons: string[];
}
interface OpenQuestion {
  question_id: string; question: string;
  asker: string | null; assignee: string | null;
  requires_followup: boolean; citations: string[];
}
interface Risk {
  risk_id: string; description: string;
  severity: 'high' | 'medium' | 'low';
  owner: string | null; mitigation: string | null; citations: string[];
}
interface Participant {
  name: string; initials: string;
  action_count: number; decision_count: number;
  question_count: number; risk_count: number;
}
interface HealthDim { score: number; weighted: number; detail: string; }
interface AnalysisResult {
  meeting_id: string; status: 'not_started' | 'running' | 'complete' | 'error';
  stage: string; progress: number; stage_detail?: string;
  health_score?: number; health_grade?: string;
  health_breakdown?: Record<string, HealthDim>;
  execution_prediction?: string; health_strengths?: string[]; health_weaknesses?: string[];
  health_recommendation?: string;
  decisions?: Array<{ title: string; confidence: number; citation: string }>;
  action_items?: ActionItem[];
  open_questions?: Array<OpenQuestion | string>;
  risks?: Risk[];
  participants?: Participant[];
  routing_summary?: { auto: number; review: number; clarify: number; total: number; jira_live?: boolean };
  agents_used?: string[]; summary?: string; error?: string;
  transcript_preview?: string; word_count?: number; nova_summary?: string;
  missed_commitments?: MissedCommitment[];
  has_audio?: boolean;
}
interface MissedCommitment {
  commitment_id: string;
  sentence: string;
  inferred_owner: string | null;
  confidence: 'high' | 'medium' | 'low';
  missing_fields: string[];
  reason: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────
const STAGE_ORDER = ['transcription','slide_analysis','extraction','enrichment','quality_gate','confidence','health_score','execution','complete'];
const STAGE_LABELS: Record<string,string> = {
  transcription:'Transcription', slide_analysis:'Slide Vision', extraction:'Nova Extraction',
  enrichment:'Evidence Linker', quality_gate:'Quality Gate', confidence:'Confidence Scorer',
  health_score:'Health Score', execution:'Execution Router', complete:'Complete',
};
const STAGE_TOOLS: Record<string, string> = {
  transcription:'AWS Transcribe', slide_analysis:'Nova Lite Vision', extraction:'Nova Lite',
  enrichment:'Rule Engine', quality_gate:'Deterministic', confidence:'Nova Lite',
  health_score:'Analytics', execution:'Router',
};

// ─── Design tokens ────────────────────────────────────────────────────────────
const STATUS = {
  AUTO:    { accent: '#16A34A', chip: 'bg-green-50  text-green-700  border border-green-100',  label: 'Executed'        },
  REVIEW:  { accent: '#D97706', chip: 'bg-amber-50  text-amber-700  border border-amber-100',  label: 'Needs Review'    },
  CLARIFY: { accent: '#DC2626', chip: 'bg-red-50    text-red-700    border border-red-100',    label: 'Execution Risk' },
} as const;

const SEVERITY_TOKENS = {
  high:   { label: 'High Risk',   color: '#DC2626', bg: '#FFF1F2', border: '#FECACA' },
  medium: { label: 'Medium Risk', color: '#D97706', bg: '#FFFBEB', border: '#FDE68A' },
  low:    { label: 'Low Risk',    color: '#64748B', bg: '#F8FAFC', border: '#E2E8F0' },
} as const;

// ─── Global CSS ───────────────────────────────────────────────────────────────
const GLOBAL_CSS = `
  @keyframes fadeUp {
    from { opacity:0; transform:translateY(10px); }
    to   { opacity:1; transform:translateY(0);    }
  }
  @keyframes fadeIn {
    from { opacity:0; }
    to   { opacity:1; }
  }
  @keyframes dpWave {
    0%,100% { transform:scaleY(0.35); }
    50%     { transform:scaleY(1);    }
  }

  .u-fade-up { animation: fadeUp 0.28s cubic-bezier(0.16,1,0.3,1) both; }
  .u-fade-in { animation: fadeIn 0.3s ease both; }

  .action-card {
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  }
  .action-card:not(.is-expanded):hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.05) !important;
    border-color: rgba(0,0,0,0.09);
  }

  .soft-card {
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .soft-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.07) !important;
  }

  .accordion-wrap {
    display: grid;
    grid-template-rows: 0fr;
    opacity: 0;
    transition:
      grid-template-rows 0.26s cubic-bezier(0.4,0,0.2,1),
      opacity            0.2s  ease;
  }
  .accordion-wrap > div { overflow: hidden; }
  .accordion-wrap.is-open {
    grid-template-rows: 1fr;
    opacity: 1;
  }

  .pipeline-chevron { transition: transform 0.22s ease; }
  .pipeline-chevron.is-open { transform: rotate(180deg); }

  .assign-dropdown {
    animation: fadeUp 0.15s cubic-bezier(0.16,1,0.3,1) both;
  }

  .section-label {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: #94A3B8;
  }
`;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function useCopy() {
  const [copied, setCopied] = useState<string | null>(null);
  const copy = (text: string, key: string) => {
    navigator.clipboard?.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };
  return { copied, copy };
}

function fmtDate(d: string | null): string {
  if (!d) return '—';
  return new Date(d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function normalizeQuestion(q: OpenQuestion | string, i: number): OpenQuestion {
  if (typeof q === 'string') return {
    question_id: `Q-${String(i + 1).padStart(3, '0')}`,
    question: q, asker: null, assignee: null,
    requires_followup: true, citations: [],
  };
  return q;
}

const AVATAR_PALETTE = ['#7C3AED','#2563EB','#059669','#D97706','#C2410C','#0891B2','#9333EA','#BE185D'];
function avatarColor(name: string): string {
  let h = 0;
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
  return AVATAR_PALETTE[h % AVATAR_PALETTE.length];
}

// ─── Avatar ───────────────────────────────────────────────────────────────────
function Avatar({ name, size = 'sm' }: { name: string; size?: 'xs' | 'sm' | 'md' }) {
  const color = avatarColor(name);
  const initials = name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
  const cls = size === 'xs' ? 'w-5 h-5 text-[9px]' : size === 'sm' ? 'w-7 h-7 text-[11px]' : 'w-9 h-9 text-sm';
  return (
    <div className={`${cls} rounded-full flex items-center justify-center shrink-0 font-bold text-white select-none`}
      style={{ backgroundColor: color }}>
      {initials}
    </div>
  );
}

// ─── Animated progress bar ────────────────────────────────────────────────────
function AnimatedBar({ value, color }: { value: number; color: string }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setWidth(value), 320);
    return () => clearTimeout(t);
  }, [value]);
  return (
    <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
      <div className="h-2.5 rounded-full"
        style={{ width: `${width}%`, backgroundColor: color, transition: 'width 0.9s cubic-bezier(0.16,1,0.3,1)' }} />
    </div>
  );
}

// ─── Export menu ─────────────────────────────────────────────────────────────
function ExportMenu({ result }: { result: AnalysisResult }) {
  const [open, setOpen] = useState(false);
  const { copied, copy } = useCopy();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);
  const items = result.action_items || [];
  const toMd = () => {
    const lines = [`# Meeting Analysis — ${result.meeting_id}`, `Health: ${result.health_score}/100`, ''];
    for (const i of items) lines.push(`- [${i.routing_band}] **${i.title}** · ${i.owner || 'TBD'} · ${i.deadline || 'No date'}`);
    return lines.join('\n');
  };
  const toCsv = () => {
    const rows = items.map(i => [i.routing_band, `"${i.title}"`, i.owner||'', i.deadline||'', `${Math.round(i.routing_confidence*100)}%`, i.ticket_id||''].join(','));
    return ['Band,Title,Owner,Deadline,Confidence,Ticket', ...rows].join('\n');
  };
  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 border border-slate-700 hover:border-slate-600 rounded-lg px-3 py-1.5 transition-all duration-150">
        <Download className="w-3.5 h-3.5" /> Export
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-50 min-w-[172px] u-fade-up">
          <button onClick={() => { copy(toMd(), 'md'); setOpen(false); }}
            className="w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors">
            {copied === 'md' ? '✓ Copied!' : 'Copy as Markdown'}
          </button>
          <button onClick={() => { copy(toCsv(), 'csv'); setOpen(false); }}
            className="w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-slate-50 transition-colors">
            {copied === 'csv' ? '✓ Copied!' : 'Download CSV'}
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Evidence drawer ──────────────────────────────────────────────────────────
function parseTimestamp(ts: string | null): number {
  if (!ts) return 0;
  const parts = ts.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return 0;
}

function EvidenceDrawer({ item, onClose, meetingId, hasAudio }: {
  item: ActionItem; onClose: () => void; meetingId: string; hasAudio: boolean;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [audioError, setAudioError] = useState(false);

  const handlePlaySource = () => {
    if (!audioRef.current || audioError) return;
    const secs = parseTimestamp(item.timestamp);
    audioRef.current.currentTime = Math.max(0, secs - 1.5);
    audioRef.current.play().catch(() => setAudioError(true));
    setPlaying(true);
  };

  const handlePause = () => {
    audioRef.current?.pause();
    setPlaying(false);
  };

  const dimLabels: Record<string,string> = {
    action_clarity:'Action clarity', ownership_certainty:'Ownership',
    evidence_strength:'Evidence', deadline_clarity:'Deadline', ambiguity_penalty:'Ambiguity',
  };
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/20 backdrop-blur-[2px]" onClick={onClose} />
      <div className="w-full max-w-sm bg-white border-l border-slate-200 overflow-y-auto shadow-2xl flex flex-col u-fade-up"
        style={{ animationDuration: '0.2s' }}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 sticky top-0 bg-white/95 backdrop-blur z-10">
          <span className="text-sm font-semibold text-slate-900">Evidence</span>
          <button onClick={onClose}
            className="text-slate-400 hover:text-slate-700 rounded-lg p-1 hover:bg-slate-100 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-6 space-y-6 flex-1">
          <p className="text-[15px] font-medium text-slate-900 leading-snug">{item.title}</p>

          {item.verbatim_quote && (
            <div>
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5">Transcript highlight</p>
              <blockquote className="bg-slate-50 border-l-[3px] border-amber-400 rounded-r-xl px-4 py-3.5">
                {item.timestamp && (
                  <p className="text-[10px] text-slate-400 font-mono mb-1.5">[{item.timestamp}] {item.owner}</p>
                )}
                <p className="text-sm text-slate-700 italic leading-relaxed">"{item.verbatim_quote}"</p>
              </blockquote>

              {/* Audio playback */}
              {hasAudio && (
                <div className="mt-3">
                  <audio
                    ref={audioRef}
                    src={`/api/meetings/${meetingId}/audio`}
                    onEnded={() => setPlaying(false)}
                    onError={() => { setAudioError(true); setPlaying(false); }}
                    preload="none"
                  />
                  <button
                    onClick={playing ? handlePause : handlePlaySource}
                    disabled={audioError}
                    className={`flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full transition-colors ${
                      audioError
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                        : playing
                          ? 'bg-red-50 border border-red-200 text-red-700 hover:bg-red-100'
                          : 'bg-violet-50 border border-violet-200 text-violet-700 hover:bg-violet-100'
                    }`}
                  >
                    <span>{playing ? '⏸' : '▶'}</span>
                    {audioError ? 'Audio unavailable' : playing ? 'Pause' : 'Play Source'}
                    {item.timestamp && !audioError && (
                      <span className="font-mono text-[10px] opacity-60">@ {item.timestamp}</span>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
              Quality gate · {item.gate_checks_passed}/7 passed
            </p>
            <div className="space-y-2">
              {['Owner identified','Clear action verb','Deadline present','No hedging language','Specific deliverable','No open conditions','Evidence cited'].map((check, i) => {
                const ok = i < item.gate_checks_passed;
                return (
                  <div key={check} className="flex items-center gap-2.5 text-xs">
                    <span className={`w-4 h-4 rounded-full flex items-center justify-center shrink-0 text-[10px] font-bold ${ok ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-400'}`}>
                      {ok ? '✓' : '✗'}
                    </span>
                    <span className={ok ? 'text-slate-700' : 'text-slate-400'}>{check}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {Object.keys(item.confidence_dimensions).length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">
                Confidence · {Math.round(item.routing_confidence * 100)}%
              </p>
              <div className="space-y-3">
                {Object.entries(item.confidence_dimensions).map(([key, dim]) => (
                  <div key={key}>
                    <div className="flex justify-between mb-1.5">
                      <span className="text-xs text-slate-500">{dimLabels[key] || key}</span>
                      <span className="text-xs font-mono text-slate-700">{Math.round(dim.score * 100)}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-1.5 rounded-full" style={{
                        width: `${dim.score*100}%`,
                        backgroundColor: dim.score>=0.8?'#16A34A':dim.score>=0.6?'#D97706':'#DC2626',
                        transition: 'width 0.5s ease',
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Participant bar ──────────────────────────────────────────────────────────
function ParticipantBar({ participants }: { participants: Participant[] }) {
  if (!participants || participants.length === 0) return null;
  return (
    <div className="bg-white border border-slate-100 rounded-2xl px-5 py-3.5 flex flex-wrap items-center gap-4 u-fade-up"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)', animationDelay: '30ms' }}>
      <div className="flex items-center gap-2 shrink-0">
        <Users className="w-3.5 h-3.5 text-slate-400" />
        <span className="section-label">Participants</span>
      </div>
      <div className="w-px h-4 bg-slate-150 shrink-0" />
      <div className="flex flex-wrap gap-3">
        {participants.map(p => (
          <div key={p.name} className="flex items-center gap-2">
            <Avatar name={p.name} size="sm" />
            <div>
              <p className="text-[13px] font-medium text-slate-800 leading-none mb-0.5">{p.name}</p>
              <div className="flex items-center gap-1.5 flex-wrap">
                {p.action_count > 0 && (
                  <span className="text-[10px] text-slate-400">{p.action_count} action{p.action_count !== 1 ? 's' : ''}</span>
                )}
                {p.question_count > 0 && (
                  <span className="text-[10px] text-amber-500 font-medium">{p.question_count} question{p.question_count !== 1 ? 's' : ''}</span>
                )}
                {p.risk_count > 0 && (
                  <span className="text-[10px] text-red-500 font-medium">{p.risk_count} risk{p.risk_count !== 1 ? 's' : ''}</span>
                )}
                {p.decision_count > 0 && (
                  <span className="text-[10px] text-green-600 font-medium">{p.decision_count} decision{p.decision_count !== 1 ? 's' : ''}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Assign picker (inline — no floating positioning) ─────────────────────────
function AssignPicker({
  current, participants, onAssign, accent = 'amber',
}: {
  current: string | null;
  participants: Participant[];
  onAssign: (person: string | null) => void;
  accent?: 'amber' | 'red';
}) {
  const [open, setOpen] = useState(false);
  const accentCls = accent === 'red'
    ? 'text-red-600 border-red-200 hover:border-red-300'
    : 'text-amber-600 border-amber-200 hover:border-amber-300';

  if (!participants || participants.length === 0) {
    return (
      <span className={`flex items-center gap-1 text-xs border rounded-full px-2.5 py-0.5 opacity-40 cursor-not-allowed ${accentCls}`}>
        <UserCheck className="w-3 h-3" />
        No participants
      </span>
    );
  }

  if (current) {
    return (
      <button
        onClick={e => { e.stopPropagation(); onAssign(null); }}
        className="flex items-center gap-1.5 text-xs bg-white border border-slate-200 rounded-full px-2 py-0.5 hover:border-red-200 transition-colors">
        <Avatar name={current} size="xs" />
        <span className="font-medium text-slate-700">{current}</span>
        <X className="w-2.5 h-2.5 text-slate-400" />
      </button>
    );
  }

  return (
    <div style={{ display: 'inline-block' }}>
      {!open ? (
        <button
          onClick={e => { e.stopPropagation(); e.preventDefault(); setOpen(true); }}
          className={`flex items-center gap-1 text-xs border rounded-full px-2.5 py-0.5 hover:bg-white transition-colors ${accentCls}`}>
          <UserCheck className="w-3 h-3" />
          Assign
        </button>
      ) : (
        <div className="flex flex-wrap gap-1" onClick={e => e.stopPropagation()}>
          {participants.map(p => (
            <button key={p.name}
              onClick={e => { e.stopPropagation(); onAssign(p.name); setOpen(false); }}
              className="flex items-center gap-1 text-xs bg-white border border-slate-200 rounded-full px-2 py-0.5 hover:bg-violet-50 hover:border-violet-200 transition-colors">
              <Avatar name={p.name} size="xs" />
              <span className="text-slate-700">{p.name}</span>
            </button>
          ))}
          <button
            onClick={e => { e.stopPropagation(); setOpen(false); }}
            className="flex items-center text-xs text-slate-400 hover:text-slate-600 px-1">
            <X className="w-3 h-3" />
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Action card ─────────────────────────────────────────────────────────────
function ActionCard({
  item, onViewEvidence, index, participants, onAssign,
}: {
  item: ActionItem;
  onViewEvidence: (i: ActionItem) => void;
  index: number;
  participants: Participant[];
  onAssign?: (actionId: string, person: string | null) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const s = STATUS[item.routing_band];

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      className={`action-card${expanded ? ' is-expanded' : ''} relative bg-white rounded-2xl border border-slate-100 cursor-pointer flex flex-col overflow-visible select-none u-fade-up`}
      style={{
        boxShadow: expanded
          ? '0 8px 28px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.05)'
          : '0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.04)',
        animationDelay: `${index * 48}ms`,
      }}
    >
      {/* Left accent bar */}
      <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-2xl" style={{ backgroundColor: s.accent }} />

      {/* Card body */}
      <div className="p-5 pl-[18px] flex-1">
        <span className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-0.5 rounded-full mb-3.5 ${s.chip}`}>
          {item.routing_band === 'AUTO'
            ? <CheckCircle className="w-3 h-3" />
            : <AlertTriangle className="w-3 h-3" />}
          {s.label}
        </span>

        <p className="text-[15px] font-[500] text-slate-900 leading-snug mb-4">{item.title}</p>

        <div className="space-y-1.5 text-[13px] text-slate-500">
          {item.owner ? (
            <div className="flex items-center gap-2">
              <Avatar name={item.owner} size="xs" />
              <span className="text-slate-700 font-medium">{item.owner}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-red-500 text-xs">
              <AlertTriangle className="w-3 h-3" /> No owner
            </div>
          )}
          {item.deadline && (
            <div className="flex items-center gap-2">
              <Calendar className="w-3.5 h-3.5 shrink-0 text-slate-350" />
              <span>Due {fmtDate(item.deadline)}</span>
            </div>
          )}
          {item.citation?.includes('SLIDE') && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-violet-600 bg-violet-50 border border-violet-100 rounded-full px-2 py-0.5">
              <BarChart3 className="w-3 h-3" />
              Slide
            </span>
          )}
          {item.ticket_id && (
            <a href={item.ticket_url || '#'} target="_blank" rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border transition-colors ${
                item.ticket_url && !item.ticket_url.includes('jira.example.com')
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100'
                  : 'bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100'
              }`}>
              <ExternalLink className="w-3 h-3 shrink-0" />
              {item.ticket_url && !item.ticket_url.includes('jira.example.com') ? 'View in Jira' : item.ticket_id}
            </a>
          )}
        </div>
      </div>

      {/* Smooth accordion expand */}
      <div className={`accordion-wrap ${expanded ? 'is-open' : ''}`}>
        <div>
          <div className="border-t border-slate-100 p-4 pl-[18px] space-y-3">
            {item.verbatim_quote && (
              <blockquote className="text-xs text-slate-500 italic pl-3 border-l-2 border-slate-200 leading-relaxed">
                "{item.verbatim_quote}"
              </blockquote>
            )}

            {/* CLARIFY — resolution steps */}
            {item.routing_band === 'CLARIFY' && (
              <div className="bg-red-50 border border-red-100 rounded-xl p-3.5 space-y-3">
                <p className="text-[11px] font-bold text-red-800 uppercase tracking-wider">How to resolve</p>
                {item.blocked_reasons.length > 0 && (
                  <div className="space-y-1.5">
                    {item.blocked_reasons.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-red-700">
                        <span className="text-red-400 font-bold shrink-0 mt-px">✗</span>
                        {r}
                      </div>
                    ))}
                  </div>
                )}
                {item.clarifying_question && (
                  <div className="border-t border-red-100 pt-2.5">
                    <p className="text-[10px] font-bold text-red-600 uppercase tracking-wider mb-1">Ask this</p>
                    <p className="text-xs text-red-800 leading-relaxed">"{item.clarifying_question}"</p>
                  </div>
                )}
                {!item.owner && participants.length > 0 && (
                  <div className="border-t border-red-100 pt-2.5 flex items-center gap-2">
                    <span className="text-xs text-red-600">Assign to:</span>
                    <AssignPicker current={null} participants={participants} onAssign={person => onAssign?.(item.action_id, person)} accent="red" />
                  </div>
                )}
              </div>
            )}

            {/* REVIEW — suggested edits diff */}
            {item.routing_band === 'REVIEW' && item.suggested_edits.length > 0 && (
              <div className="bg-amber-50 border border-amber-100 rounded-xl p-3.5 space-y-2.5">
                <p className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">Suggested changes</p>
                {item.suggested_edits.map((e, i) => (
                  <div key={i} className="space-y-1">
                    <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider">{e.field}</p>
                    <div className="flex flex-col gap-1 text-xs pl-2">
                      <span className="text-slate-400 line-through leading-snug">{e.current || '(not set)'}</span>
                      <span className="text-amber-900 font-medium leading-snug">→ {e.suggestion}</span>
                    </div>
                    {e.reason && <p className="text-[10px] text-amber-600 pl-2 italic">{e.reason}</p>}
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={ev => { ev.stopPropagation(); onViewEvidence(item); }}
              className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1.5 transition-colors">
              <Eye className="w-3 h-3" /> View evidence & confidence
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Open question card ───────────────────────────────────────────────────────
function OpenQuestionCard({
  question: rawQ, index, participants, assignees, onAssign,
}: {
  question: OpenQuestion | string;
  index: number;
  participants: Participant[];
  assignees: Record<string, string | null>;
  onAssign: (qid: string, person: string | null) => void;
}) {
  const q = normalizeQuestion(rawQ, index);
  const assignee = assignees[q.question_id] ?? q.assignee;
  const [resolved, setResolved] = useState(false);

  if (resolved) {
    return (
      <div className="soft-card bg-green-50 border border-green-100 rounded-2xl p-5"
        style={{ boxShadow: '0 1px 3px rgba(22,163,74,0.08)' }}>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-green-100 border border-green-200 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-4 h-4 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[13px] text-slate-500 line-through truncate">{q.question}</p>
            <p className="text-[11px] text-green-600 font-medium mt-0.5">Resolved{assignee ? ` · ${assignee}` : ''}</p>
          </div>
          <button onClick={() => setResolved(false)}
            className="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">
            Undo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="soft-card bg-amber-50 border border-amber-100 rounded-2xl p-5"
      style={{ boxShadow: '0 1px 3px rgba(217,119,6,0.08)' }}>
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-white border border-amber-200 flex items-center justify-center shrink-0 mt-0.5">
          <HelpCircle className="w-4 h-4 text-amber-600" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-bold text-amber-700 uppercase tracking-wider">Question</span>
            <span className="text-[10px] font-mono text-amber-500/60">{q.question_id}</span>
          </div>
          <p className="text-[14px] text-slate-800 leading-snug mb-3">{q.question}</p>

          <div className="flex items-center gap-3 flex-wrap">
            {q.asker && (
              <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                <Avatar name={q.asker} size="xs" />
                <span>Asked by <span className="font-medium text-slate-700">{q.asker}</span></span>
              </div>
            )}
            <div className="flex items-center gap-1.5 flex-wrap">
              <MessageCircle className="w-3 h-3 text-amber-500" />
              <span className="text-[11px] text-amber-600 font-medium">Unresolved</span>
              <span className="text-[11px] text-slate-400">—</span>
              <AssignPicker
                current={assignee ?? null}
                participants={participants}
                onAssign={person => onAssign(q.question_id, person)}
                accent="amber"
              />
              {assignee && (
                <button
                  onClick={e => { e.stopPropagation(); setResolved(true); }}
                  className="flex items-center gap-1 text-xs bg-green-50 border border-green-200 text-green-700 rounded-full px-2.5 py-0.5 hover:bg-green-100 transition-colors font-medium">
                  <CheckCircle2 className="w-3 h-3" />
                  Resolved
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Risk card ────────────────────────────────────────────────────────────────
function RiskCard({ risk, participants, assignee, onAssign }: {
  risk: Risk; participants: Participant[];
  assignee?: string | null;
  onAssign?: (riskId: string, person: string | null) => void;
}) {
  const sev = SEVERITY_TOKENS[risk.severity] || SEVERITY_TOKENS.medium;
  const resolvedOwner = assignee ?? risk.owner;
  return (
    <div className="soft-card rounded-2xl border p-5"
      style={{ backgroundColor: sev.bg, borderColor: sev.border, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
      <div className="flex items-start gap-3">
        <div className="w-7 h-7 rounded-full bg-white flex items-center justify-center shrink-0 mt-0.5"
          style={{ border: `1.5px solid ${sev.color}30` }}>
          <Shield className="w-4 h-4" style={{ color: sev.color }} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: sev.color }}>
              {sev.label}
            </span>
            <span className="text-[10px] font-mono opacity-40">{risk.risk_id}</span>
          </div>
          <p className="text-[14px] text-slate-800 leading-snug font-medium mb-2.5">{risk.description}</p>

          {risk.mitigation && (
            <div className="flex items-start gap-1.5 text-xs text-slate-600 mb-2.5">
              <span className="text-slate-400 shrink-0 mt-0.5 font-bold">→</span>
              <span>{risk.mitigation}</span>
            </div>
          )}

          {resolvedOwner ? (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
              <Avatar name={resolvedOwner} size="xs" />
              <span className="font-medium text-slate-700">{resolvedOwner}</span>
              {participants.length > 0 && onAssign && (
                <AssignPicker current={resolvedOwner} participants={participants}
                  onAssign={person => onAssign(risk.risk_id, person)} accent="amber" />
              )}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-[11px] text-red-600">
              <AlertTriangle className="w-3 h-3" />
              <span>No owner</span>
              {participants.length > 0 && onAssign && (
                <AssignPicker current={null} participants={participants}
                  onAssign={person => onAssign(risk.risk_id, person)} accent="red" />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Missed Commitments ───────────────────────────────────────────────────────
function MissedCommitmentsSection({ commitments }: { commitments: MissedCommitment[] }) {
  if (!commitments.length) return null;
  const confColor = (c: string) =>
    c === 'high' ? 'text-red-600' : c === 'medium' ? 'text-amber-600' : 'text-slate-500';
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        <h2 className="text-base font-semibold text-slate-900">Missed Commitments</h2>
        <span className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-full px-2 py-0.5 font-medium">
          {commitments.length} detected
        </span>
        <span className="text-xs text-slate-400">· vague language that didn't pass the quality gate</span>
      </div>
      <div className="space-y-3">
        {commitments.map(c => (
          <div key={c.commitment_id}
            className="bg-amber-50/60 border border-amber-200/80 rounded-2xl p-5"
            style={{ boxShadow: '0 1px 3px rgba(217,119,6,0.06)' }}>
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-amber-100 border border-amber-200 flex items-center justify-center shrink-0 mt-0.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-bold text-amber-700 uppercase tracking-wider mb-2">
                  Potential Commitment
                </p>
                <blockquote className="text-[14px] text-slate-700 leading-snug italic border-l-2 border-amber-300 pl-3 mb-3">
                  "{c.sentence}"
                </blockquote>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
                  {c.inferred_owner && (
                    <span className="text-slate-600">
                      Owner: <span className="font-medium text-slate-800">{c.inferred_owner}</span>
                      <span className="text-slate-400 ml-1">(inferred)</span>
                    </span>
                  )}
                  {c.missing_fields.map(f => (
                    <span key={f} className="flex items-center gap-1 text-red-600">
                      <X className="w-3 h-3" />
                      {f.charAt(0).toUpperCase() + f.slice(1)}: Missing
                    </span>
                  ))}
                  <span className={`font-medium ${confColor(c.confidence)}`}>
                    Confidence: {c.confidence.charAt(0).toUpperCase() + c.confidence.slice(1)}
                  </span>
                </div>
                {c.reason && (
                  <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">{c.reason}.</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Accountability Score Breakdown ───────────────────────────────────────────
const DIM_LABELS: Record<string, string> = {
  ownership_clarity:  'Owners assigned',
  action_clarity:     'Action specificity',
  evidence_quality:   'Evidence quality',
  deadline_presence:  'Deadline coverage',
  ambiguity_rate:     'Ambiguity control',
  risk_coverage:      'Risk documentation',
};

function AccountabilityBreakdown({
  score, grade, breakdown, strengths, weaknesses, prediction,
  missedCount, unresolvedQuestions,
}: {
  score: number; grade: string;
  breakdown?: Record<string, { score: number; weighted: number; detail: string }>;
  strengths?: string[]; weaknesses?: string[]; prediction?: string;
  missedCount: number; unresolvedQuestions: number;
}) {
  const hColor = score >= 80 ? '#16A34A' : score >= 60 ? '#D97706' : '#DC2626';
  const hLabel = score >= 80 ? 'Strong' : score >= 60 ? 'Moderate' : 'At Risk';

  // Build + and - signals
  const positives: string[] = [...(strengths ?? [])];
  const negatives: string[] = [...(weaknesses ?? [])];
  if (missedCount > 0) negatives.push(`${missedCount} vague commitment${missedCount > 1 ? 's' : ''} detected`);
  if (unresolvedQuestions > 0) negatives.push(`${unresolvedQuestions} unresolved question${unresolvedQuestions > 1 ? 's' : ''}`);

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-6"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>

      {/* Header */}
      <div className="flex items-end justify-between mb-5">
        <div className="flex items-baseline gap-2">
          <span className="text-5xl font-bold text-slate-900"
            style={{ fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>
            {score}
          </span>
          <span className="text-slate-400 text-xl">/&nbsp;100</span>
        </div>
        <div className="text-right">
          <span className="text-sm font-semibold px-3 py-1.5 rounded-xl block mb-1"
            style={{ backgroundColor: `${hColor}15`, color: hColor }}>
            Grade {grade} · {hLabel}
          </span>
          {prediction && (
            <p className="text-[11px] text-slate-400">{prediction}</p>
          )}
        </div>
      </div>

      {/* Execution Readiness bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Execution Readiness</span>
          <span className="text-xs font-mono text-slate-500">{score}%</span>
        </div>
        <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-2.5 rounded-full transition-all duration-700 ease-out"
            style={{ width: `${score}%`, backgroundColor: hColor }} />
        </div>
      </div>

      {/* Signals grid */}
      {(positives.length > 0 || negatives.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-5">
          {positives.length > 0 && (
            <div className="space-y-1.5">
              {positives.map((s, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-slate-600">
                  <span className="text-emerald-500 font-bold shrink-0 mt-px">+</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          )}
          {negatives.length > 0 && (
            <div className="space-y-1.5">
              {negatives.map((w, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-slate-500">
                  <span className="text-red-400 font-bold shrink-0 mt-px">−</span>
                  <span>{w}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dimension breakdown */}
      {breakdown && Object.keys(breakdown).length > 0 && (
        <div>
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-3">Score breakdown</p>
          <div className="space-y-2.5">
            {Object.entries(breakdown).map(([key, dim]) => (
              <div key={key}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-slate-500">{DIM_LABELS[key] || key}</span>
                  <span className="text-xs font-mono text-slate-600">{Math.round(dim.score * 100)}%</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-1.5 rounded-full transition-all duration-700 ease-out"
                    style={{
                      width: `${dim.score * 100}%`,
                      backgroundColor: dim.score >= 0.8 ? '#16A34A' : dim.score >= 0.6 ? '#D97706' : '#DC2626',
                    }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Pipeline row ─────────────────────────────────────────────────────────────
function PipelineRow({ stage, stageDetail, isRunning }: {
  stage: string; stageDetail?: string; isRunning: boolean;
}) {
  const [open, setOpen] = useState(isRunning);
  const currentIdx = STAGE_ORDER.indexOf(stage);
  return (
    <div className="bg-white rounded-2xl border border-slate-100"
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50/80 transition-colors text-left rounded-2xl">
        <div className="w-6 h-6 rounded-lg bg-violet-50 flex items-center justify-center shrink-0">
          <Zap className="w-3.5 h-3.5 text-violet-600" />
        </div>
        <span className="text-sm font-medium text-slate-700">AI Pipeline</span>
        {isRunning ? (
          <span className="flex items-center gap-1.5 text-xs text-amber-600 ml-1">
            <Loader2 className="w-3 h-3 animate-spin" />
            {stageDetail || STAGE_LABELS[stage]}
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-xs text-emerald-600 ml-1">
            <CheckCircle className="w-3 h-3" /> Complete
          </span>
        )}
        <ChevronDown className={`pipeline-chevron${open ? ' is-open' : ''} w-4 h-4 text-slate-400 ml-auto`} />
      </button>

      <div className={`accordion-wrap ${open ? 'is-open' : ''}`}>
        <div>
          <div className="border-t border-slate-100 px-5 py-4 flex flex-wrap gap-x-5 gap-y-2.5">
            {STAGE_ORDER.slice(0, -1).map((s, i) => {
              const done   = currentIdx > i || stage === 'complete';
              const active = s === stage;
              return (
                <div key={s} className="flex items-center gap-1.5 text-xs">
                  {done   ? <CheckCircle className="w-3 h-3 text-emerald-500" />
                          : active ? <Loader2 className="w-3 h-3 text-amber-500 animate-spin" />
                                   : <Clock className="w-3 h-3 text-slate-300" />}
                  <span className={active ? 'text-amber-600 font-medium' : done ? 'text-slate-600' : 'text-slate-300'}>
                    {STAGE_LABELS[s]}
                  </span>
                  {STAGE_TOOLS[s] && (
                    <span className="text-slate-300 text-[11px]">· {STAGE_TOOLS[s]}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Loading state ────────────────────────────────────────────────────────────
const STAGE_DESCRIPTIONS: Record<string, string> = {
  transcription: 'Converting speech to text with speaker diarization',
  extraction:    'Nova Lite reading the transcript for owners, deadlines & decisions',
  enrichment:    'Linking evidence citations to each action item',
  quality_gate:  'Running 7 deterministic checks — hedging, ownership, specificity',
  confidence:    'Scoring each item across 5 confidence dimensions',
  health_score:  'Computing meeting health and execution prediction',
  execution:     'Routing to AUTO → Jira · REVIEW → edits · CLARIFY → questions',
  complete:      'Analysis complete',
};

const STAGE_COLORS: Record<string, string> = {
  transcription: '#2563EB',
  extraction:    '#7C3AED',
  enrichment:    '#0891B2',
  quality_gate:  '#D97706',
  confidence:    '#7C3AED',
  health_score:  '#059669',
  execution:     '#16A34A',
  complete:      '#16A34A',
};

function LoadingView({ stage, stageDetail, transcript, wordCount, progress, meetingId }: {
  stage: string; stageDetail?: string; transcript?: string;
  wordCount?: number; progress: number; meetingId: string;
}) {
  const [displayed, setDisplayed] = useState('');
  const [elapsed, setElapsed]     = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!transcript) return;
    setDisplayed(''); let i = 0;
    const t = setInterval(() => {
      i += 6; setDisplayed(transcript.slice(0, i));
      if (i >= transcript.length) clearInterval(t);
    }, 16);
    return () => clearInterval(t);
  }, [transcript]);

  const currentIdx = STAGE_ORDER.indexOf(stage);
  const BARS = [0.4, 0.8, 0.6, 1, 0.5, 0.9, 0.7, 1, 0.4, 0.8, 0.6, 0.9, 0.5, 1, 0.7, 0.3, 0.7, 1, 0.6];
  const activeColor = STAGE_COLORS[stage] || '#7C3AED';

  return (
    <div className="min-h-[calc(100vh-49px)] bg-[#0F172A] flex flex-col items-center justify-center px-5 py-16 u-fade-in">

      {/* Waveform */}
      <div className="flex items-center justify-center gap-[3px] h-14 mb-10">
        {BARS.map((h, i) => (
          <div key={i} className="w-[3px] rounded-full"
            style={{
              height: '100%', transformOrigin: 'center',
              backgroundColor: activeColor,
              animation: `dpWave ${0.7 + (i % 5) * 0.13}s ease-in-out infinite alternate`,
              animationDelay: `${i * 55}ms`,
              opacity: 0.25 + h * 0.7,
              transform: `scaleY(${h * 0.5})`,
            }} />
        ))}
      </div>

      {/* Stage heading */}
      <p className="text-[11px] font-bold uppercase tracking-widest mb-2" style={{ color: activeColor }}>
        {stage === 'not_started' || !stage ? 'Initializing' : STAGE_LABELS[stage] || 'Processing'}
      </p>
      <h2 className="text-2xl font-bold text-white mb-2 text-center">
        Analyzing your meeting
      </h2>
      <p className="text-sm text-slate-400 mb-10 text-center max-w-sm leading-relaxed">
        {stageDetail || STAGE_DESCRIPTIONS[stage] || 'Starting the AI pipeline…'}
      </p>

      {/* Pipeline stage tracker */}
      <div className="w-full max-w-md bg-slate-800/60 border border-slate-700/60 rounded-2xl overflow-hidden mb-8">
        {/* Progress bar at top */}
        <div className="h-[3px] bg-slate-700">
          <div className="h-[3px] transition-all duration-700 ease-out rounded-full"
            style={{ width: `${progress}%`, backgroundColor: activeColor }} />
        </div>

        <div className="p-5 space-y-0">
          {STAGE_ORDER.slice(0, -1).map((s, i) => {
            const done   = currentIdx > i || stage === 'complete';
            const active = s === stage;
            const waiting = !done && !active;
            return (
              <div key={s} className={`flex items-center gap-4 py-2.5 ${i < STAGE_ORDER.length - 2 ? 'border-b border-slate-700/40' : ''}`}>
                {/* Status icon */}
                <div className="w-6 h-6 rounded-full flex items-center justify-center shrink-0">
                  {done ? (
                    <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                  ) : active ? (
                    <div className="w-5 h-5 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: `${activeColor}20` }}>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: activeColor }} />
                    </div>
                  ) : (
                    <div className="w-5 h-5 rounded-full bg-slate-700/60 flex items-center justify-center">
                      <Clock className="w-3 h-3 text-slate-600" />
                    </div>
                  )}
                </div>

                {/* Stage name + tool */}
                <div className="flex-1 min-w-0">
                  <p className={`text-[13px] font-medium leading-tight ${
                    done ? 'text-slate-400' : active ? 'text-white' : 'text-slate-600'
                  }`}>
                    {STAGE_LABELS[s]}
                  </p>
                  {active && stageDetail && (
                    <p className="text-[11px] mt-0.5" style={{ color: `${activeColor}cc` }}>{stageDetail}</p>
                  )}
                </div>

                {/* Tool badge */}
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full shrink-0 ${
                  done   ? 'bg-emerald-500/10 text-emerald-500' :
                  active ? 'text-white' : 'bg-slate-700/40 text-slate-600'
                }`}
                  style={active ? { backgroundColor: `${activeColor}20`, color: activeColor } : {}}>
                  {STAGE_TOOLS[s]}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Transcript preview (once available) */}
      {transcript && (
        <div className="w-full max-w-md u-fade-up">
          <div className="flex items-center gap-2 mb-2">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
            </span>
            <span className="text-xs text-emerald-400 font-medium">
              Transcript ready{wordCount ? ` · ${wordCount} words` : ''}
            </span>
          </div>
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-4 max-h-36 overflow-y-auto">
            <p className="text-[11px] text-slate-400 font-mono leading-relaxed whitespace-pre-wrap">{displayed}</p>
          </div>
        </div>
      )}

      {/* Footer */}
      <p className="text-[11px] text-slate-600 font-mono mt-8">
        {elapsed}s elapsed · {progress}% complete · {meetingId}
      </p>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function AnalysisPageClient({ initialData }: { initialData?: AnalysisResult | null }) {
  const params    = useParams();
  const meetingId = params.id as string;
  const [result, setResult]             = useState<AnalysisResult | null>(initialData ?? null);
  const [evidenceItem, setEvidenceItem] = useState<ActionItem | null>(null);
  // Local assignee overrides for open questions (not persisted to backend)
  const [questionAssignees, setQuestionAssignees] = useState<Record<string, string | null>>({});
  // Local assignee overrides for action items
  const [actionAssignees, setActionAssignees] = useState<Record<string, string | null>>({});
  // Local assignee overrides for risks
  const [riskAssignees, setRiskAssignees] = useState<Record<string, string | null>>({});

  useEffect(() => {
    // Already have final data from server-side prefetch — no polling needed
    if (result?.status === 'complete' || result?.status === 'error') return;
    let interval: ReturnType<typeof setInterval>;
    let started = false;
    let retries = 0;
    const fetchResults = async (): Promise<AnalysisResult | null> => {
      try {
        const res = await fetch(`/api/meetings/${meetingId}/results`);
        if (!res.ok) return null;
        return await res.json();
      } catch { return null; }
    };
    const start = async () => {
      // Retry up to 3 times on initial load (handles transient Cloudflare/tunnel hiccups)
      let existing: AnalysisResult | null = null;
      while (!existing && retries < 3) {
        existing = await fetchResults();
        if (!existing) { retries++; await new Promise(r => setTimeout(r, 800)); }
      }
      if (!existing) {
        setResult({ meeting_id: meetingId, status: 'error', stage: 'error', progress: 0, error: 'Could not connect to analysis server. Please refresh.' });
        return;
      }
      if (existing.status === 'complete' || existing.status === 'error') { setResult(existing); return; }
      if (!started && existing.status !== 'running') {
        await fetch(`/api/meetings/${meetingId}/analyze`, { method: 'POST' }).catch(() => {});
        started = true;
      }
      interval = setInterval(async () => {
        const data = await fetchResults();
        if (!data) return; // skip on transient error, keep polling
        setResult(data);
        if (data.status === 'complete' || data.status === 'error') clearInterval(interval);
      }, 700);
    };
    start();
    return () => clearInterval(interval);
  }, [meetingId]);

  const isRunning  = !result || result.status === 'running' || result.status === 'not_started';
  const isComplete = result?.status === 'complete';
  const isError    = result?.status === 'error';
  const items      = result?.action_items || [];
  const participants = result?.participants || [];
  const risks        = result?.risks || [];
  const rawQuestions = result?.open_questions || [];
  const questions    = rawQuestions.map((q, i) => normalizeQuestion(q, i));

  // Split action items by routing band
  const autoItems    = items.filter(i => i.routing_band === 'AUTO');
  const reviewItems  = items.filter(i => i.routing_band === 'REVIEW');
  const clarifyItems = items.filter(i => i.routing_band === 'CLARIFY');

  const autoCount = autoItems.length;
  const needAttn  = reviewItems.length + clarifyItems.length;
  const score     = result?.health_score ?? 0;
  const hColor    = score >= 80 ? '#16A34A' : score >= 60 ? '#D97706' : '#DC2626';
  const hLabel    = result?.health_grade ?? (score >= 80 ? 'Good' : score >= 60 ? 'Moderate' : 'At Risk');

  const meetingTitle = (() => {
    if (!result?.nova_summary) return null;
    const first = result.nova_summary.split('.')[0];
    return first.replace(/^(The meeting|This meeting|In this meeting|The team|The participants)[,\s]*/i, '').trim();
  })();

  // Stagger delay helper: sections start after all action items have entered
  const sectionDelay = (extra: number) => `${(items.length * 48) + extra}ms`;

  const handleAssignQuestion = (qid: string, person: string | null) => {
    setQuestionAssignees(prev => ({ ...prev, [qid]: person }));
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900">
      <style dangerouslySetInnerHTML={{ __html: GLOBAL_CSS }} />

      {/* ── Sticky nav ────────────────────────────────────────────────────── */}
      <header className="bg-[#0F172A] border-b border-slate-800 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-5 py-3 flex items-center gap-3">
          <div className="flex items-center gap-2.5 shrink-0">
            <div className="w-6 h-6 rounded-md bg-violet-600 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-white text-sm tracking-tight">DecisionPilot</span>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />
          <span className="text-slate-400 text-xs font-mono truncate max-w-[180px]">{meetingId}</span>
          {isRunning && (
            <div className="flex items-center gap-1.5 text-xs text-violet-400 ml-1">
              <Loader2 className="w-3 h-3 animate-spin" /> {result?.progress ?? 0}%
            </div>
          )}
          <div className="ml-auto flex items-center gap-3">
            {isComplete && <ExportMenu result={result} />}
            <a href="/"
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1.5">
              <ArrowLeft className="w-3.5 h-3.5" /> New
            </a>
          </div>
        </div>
        {isRunning && (
          <div className="h-[2px] bg-slate-800">
            <div className="h-[2px] bg-violet-500 transition-all duration-700"
              style={{ width: `${result?.progress ?? 0}%` }} />
          </div>
        )}
      </header>

      {isRunning && (
        <LoadingView
          stage={result?.stage || 'not_started'}
          stageDetail={result?.stage_detail}
          transcript={result?.transcript_preview}
          wordCount={result?.word_count}
          progress={result?.progress ?? 0}
          meetingId={meetingId} />
      )}

      {isError && (
        <div className="max-w-5xl mx-auto px-5 py-16 text-center u-fade-in">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
          <p className="text-base font-semibold text-slate-800 mb-2">Analysis failed</p>
          <p className="text-sm text-slate-500">{result?.error}</p>
        </div>
      )}

      {isComplete && (
        <div className="max-w-5xl mx-auto px-5 py-10 space-y-8">

          {/* ── 1. Meeting header ──────────────────────────────────────────── */}
          <div className="u-fade-up">
            <div className="-mx-5 px-5 pt-8 pb-8 rounded-b-[20px]"
              style={{ background: 'linear-gradient(180deg, rgba(124,58,237,0.05) 0%, rgba(248,250,252,0) 100%)' }}>
              <p className="section-label mb-3">Meeting Analysis</p>
              {meetingTitle && (
                <h1 className="text-[28px] font-bold text-slate-900 leading-tight max-w-3xl mb-5">
                  {meetingTitle}
                </h1>
              )}
              <div className="flex flex-wrap items-center gap-2 mb-4">
                {result.health_score !== undefined && (
                  <span className="inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-xl"
                    style={{ backgroundColor: `${hColor}15`, color: hColor }}>
                    <BarChart3 className="w-3.5 h-3.5" /> Health {result.health_score}
                  </span>
                )}
                {items.length > 0 && (
                  <span className="inline-flex items-center text-sm text-slate-600 bg-slate-100 px-3 py-1 rounded-xl">
                    {items.length} action{items.length !== 1 ? 's' : ''}
                  </span>
                )}
                {autoCount > 0 && (
                  <span className="inline-flex items-center gap-1.5 text-sm text-green-700 bg-green-50 border border-green-100 px-3 py-1 rounded-xl">
                    <CheckCircle className="w-3.5 h-3.5" /> {autoCount} executed
                  </span>
                )}
                {needAttn > 0 && (
                  <span className="inline-flex items-center gap-1.5 text-sm text-red-700 bg-red-50 border border-red-100 px-3 py-1 rounded-xl">
                    <AlertTriangle className="w-3.5 h-3.5" /> {needAttn} need attention
                  </span>
                )}
                {(result.decisions?.length ?? 0) > 0 && (
                  <span className="inline-flex items-center text-sm text-slate-600 bg-slate-100 px-3 py-1 rounded-xl">
                    {result.decisions!.length} decision{result.decisions!.length !== 1 ? 's' : ''}
                  </span>
                )}
                {result.word_count && (
                  <span className="inline-flex items-center text-sm text-slate-400 bg-slate-50 border border-slate-100 px-3 py-1 rounded-xl">
                    {result.word_count} words
                  </span>
                )}
              </div>
              {result.nova_summary && (
                <p className="text-[15px] text-slate-500 leading-relaxed max-w-3xl">
                  {result.nova_summary}
                </p>
              )}
            </div>
          </div>

          {/* ── 2. Participants ────────────────────────────────────────────── */}
          {participants.length > 0 && (
            <ParticipantBar participants={participants} />
          )}

          {/* ── 3a. Executed action items ──────────────────────────────────── */}
          {autoItems.length > 0 && (
            <section className="u-fade-up" style={{ animationDelay: '60ms' }}>
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <h2 className="text-base font-semibold text-slate-900">Executed</h2>
                <span className="text-xs text-green-600 bg-green-50 border border-green-100 rounded-full px-2 py-0.5 font-medium">
                  {autoItems.length} auto-committed
                </span>
                {result?.routing_summary?.jira_live ? (
                  <span className="flex items-center gap-1 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-full px-2 py-0.5 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block" />
                    Live Jira
                  </span>
                ) : (
                  <span className="text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded-full px-2 py-0.5">
                    Mock tickets
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {autoItems.map((item, i) => (
                  <ActionCard key={item.action_id} item={item} index={i}
                    onViewEvidence={setEvidenceItem} participants={participants}
                    onAssign={(id, p) => setActionAssignees(prev => ({ ...prev, [id]: p }))} />
                ))}
              </div>
            </section>
          )}

          {/* ── 3b. Review action items ────────────────────────────────────── */}
          {reviewItems.length > 0 && (
            <section className="u-fade-up" style={{ animationDelay: `${autoItems.length * 48 + 60}ms` }}>
              <div className="flex items-center gap-2 mb-4">
                <Eye className="w-4 h-4 text-amber-600" />
                <h2 className="text-base font-semibold text-slate-900">Needs Review</h2>
                <span className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-full px-2 py-0.5 font-medium">
                  {reviewItems.length} item{reviewItems.length !== 1 ? 's' : ''} · edits suggested
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {reviewItems.map((item, i) => (
                  <ActionCard key={item.action_id} item={item} index={autoItems.length + i}
                    onViewEvidence={setEvidenceItem} participants={participants} />
                ))}
              </div>
            </section>
          )}

          {/* ── 3c. Clarify action items ───────────────────────────────────── */}
          {clarifyItems.length > 0 && (
            <section className="u-fade-up" style={{ animationDelay: `${(autoItems.length + reviewItems.length) * 48 + 60}ms` }}>
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <h2 className="text-base font-semibold text-slate-900">Execution Risks</h2>
                <span className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-full px-2 py-0.5 font-medium">
                  {clarifyItems.length} blocked · click to resolve
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {clarifyItems.map((item, i) => (
                  <ActionCard key={item.action_id} item={item} index={autoItems.length + reviewItems.length + i}
                    onViewEvidence={setEvidenceItem} participants={participants} />
                ))}
              </div>
            </section>
          )}

          {/* ── 4. Decisions + Open Questions ──────────────────────────────── */}
          {((result.decisions?.length ?? 0) > 0 || questions.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

              {result.decisions && result.decisions.length > 0 && (
                <section className="u-fade-up" style={{ animationDelay: sectionDelay(80) }}>
                  <div className="flex items-center gap-2 mb-4">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    <h2 className="text-base font-semibold text-slate-900">Decisions</h2>
                  </div>
                  <div className="space-y-3">
                    {result.decisions.map((d, i) => (
                      <div key={i}
                        className="soft-card bg-green-50 border border-green-100 rounded-2xl p-5 flex items-start gap-3.5"
                        style={{ boxShadow: '0 1px 3px rgba(22,163,74,0.08)' }}>
                        <div className="w-7 h-7 rounded-full bg-white border border-green-200 flex items-center justify-center shrink-0 mt-0.5">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-[11px] font-bold text-green-700 uppercase tracking-wider mb-1.5">Decision</p>
                          <p className="text-[15px] text-slate-800 leading-snug font-medium">{d.title}</p>
                          {d.citation && (
                            <p className="text-xs text-green-700/60 mt-2 italic">"{d.citation}"</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {questions.length > 0 && (
                <section className="u-fade-up" style={{ animationDelay: sectionDelay(130) }}>
                  <div className="flex items-center gap-2 mb-4">
                    <HelpCircle className="w-4 h-4 text-amber-600" />
                    <h2 className="text-base font-semibold text-slate-900">Open Questions</h2>
                    <span className="text-xs text-amber-600 bg-amber-50 border border-amber-100 rounded-full px-2 py-0.5 font-medium">
                      {questions.filter(q => !(questionAssignees[q.question_id] ?? q.assignee)).length} unassigned
                    </span>
                  </div>
                  <div className="space-y-3">
                    {questions.map((q, i) => (
                      <OpenQuestionCard
                        key={q.question_id}
                        question={q}
                        index={i}
                        participants={participants}
                        assignees={questionAssignees}
                        onAssign={handleAssignQuestion}
                      />
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}

          {/* ── 5. Risks ───────────────────────────────────────────────────── */}
          {risks.length > 0 && (
            <section className="u-fade-up" style={{ animationDelay: sectionDelay(180) }}>
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-4 h-4 text-red-500" />
                <h2 className="text-base font-semibold text-slate-900">Risks</h2>
                {risks.filter(r => r.severity === 'high').length > 0 && (
                  <span className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-full px-2 py-0.5 font-medium">
                    {risks.filter(r => r.severity === 'high').length} high severity
                  </span>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {risks.map(r => (
                  <RiskCard key={r.risk_id} risk={r} participants={participants}
                    assignee={riskAssignees[r.risk_id] ?? null}
                    onAssign={(id, person) => setRiskAssignees(prev => ({ ...prev, [id]: person }))} />
                ))}
              </div>
            </section>
          )}

          {/* ── 5b. Missed Commitments ─────────────────────────────────────── */}
          {(result.missed_commitments?.length ?? 0) > 0 && (
            <div className="u-fade-up" style={{ animationDelay: sectionDelay(200) }}>
              <MissedCommitmentsSection commitments={result.missed_commitments!} />
            </div>
          )}

          {/* ── 6. Meeting Accountability Score ────────────────────────────── */}
          {result.health_score !== undefined && (
            <section className="u-fade-up" style={{ animationDelay: sectionDelay(240) }}>
              <h2 className="text-base font-semibold text-slate-900 mb-4">Meeting Accountability Score</h2>
              <AccountabilityBreakdown
                score={result.health_score}
                grade={result.health_grade ?? 'C'}
                breakdown={result.health_breakdown}
                strengths={result.health_strengths}
                weaknesses={result.health_weaknesses}
                prediction={result.execution_prediction}
                missedCount={result.missed_commitments?.length ?? 0}
                unresolvedQuestions={questions.filter(q => !(questionAssignees[q.question_id] ?? q.assignee)).length}
              />
            </section>
          )}

          {/* ── 7. AI Pipeline (collapsed) ─────────────────────────────────── */}
          <div className="u-fade-up" style={{ animationDelay: sectionDelay(300) }}>
            <PipelineRow stage={result.stage} stageDetail={result.stage_detail} isRunning={isRunning} />
          </div>

        </div>
      )}

      {evidenceItem && (
        <EvidenceDrawer
          item={evidenceItem}
          onClose={() => setEvidenceItem(null)}
          meetingId={meetingId}
          hasAudio={result?.has_audio ?? false}
        />
      )}
    </div>
  );
}
