'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import {
  Mic, FileText, Image, Zap, Ticket, ChevronRight,
  Shield, X, ClipboardPaste, CheckCircle, GitBranch,
  Loader2, Activity, ShieldCheck,
} from 'lucide-react';

// ─── Global animation / interaction CSS ──────────────────────────────────────
const HOME_CSS = `
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0);    }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes novaPulse {
    0%, 100% { box-shadow: 0 0 0 0   rgba(124,58,237,0),    0 2px 8px rgba(124,58,237,0.15); }
    50%       { box-shadow: 0 0 0 7px rgba(124,58,237,0.12), 0 4px 24px rgba(124,58,237,0.30); }
  }
  @keyframes stepIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0);   }
  }

  .u-fade-up  { animation: fadeUp 0.32s cubic-bezier(0.16,1,0.3,1) both; }
  .u-fade-in  { animation: fadeIn 0.3s ease both; }

  /* Nova glow — always on, dims when pipeline is inactive */
  .nova-idle  { animation: novaPulse 2.8s ease-in-out infinite; }

  /* Upload zone */
  .upload-zone {
    transition: border-color 0.15s ease, background 0.15s ease,
                transform 0.15s ease, box-shadow 0.15s ease;
  }
  .upload-zone:hover {
    border-color: #7C3AED;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.08);
    transform: translateY(-1px);
  }
  .upload-zone.drag-over {
    border-color: #7C3AED !important;
    background: rgba(124,58,237,0.04) !important;
    box-shadow: 0 0 0 5px rgba(124,58,237,0.10) !important;
    transform: scale(1.015);
  }
  .upload-zone.has-file {
    border-color: #16A34A;
    background: rgba(22,163,74,0.03);
  }

  /* Feature card hover */
  .feature-card {
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }
  .feature-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
  }

  /* CTA press */
  .cta-btn { transition: all 0.15s ease; }
  .cta-btn:active:not(:disabled) { transform: scale(0.98); }

  /* Timeline step entry */
  .step-item { animation: stepIn 0.22s cubic-bezier(0.16,1,0.3,1) both; }

  /* Pipeline connector fill */
  .pipe-connector {
    transition: background-color 0.5s ease;
  }
`;

// ─── Pipeline data ────────────────────────────────────────────────────────────
const PIPELINE = [
  { id: 'audio',      label: 'Audio',        sub: 'Input',          icon: Mic,         isNova: false },
  { id: 'transcribe', label: 'Transcribe',   sub: 'AWS',            icon: Activity,    isNova: false },
  { id: 'nova',       label: 'Nova Lite',    sub: 'Amazon Nova',    icon: Zap,         isNova: true  },
  { id: 'gate',       label: 'Quality Gate', sub: '7 checks',       icon: ShieldCheck, isNova: false },
  { id: 'router',     label: 'Router',       sub: 'AUTO/REVIEW',    icon: GitBranch,   isNova: false },
  { id: 'jira',       label: 'Jira',         sub: 'Execution',      icon: Ticket,      isNova: false },
];

const NODE_STYLE: Record<string, { bg: string; icon: string; ring: string }> = {
  default: { bg: 'bg-slate-100',   icon: 'text-slate-500',   ring: 'border-slate-200' },
  nova:    { bg: 'bg-violet-100',  icon: 'text-violet-600',  ring: 'border-violet-300' },
  done:    { bg: 'bg-emerald-50',  icon: 'text-emerald-600', ring: 'border-emerald-200' },
  active:  { bg: 'bg-violet-50',   icon: 'text-violet-600',  ring: 'border-violet-300' },
};

// ─── Pipeline visualization ───────────────────────────────────────────────────
function PipelineViz({ activeIdx }: { activeIdx: number }) {
  return (
    <div className="flex items-start justify-center gap-0 overflow-x-auto py-2">
      {PIPELINE.map((node, i) => {
        const Icon    = node.icon;
        const done    = activeIdx > i;
        const active  = activeIdx === i;
        const style   = done ? NODE_STYLE.done : active ? NODE_STYLE.active : node.isNova ? NODE_STYLE.nova : NODE_STYLE.default;
        return (
          <div key={node.id} className="flex items-center shrink-0">
            <div className="flex flex-col items-center gap-2">
              {/* Node circle */}
              <div
                className={[
                  `w-14 h-14 rounded-2xl border-2 flex items-center justify-center`,
                  `transition-all duration-300`,
                  style.bg, style.ring,
                  node.isNova && activeIdx < 0 ? 'nova-idle' : '',
                  active ? 'scale-110' : '',
                ].join(' ')}
                style={node.isNova && active ? { boxShadow: '0 0 0 7px rgba(124,58,237,0.15), 0 4px 24px rgba(124,58,237,0.35)' } : {}}
              >
                {done
                  ? <CheckCircle className="w-6 h-6 text-emerald-500" />
                  : <Icon className={`w-6 h-6 ${style.icon} transition-colors`} />}
              </div>
              {/* Label */}
              <div className="text-center w-[80px]">
                <p className={`text-[11px] font-semibold leading-tight ${active ? 'text-slate-900' : 'text-slate-600'}`}>
                  {node.label}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">{node.sub}</p>
              </div>
            </div>
            {/* Connector line */}
            {i < PIPELINE.length - 1 && (
              <div
                className={`pipe-connector h-[2px] w-7 mb-7 mx-0.5 rounded-full ${done ? 'bg-emerald-300' : 'bg-slate-200'}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── AI thinking timeline ─────────────────────────────────────────────────────
const AUDIO_STEPS = [
  'Uploading audio file…',
  'AWS Transcribe processing speakers…',
  'Speaker diarization complete…',
  'Initializing Nova Lite pipeline…',
  'Nova extracting action items & decisions…',
  'Quality gate evaluating commitments…',
  'Confidence scoring in progress…',
  'Building execution plan…',
];
const TEXT_STEPS = [
  'Submitting transcript…',
  'Initializing Nova Lite pipeline…',
  'Nova extracting action items & decisions…',
  'Detecting ownership and deadlines…',
  'Quality gate evaluating commitments…',
  'Confidence scoring in progress…',
  'Building execution plan…',
];

function AITimeline({ steps, currentStep }: { steps: string[]; currentStep: number }) {
  const visible = steps.slice(0, Math.max(currentStep, 1));
  return (
    <div className="py-4 px-1">
      <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-5">
        Amazon Nova analyzing meeting…
      </p>
      <div className="space-y-3.5">
        {visible.map((step, i) => {
          const done   = i < currentStep - 1;
          const active = i === currentStep - 1;
          return (
            <div key={step} className="step-item flex items-center gap-3"
              style={{ animationDelay: `${i * 55}ms` }}>
              <div className={[
                'w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-200',
                done   ? 'bg-emerald-500 border-emerald-500' :
                active ? 'border-violet-500 bg-white'        :
                         'border-slate-200 bg-white',
              ].join(' ')}>
                {done   && <CheckCircle className="w-3 h-3 text-white" />}
                {active && <Loader2 className="w-3 h-3 text-violet-500 animate-spin" />}
              </div>
              <span className={`text-sm leading-snug ${
                done   ? 'text-slate-500' :
                active ? 'text-slate-900 font-medium' :
                         'text-slate-400'
              }`}>
                {step}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Upload zone ──────────────────────────────────────────────────────────────
interface FileZoneProps {
  label: string; hint: string; accept: string; required?: boolean;
  multiple?: boolean; file?: File | null; files?: File[];
  onChange?: (f: File | undefined) => void;
  onChangeMultiple?: (f: File[]) => void;
  icon: React.ReactNode;
}
function FileZone({ label, hint, accept, required, multiple, file, files, onChange, onChangeMultiple, icon }: FileZoneProps) {
  const ref      = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const hasFile  = !!(file || (files && files.length > 0));
  const fileName = file?.name ?? (files && files.length > 0 ? `${files.length} file${files.length !== 1 ? 's' : ''}` : null);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDrag(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (!dropped.length) return;
    if (multiple && onChangeMultiple) onChangeMultiple(dropped);
    else if (onChange) onChange(dropped[0]);
  }, [multiple, onChange, onChangeMultiple]);

  return (
    <div
      onClick={() => ref.current?.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={onDrop}
      className={[
        'upload-zone rounded-2xl border-2 border-dashed p-5 text-center cursor-pointer select-none',
        hasFile ? 'has-file' : drag ? 'drag-over' : 'border-slate-200 bg-white',
      ].join(' ')}
    >
      <div className={`flex justify-center mb-3 transition-colors ${hasFile ? 'text-emerald-500' : 'text-slate-400'}`}>
        {hasFile ? <CheckCircle className="w-7 h-7" /> : icon}
      </div>
      <p className="text-[13px] font-semibold text-slate-800">{label}</p>
      {hasFile && fileName
        ? <p className="text-xs text-emerald-600 mt-1 font-medium truncate px-2">{fileName}</p>
        : <div className="mt-1">
            <p className="text-xs text-slate-500">{hint}</p>
            {required && <p className="text-[11px] text-red-400 mt-0.5 font-medium">Required</p>}
          </div>}
      <input ref={ref} type="file" accept={accept} multiple={multiple} className="hidden"
        onClick={e => e.stopPropagation()}
        onChange={e => {
          if (multiple && onChangeMultiple) onChangeMultiple(Array.from(e.target.files ?? []));
          else if (onChange) onChange(e.target.files?.[0]);
        }} />
    </div>
  );
}

// ─── Sample transcript ────────────────────────────────────────────────────────
const SAMPLE = `Team standup, March 4th.

Sarah Chen: I'll deploy the authentication service to production by Friday March 7th. I own the rollout end to end.

John: I'll update the API documentation with the new Auth0 integration details by March 12th.

Sarah Chen: I'll also run the full QA suite on the release candidate by end of next week, March 14th.

Manager: We've decided to use Auth0 for OAuth2 — budget is approved at $45k.

John: Someone should probably look at the rollback plan at some point.

Manager: Good point, that's important. Let's table it for now and revisit.`;

// ─── Main ─────────────────────────────────────────────────────────────────────
type Mode = 'audio' | 'transcript';

export default function HomePage() {
  const [mode, setMode]           = useState<Mode>('audio');
  const [audio, setAudio]         = useState<File | null>(null);
  const [slides, setSlides]       = useState<File[]>([]);
  const [shots, setShots]         = useState<File[]>([]);
  const [text, setText]           = useState('');
  const [processing, setProcessing] = useState(false);
  const [step, setStep]           = useState(0);
  const [nodeIdx, setNodeIdx]     = useState(-1);
  const [error, setError]         = useState<string | null>(null);

  const audioReady = mode === 'audio' && !!audio;
  const textReady  = mode === 'transcript' && text.trim().length > 50;
  const ready      = (audioReady || textReady) && !processing;

  const handleAnalyze = async () => {
    if (!ready) return;
    setProcessing(true);
    setError(null);
    setStep(0);
    setNodeIdx(0);

    const steps = mode === 'audio' ? AUDIO_STEPS : TEXT_STEPS;

    // Stagger timeline steps
    steps.forEach((_, i) => {
      setTimeout(() => setStep(i + 1), i * 650 + 300);
    });
    // Animate pipeline nodes
    PIPELINE.forEach((_, i) => {
      setTimeout(() => setNodeIdx(i), i * 620 + 120);
    });

    const form = new FormData();
    if (mode === 'audio' && audio) {
      form.append('audio', audio);
      slides.forEach(f => form.append('slides', f));
      shots.forEach(f => form.append('screenshots', f));
    } else {
      form.append('transcript_text', text);
    }

    try {
      const res = await fetch('/api/meetings/upload', { method: 'POST', body: form });
      if (!res.ok) throw new Error('Upload failed');
      const data = await res.json();
      setTimeout(() => { window.location.href = `/analysis/${data.meeting_id}`; }, 1000);
    } catch {
      setError('Upload failed. Check that the backend is running and try again.');
      setProcessing(false);
      setStep(0);
      setNodeIdx(-1);
    }
  };

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <style>{HOME_CSS}</style>

      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <header className="bg-[#0F172A] border-b border-slate-800 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-violet-600 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold text-white text-sm tracking-tight">DecisionPilot</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-violet-500/30 bg-violet-500/10 text-violet-300 text-xs font-semibold">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-violet-400" />
            </span>
            Amazon Nova · Live
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div
        className="pt-16 pb-10 text-center px-5 relative"
        style={{ background: 'radial-gradient(ellipse 80% 55% at 50% 0%, rgba(124,58,237,0.07) 0%, transparent 68%)' }}
      >
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-violet-200 bg-violet-50 text-violet-700 text-xs font-bold mb-6 u-fade-up">
          <Zap className="w-3 h-3" /> Powered by Amazon Nova
        </div>

        {/* Headline */}
        <h1
          className="text-[50px] font-bold text-slate-900 leading-[1.08] tracking-[-0.02em] mb-4 u-fade-up"
          style={{ animationDelay: '50ms' }}>
          Turn meetings into<br />
          <span className="text-transparent bg-clip-text"
            style={{ backgroundImage: 'linear-gradient(135deg, #7C3AED 0%, #9333EA 100%)' }}>
            accountable execution.
          </span>
        </h1>

        {/* Subline */}
        <p
          className="text-[17px] text-slate-500 max-w-lg mx-auto leading-relaxed u-fade-up"
          style={{ animationDelay: '100ms' }}>
          DecisionPilot uses Amazon Nova to extract commitments,
          verify action quality, and generate auditable Jira tickets.
        </p>

        {/* Pipeline visualization */}
        <div className="mt-10 max-w-3xl mx-auto u-fade-up" style={{ animationDelay: '160ms' }}>
          <PipelineViz activeIdx={nodeIdx} />
        </div>
      </div>

      {/* ── Upload card ───────────────────────────────────────────────────── */}
      <div className="max-w-[600px] mx-auto px-5 pb-16">
        <div
          className="bg-white rounded-2xl border border-slate-200 overflow-hidden u-fade-up"
          style={{
            animationDelay: '230ms',
            boxShadow: '0 4px 24px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          {/* Card header */}
          <div className="px-6 pt-6 pb-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-[15px] font-semibold text-slate-900">Upload Meeting Assets</h2>
              <p className="text-[13px] text-slate-400 mt-0.5">Start an Amazon Nova analysis pipeline</p>
            </div>
          </div>

          <div className="p-6">
            {/* Mode tabs */}
            <div className="flex gap-1 mb-5 bg-slate-100 rounded-xl p-1 w-fit">
              {(['audio', 'transcript'] as const).map(m => (
                <button key={m} onClick={() => !processing && setMode(m)}
                  className={[
                    'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                    mode === m
                      ? 'bg-white text-slate-900 shadow-sm border border-slate-200/80'
                      : 'text-slate-500 hover:text-slate-700',
                  ].join(' ')}>
                  {m === 'audio'
                    ? <><Mic className="w-3.5 h-3.5" /> Upload Audio</>
                    : <><ClipboardPaste className="w-3.5 h-3.5" /> Paste Transcript</>}
                </button>
              ))}
            </div>

            {/* Input — hidden while processing */}
            {!processing && (
              mode === 'audio' ? (
                <div className="grid grid-cols-3 gap-3 mb-5">
                  <FileZone
                    icon={<Mic className="w-7 h-7" />} label="Meeting Audio"
                    hint="MP3 · WAV · M4A" accept="audio/*" required
                    file={audio} onChange={f => setAudio(f ?? null)} />
                  <FileZone
                    icon={<FileText className="w-7 h-7" />} label="Slides"
                    hint="PDF · PPTX" accept=".pdf,.pptx" multiple
                    files={slides} onChangeMultiple={setSlides} />
                  <FileZone
                    icon={<Image className="w-7 h-7" />} label="Whiteboard"
                    hint="PNG · JPG" accept="image/*" multiple
                    files={shots} onChangeMultiple={setShots} />
                </div>
              ) : (
                <div className="mb-5">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs text-slate-500">Paste your meeting transcript</p>
                    <button onClick={() => setText(SAMPLE)}
                      className="text-xs text-violet-600 hover:text-violet-700 font-semibold underline underline-offset-2 transition-colors">
                      Load sample
                    </button>
                  </div>
                  <textarea
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder={"Sarah Chen: I'll deploy the checkout service by Friday...\nJohn: I'll update API docs by March 12...\n\nPaste any meeting notes, transcript, or summary."}
                    className="w-full h-52 bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm text-slate-800 placeholder-slate-400 resize-none focus:outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-400/10 font-mono leading-relaxed transition-all"
                  />
                  <div className="flex items-center justify-between mt-1.5">
                    <p className="text-xs text-slate-400">
                      {text.length > 0
                        ? `${text.split(/\s+/).filter(Boolean).length} words`
                        : 'Minimum 50 characters required'}
                    </p>
                    {text.length > 0 && (
                      <button onClick={() => setText('')}
                        className="text-xs text-slate-400 hover:text-red-500 transition-colors">
                        Clear
                      </button>
                    )}
                  </div>
                </div>
              )
            )}

            {/* AI thinking timeline (replaces input during processing) */}
            {processing && (
              <AITimeline
                steps={mode === 'audio' ? AUDIO_STEPS : TEXT_STEPS}
                currentStep={step} />
            )}

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl p-3 mb-4 text-sm text-red-700">
                <X className="w-4 h-4 shrink-0 mt-0.5" /> {error}
              </div>
            )}

            {/* CTA button */}
            {!processing && (
              <button onClick={handleAnalyze} disabled={!ready}
                className={[
                  'cta-btn w-full py-3.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2.5',
                  ready
                    ? 'bg-[#0F172A] hover:bg-slate-800 text-white shadow-sm cursor-pointer'
                    : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed',
                ].join(' ')}>
                <Zap className="w-4 h-4" />
                Analyze Meeting
                {ready && <ChevronRight className="w-4 h-4 opacity-50" />}
              </button>
            )}

            {!processing && (
              <p className="text-center text-[12px] text-slate-400 mt-3 leading-relaxed">
                {mode === 'transcript'
                  ? 'Nova Lite → Quality Gate → Confidence Scorer → AUTO / REVIEW / CLARIFY'
                  : 'AWS Transcribe → Nova Lite → Quality Gate → Execution Router'}
              </p>
            )}
          </div>
        </div>

        {/* ── Feature cards ────────────────────────────────────────────────── */}
        <div className="grid grid-cols-3 gap-3 mt-5">
          {[
            {
              icon: Shield,   color: 'violet',
              title: 'Quality Gate',
              desc: '7 deterministic checks before AI processing. Hedge words and unresolved owners are rejected.',
            },
            {
              icon: Zap,      color: 'amber',
              title: 'Confidence Scoring',
              desc: 'Action items scored on clarity, ownership certainty, evidence strength, and deadline presence.',
            },
            {
              icon: Ticket,   color: 'emerald',
              title: 'Evidence-Linked',
              desc: 'Every Jira ticket cites the exact timestamp and verbatim quote from the meeting transcript.',
            },
          ].map(({ icon: Icon, color, title, desc }) => (
            <div key={title}
              className="feature-card bg-white border border-slate-100 rounded-2xl p-5"
              style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <div className={[
                'w-10 h-10 rounded-xl border flex items-center justify-center mb-3.5',
                color === 'violet'  ? 'bg-violet-50  border-violet-100'  :
                color === 'amber'   ? 'bg-amber-50   border-amber-100'   :
                                     'bg-emerald-50 border-emerald-100',
              ].join(' ')}>
                <Icon className={`w-5 h-5 ${
                  color === 'violet'  ? 'text-violet-600'  :
                  color === 'amber'   ? 'text-amber-600'   :
                                       'text-emerald-600'
                }`} />
              </div>
              <p className="text-[13px] font-semibold text-slate-900 mb-1.5">{title}</p>
              <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
