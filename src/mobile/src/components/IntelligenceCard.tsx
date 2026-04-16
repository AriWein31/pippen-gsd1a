import React from 'react';
import { Card, CardContent } from './Card';
import { BrainIcon, AlertTriangleIcon, CheckCircleIcon, InfoIcon } from './Icons';
import type { RiskScore, DailyBrief, BaselineMetric } from '../types';
import type { Recommendation } from '../api/client';

// ─── Priority badge ───────────────────────────────────────────────────────────

const REC_PRIORITY_CONFIG: Record<
  Recommendation['priority'],
  { label: string; bg: string; text: string; dot: string; border: string }
> = {
  critical: { label: 'Critical', bg: 'bg-red-50', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200' },
  high:     { label: 'High',     bg: 'bg-orange-50', text: 'text-orange-700', dot: 'bg-orange-500', border: 'border-orange-200' },
  medium:   { label: 'Medium',   bg: 'bg-amber-50',  text: 'text-amber-700',  dot: 'bg-amber-500',  border: 'border-amber-200' },
  low:      { label: 'Low',      bg: 'bg-blue-50',   text: 'text-blue-700',   dot: 'bg-blue-500',   border: 'border-blue-200' },
};

function RecommendationBadge({ priority }: { priority: Recommendation['priority'] }) {
  const c = REC_PRIORITY_CONFIG[priority];
  const pulse = priority === 'critical' || priority === 'high';
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border}`}>
      {pulse && <span className={`w-1.5 h-1.5 rounded-full ${c.dot} animate-pulse`} />}
      {c.label}
    </span>
  );
}

// ─── Recommendation card ─────────────────────────────────────────────────────

function RecommendationCardView({ rec }: { rec: Recommendation }) {
  const c = REC_PRIORITY_CONFIG[rec.priority];
  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-4 flex flex-col gap-2`}>
      <div className="flex items-start justify-between gap-2">
        <RecommendationBadge priority={rec.priority} />
        <span className="text-xs opacity-50 text-right flex-shrink-0">
          {Math.round(rec.confidence * 100)}% confidence
        </span>
      </div>
      <p className="font-semibold text-[#1A1D21] leading-snug text-sm">{rec.headline}</p>
      <p className="text-xs text-[#4B5563] leading-relaxed">{rec.explanation}</p>
      {rec.suggested_action && (
        <div className="flex items-start gap-2 p-2 bg-white/60 rounded-lg border border-[#E5E7EB]">
          <span className="text-sm text-[#315BFF] flex-shrink-0">→</span>
          <p className="text-xs text-[#1A1D21] font-medium">{rec.suggested_action}</p>
        </div>
      )}
    </div>
  );
}

// ─── IntelligenceCard props ────────────────────────────────────────────────────

interface IntelligenceCardProps {
  risk?: RiskScore | null;
  brief?: DailyBrief | null;
  baselines?: BaselineMetric[];
  patterns?: Array<{ pattern_type: string; severity: number; confidence: number; reason: string }>;
  isLoading?: boolean;
  hasSufficientData?: boolean;
  isDegraded?: boolean;
  isConfigured?: boolean;
  onRefresh?: () => void;
  /** Week 8: render individual recommendation cards */
  recommendations?: Recommendation[];
}

function RiskBadge({ level }: { level: string }) {
  const config: Record<string, { label: string; color: string; bg: string; text: string }> = {
    low: { label: 'Low Risk', color: '#16A34A', bg: '#DCFCE7', text: '#15803D' },
    medium: { label: 'Medium Risk', color: '#D97706', bg: '#FEF3C7', text: '#B45309' },
    high: { label: 'High Risk', color: '#DC2626', bg: '#FEE2E2', text: '#B91C1C' },
    critical: { label: 'Critical', color: '#7C3AED', bg: '#EDE9FE', text: '#6D28D9' },
  };
  const c = config[level] ?? config.low;

  return (
    <span
      className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold"
      style={{ backgroundColor: c.bg, color: c.text }}
    >
      {level === 'critical' || level === 'high' ? (
        <AlertTriangleIcon size={12} />
      ) : (
        <CheckCircleIcon size={12} />
      )}
      {c.label}
    </span>
  );
}

export const IntelligenceCard: React.FC<IntelligenceCardProps> = ({
  risk,
  brief,
  baselines,
  patterns,
  isLoading,
  hasSufficientData,
  isDegraded,
  isConfigured,
  onRefresh,
  recommendations = [],
}) => {
  // ── Week 8: Recommendation rendering mode ────────────────────────────────
  if (recommendations.length > 0) {
    return (
      <div className="flex flex-col gap-3">
        {recommendations.map((rec) => (
          <RecommendationCardView key={rec.id} rec={rec} />
        ))}
      </div>
    );
  }
  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5E7EB]" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-[#E5E7EB] rounded w-1/2" />
              <div className="h-3 bg-[#E5E7EB] rounded w-2/3" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Not configured: VITE_PATIENT_ID is not set — surface clearly, do not fabricate data
  if (!isConfigured) {
    return (
      <Card variant="outlined">
        <CardContent>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-[#FEF3C7] flex items-center justify-center flex-shrink-0">
              <AlertTriangleIcon size={20} color="#D97706" />
            </div>
            <div>
              <p className="font-semibold text-[#1A1D21]">Intelligence Not Configured</p>
              <p className="text-sm text-[#8A8E97] mt-1">
                Set <code className="bg-[#F6F7F9] px-1 rounded text-xs">VITE_PATIENT_ID</code> in your <code className="bg-[#F6F7F9] px-1 rounded text-xs">.env</code> file to enable overnight intelligence. See the mobile README for setup instructions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!hasSufficientData) {
    return (
      <Card variant="outlined">
        <CardContent>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-[#F6F7F9] flex items-center justify-center flex-shrink-0">
              <InfoIcon size={20} color="#8A8E97" />
            </div>
            <div>
              <p className="font-semibold text-[#1A1D21]">Intelligence Building</p>
              <p className="text-sm text-[#8A8E97] mt-1">
                Not enough data yet. Keep logging — intelligence grows after a few days of entries.
              </p>
            </div>
          </div>
          <button
            onClick={onRefresh}
            className="mt-3 text-sm text-[#315BFF] font-medium"
          >
            Refresh
          </button>
        </CardContent>
      </Card>
    );
  }

  // We have data — show risk + brief summary
  const riskScore = risk?.risk_score ?? 0;
  const riskLevel = risk?.risk_level ?? 'low';

  // Build a short status line from baselines
  const avgGlucose = baselines?.find(m => m.metric_type === 'overnight_average_glucose');
  const gapFreq = baselines?.find(m => m.metric_type === 'coverage_gap_frequency');

  return (
    <Card variant="outlined">
      <CardContent>
        <div className="flex items-start gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[#F6F7F9] flex items-center justify-center flex-shrink-0">
            <BrainIcon size={20} color="#315BFF" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="font-semibold text-[#1A1D21]">Overnight Intelligence</p>
              {risk && <RiskBadge level={riskLevel} />}
              {isDegraded && (
                <span
                  title="Some intelligence data could not be loaded"
                  className="inline-flex items-center gap-0.5 text-xs text-[#D97706]"
                >
                  <AlertTriangleIcon size={12} /> partial
                </span>
              )}
            </div>
            {risk && (
              <p className="text-xs text-[#8A8E97] mt-0.5">
                Score {riskScore.toFixed(1)} · confidence {Math.round(risk.confidence * 100)}%
              </p>
            )}
          </div>
        </div>

        {isDegraded && (
          <div className="mb-3 p-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-xl flex items-start gap-2">
            <AlertTriangleIcon size={16} color="#D97706" className="flex-shrink-0 mt-0.5" />
            <p className="text-xs text-[#92400E]">
              <span className="font-semibold">Partial data — </span>
              Some intelligence endpoints failed to load. Results below may be incomplete.
            </p>
          </div>
        )}

        {brief && (
          <div className="mb-3 p-3 bg-[#F6F7F9] rounded-xl">
            <p className="text-sm font-medium text-[#1A1D21] mb-1">{brief.summary}</p>
            {brief.what_matters.length > 0 && (
              <p className="text-xs text-[#8A8E97] mt-2">
                <span className="font-medium">Matters: </span>
                {brief.what_matters[0]}
              </p>
            )}
            {brief.recommended_attention.length > 0 && (
              <p className="text-xs text-[#8A8E97] mt-1">
                <span className="font-medium">Tonight: </span>
                {brief.recommended_attention[0]}
              </p>
            )}
          </div>
        )}

        {avgGlucose && avgGlucose.value !== null && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-[#8A8E97]">Avg overnight glucose</span>
            <span className="font-medium text-[#1A1D21]">{avgGlucose.value} mg/dL</span>
          </div>
        )}

        {gapFreq && gapFreq.value !== null && (
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-[#8A8E97]">Coverage gap frequency</span>
            <span className="font-medium text-[#1A1D21]">{Math.round(gapFreq.value * 100)}%</span>
          </div>
        )}

        {(patterns?.length ?? 0) > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
            <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-2">
              Detected Patterns
            </p>
            {patterns?.slice(0, 3).map((p, i) => (
              <p key={i} className="text-xs text-[#8A8E97] mt-1">
                · {p.reason.length > 80 ? p.reason.slice(0, 80) + '…' : p.reason}
              </p>
            ))}
          </div>
        )}

        {risk && risk.factors.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#E5E7EB]">
            <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-2">
              Active Factors
            </p>
            {risk.factors.slice(0, 2).map((f, i) => (
              <p key={i} className="text-xs text-[#8A8E97] mt-1">
                · {f.reason.length > 80 ? f.reason.slice(0, 80) + '…' : f.reason}
              </p>
            ))}
          </div>
        )}

        <button
          onClick={onRefresh}
          className="mt-3 text-sm text-[#315BFF] font-medium"
        >
          Refresh intelligence
        </button>
      </CardContent>
    </Card>
  );
};