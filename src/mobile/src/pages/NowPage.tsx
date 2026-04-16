import React from 'react';
import { Card, CardContent } from '../components/Card';
import { ActiveCourseCard } from '../components/ActiveCourseCard';
import { AlertCard } from '../components/AlertCard';
import { SyncStatus } from '../components/SyncStatus';
import { useActiveCourse } from '../hooks';
import { useNow } from '../hooks/useNow';
import {
  GlucoseIcon,
  CornstarchIcon,
  MealIcon,
  SymptomIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  MinusIcon,
} from '../components/Icons';
import { useNavigate } from 'react-router-dom';
import type { Recommendation, Change } from '../api/client';
import type { Alert } from '../types';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID;

// ─── Priority badge ──────────────────────────────────────────────────────────

const PRIORITY_CONFIG: Record<
  Recommendation['priority'],
  { label: string; bg: string; text: string; dot: string; border: string }
> = {
  critical: {
    label: 'Critical',
    bg: 'bg-red-50',
    text: 'text-red-700',
    dot: 'bg-red-500',
    border: 'border-red-200',
  },
  high: {
    label: 'High',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    dot: 'bg-orange-500',
    border: 'border-orange-200',
  },
  medium: {
    label: 'Medium',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    dot: 'bg-amber-500',
    border: 'border-amber-200',
  },
  low: {
    label: 'Low',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    dot: 'bg-blue-500',
    border: 'border-blue-200',
  },
};

function PriorityBadge({ priority }: { priority: Recommendation['priority'] }) {
  const c = PRIORITY_CONFIG[priority];
  const pulse = priority === 'critical' || priority === 'high';
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${c.bg} ${c.text} ${c.border}`}
    >
      {pulse && (
        <span className={`w-2 h-2 rounded-full ${c.dot} animate-pulse`} />
      )}
      {c.label}
    </span>
  );
}

// ─── Recommendation card ─────────────────────────────────────────────────────

function RecommendationCard({
  rec,
  onDismiss,
}: {
  rec: Recommendation;
  onDismiss: (id: string) => void;
}) {
  const c = PRIORITY_CONFIG[rec.priority];

  return (
    <div
      className={`rounded-2xl border ${c.border} ${c.bg} p-4 flex flex-col gap-3`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <PriorityBadge priority={rec.priority} />
          <span className="text-xs opacity-60 capitalize">{rec.category}</span>
        </div>
        <span className="text-xs opacity-50 text-right flex-shrink-0">
          {Math.round(rec.confidence * 100)}% confidence
        </span>
      </div>

      {/* Headline */}
      <p className="font-semibold text-[#1A1D21] leading-snug">{rec.headline}</p>

      {/* Explanation */}
      <p className="text-sm text-[#4B5563] leading-relaxed">{rec.explanation}</p>

      {/* Suggested action */}
      {rec.suggested_action && (
        <div className="flex items-start gap-2 p-3 bg-white/60 rounded-xl border border-[#E5E7EB]">
          <span className="text-sm text-[#315BFF] mt-0.5 flex-shrink-0">→</span>
          <p className="text-sm text-[#1A1D21] font-medium">{rec.suggested_action}</p>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={() => onDismiss(rec.id)}
          className="flex-1 text-xs font-medium py-2 px-3 rounded-lg border border-[#E5E7EB] bg-white text-[#4B5563] hover:bg-gray-50 transition-colors"
        >
          Dismiss
        </button>
        <button
          onClick={() => onDismiss(rec.id)}
          className="flex-1 text-xs font-medium py-2 px-3 rounded-lg bg-[#315BFF] text-white hover:bg-[#2545cf] transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  );
}

// ─── Changes panel ────────────────────────────────────────────────────────────

const DIRECTION_ICON: Record<Change['direction'], React.ReactNode> = {
  up: <TrendingUpIcon size={14} color="#DC2626" />,
  down: <TrendingDownIcon size={14} color="#16A34A" />,
  stable: <MinusIcon size={14} color="#6B7280" />,
};

const DIRECTION_COLOR: Record<Change['direction'], string> = {
  up: 'text-red-600',
  down: 'text-green-600',
  stable: 'text-gray-500',
};

function ChangesPanel({ changes }: { changes: Change[] }) {
  if (changes.length === 0) return null;
  return (
    <Card variant="outlined">
      <CardContent>
        <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          This Week vs Last Week
        </p>
        <div className="flex flex-col gap-2">
          {changes.map((change) => (
            <div key={change.metric} className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                {DIRECTION_ICON[change.direction]}
                <span className="text-sm text-[#1A1D21] capitalize">
                  {change.metric.replace(/_/g, ' ')}
                </span>
              </div>
              <span className={`text-sm font-medium ${DIRECTION_COLOR[change.direction]}`}>
                {change.direction === 'stable'
                  ? 'stable'
                  : `${change.direction === 'up' ? '+' : ''}${change.delta_pct}%`}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Brief panel ──────────────────────────────────────────────────────────────

function BriefPanel({
  brief,
}: {
  brief: { what_changed: string[]; what_matters: string[]; recommended_attention: string[] } | null;
}) {
  if (!brief) return null;
  return (
    <Card variant="outlined">
      <CardContent>
        <div className="flex items-start gap-2 mb-3">
          <AlertTriangleIcon size={16} color="#D97706" className="flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-[#1A1D21]">What Matters Today</p>
          </div>
        </div>
        {brief.what_matters.length > 0 && (
          <div className="mb-2">
            {brief.what_matters.map((item, i) => (
              <p key={i} className="text-sm text-[#4B5563] flex items-start gap-1.5">
                <span className="text-[#315BFF] flex-shrink-0 mt-0.5">·</span>
                {item}
              </p>
            ))}
          </div>
        )}
        {brief.what_changed.length > 0 && (
          <div className="pt-2 border-t border-[#E5E7EB]">
            <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-1">
              Changed
            </p>
            {brief.what_changed.map((item, i) => (
              <p key={i} className="text-sm text-[#4B5563] flex items-start gap-1.5">
                <span className="text-[#315BFF] flex-shrink-0 mt-0.5">·</span>
                {item}
              </p>
            ))}
          </div>
        )}
        {brief.recommended_attention.length > 0 && (
          <div className="mt-2 p-2 bg-[#F0F4FF] rounded-lg border border-[#315BFF]/20">
            <p className="text-xs font-semibold text-[#315BFF] mb-1">Tonight</p>
            <p className="text-sm text-[#1A1D21]">{brief.recommended_attention[0]}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Risk card ────────────────────────────────────────────────────────────────

const RISK_LEVEL_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  low: { bg: 'bg-green-50', text: 'text-green-700', label: 'Low Risk' },
  medium: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Medium Risk' },
  high: { bg: 'bg-orange-50', text: 'text-orange-700', label: 'High Risk' },
  critical: { bg: 'bg-red-50', text: 'text-red-700', label: 'Critical' },
};

function RiskCard({
  risk,
}: {
  risk: {
    risk_score: number;
    risk_level: string;
    confidence: number;
    factors: Array<{ reason: string }>;
  } | null;
}) {
  if (!risk) return null;
  const cfg = RISK_LEVEL_CONFIG[risk.risk_level] ?? RISK_LEVEL_CONFIG.low;
  return (
    <Card variant="outlined">
      <CardContent>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-[#1A1D21]">Risk Score</p>
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text}`}>
            {risk.risk_level === 'critical' || risk.risk_level === 'high' ? (
              <AlertTriangleIcon size={12} />
            ) : (
              <CheckCircleIcon size={12} />
            )}
            {cfg.label}
          </span>
        </div>
        <div className="flex items-end gap-2 mb-3">
          <span className="text-4xl font-bold text-[#1A1D21]">{risk.risk_score.toFixed(1)}</span>
          <span className="text-sm text-[#8A8E97] mb-1">/ 10</span>
        </div>
        <p className="text-xs text-[#8A8E97] mb-3">
          confidence {Math.round(risk.confidence * 100)}%
        </p>
        {risk.factors.length > 0 && (
          <div className="pt-3 border-t border-[#E5E7EB]">
            <p className="text-xs font-semibold text-[#8A8E97] uppercase tracking-wide mb-2">
              Top Factors
            </p>
            {risk.factors.slice(0, 2).map((f, i) => (
              <p key={i} className="text-xs text-[#4B5563] flex items-start gap-1.5">
                <span className="text-[#315BFF] flex-shrink-0">·</span>
                {f.reason}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Quick action button ──────────────────────────────────────────────────────

interface QuickActionProps {
  icon: React.FC<{ size?: number; color?: string }>;
  label: string;
  onClick: () => void;
}

const QuickAction: React.FC<QuickActionProps> = ({ icon: Icon, label, onClick }) => (
  <button
    onClick={onClick}
    className="flex flex-col items-center gap-2 p-4 rounded-2xl bg-white hover:bg-[#F6F7F9] transition-colors duration-200 min-w-[80px]"
  >
    <div className="w-12 h-12 rounded-full bg-[#F6F7F9] flex items-center justify-center">
      <Icon size={24} color="#315BFF" />
    </div>
    <span className="text-sm font-medium text-[#1A1D21]">{label}</span>
  </button>
);

// ─── Main page ────────────────────────────────────────────────────────────────

export const NowPage: React.FC = () => {
  const navigate = useNavigate();
  const { course, loading: courseLoading, error } = useActiveCourse(PATIENT_ID);
  const { recommendations, changes, loading, isConfigured, isMock, refetch: refetchNow, nowData } = useNow();

  // Merge active_alerts from nowData into the alerts display
  const activeAlerts: Alert[] = nowData?.active_alerts ?? [];

  const handleDismissRecommendation = (id: string) => {
    // Optimistically remove from UI — no backend action needed for MVP
    console.debug('[NowPage] dismiss recommendation', id);
  };

  const handleQuickAction = (path: string): void => {
    navigate(`/actions?form=${path}`);
  };

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#F6F7F9] pb-20">
        <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-[#1A1D21]">Now</h1>
              <p className="text-sm text-[#8A8E97] mt-0.5">
                {new Date().toLocaleDateString('en-US', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
          </div>
        </header>
        <div className="px-4 pt-6 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-2xl h-32 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ── Not configured ─────────────────────────────────────────────────────────
  if (!isConfigured) {
    return (
      <div className="min-h-screen bg-[#F6F7F9] pb-20">
        <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
          <h1 className="text-2xl font-bold text-[#1A1D21]">Now</h1>
        </header>
        <div className="px-4 pt-6">
          <Card variant="outlined">
            <CardContent>
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-[#FEF3C7] flex items-center justify-center flex-shrink-0">
                  <AlertTriangleIcon size={20} color="#D97706" />
                </div>
                <div>
                  <p className="font-semibold text-[#1A1D21]">Now Screen Not Configured</p>
                  <p className="text-sm text-[#8A8E97] mt-1">
                    Set <code className="bg-[#F6F7F9] px-1 rounded text-xs">VITE_PATIENT_ID</code>{' '}
                    in your <code className="bg-[#F6F7F9] px-1 rounded text-xs">.env</code> file to enable the Now screen.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const brief = nowData?.brief ?? null;
  const risk = nowData?.risk ?? null;

  return (
    <div className="min-h-screen bg-[#F6F7F9] pb-20">
      {/* Header */}
      <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#1A1D21]">Now</h1>
            <p className="text-sm text-[#8A8E97] mt-0.5">
              {new Date().toLocaleDateString('en-US', {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isMock && (
              <span className="text-xs text-[#D97706] bg-amber-50 px-2 py-1 rounded-full border border-amber-200">
                Dev mode
              </span>
            )}
            <SyncStatus pendingCount={0} />
          </div>
        </div>
      </header>

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <section className="px-4 pt-6 pb-0">
          <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
            Active Alerts
          </h2>
          <div className="flex flex-col gap-3">
            {activeAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onAcknowledge={() => {}}
                onDismiss={() => {}}
              />
            ))}
          </div>
        </section>
      )}

      {/* Recommendations (the star of the page) */}
      <section className="px-4 pt-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          What to Do Now
        </h2>
        {recommendations.length === 0 ? (
          <Card variant="outlined">
            <CardContent>
              <div className="text-center py-4">
                <p className="text-sm text-[#8A8E97]">No recommendations right now — all good 👍</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-col gap-3">
            {recommendations.map((rec) => (
              <RecommendationCard
                key={rec.id}
                rec={rec}
                onDismiss={handleDismissRecommendation}
              />
            ))}
          </div>
        )}
      </section>

      {/* Changes panel */}
      {changes.length > 0 && (
        <section className="px-4 pt-6">
          <ChangesPanel changes={changes} />
        </section>
      )}

      {/* Brief panel */}
      {brief && (
        <section className="px-4 pt-6">
          <BriefPanel brief={brief} />
        </section>
      )}

      {/* Risk card */}
      {risk && (
        <section className="px-4 pt-6">
          <RiskCard risk={risk} />
        </section>
      )}

      {/* Active Coverage */}
      <section className="px-4 pt-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Current Coverage
        </h2>
        <ActiveCourseCard
          course={course}
          loading={courseLoading}
          error={error}
          onRefresh={refetchNow}
        />
      </section>

      {/* Quick Actions */}
      <section className="px-4 pt-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Quick Log
        </h2>
        <div className="flex gap-3 overflow-x-auto pb-2 -mx-4 px-4">
          <QuickAction
            icon={GlucoseIcon}
            label="Glucose"
            onClick={() => handleQuickAction('glucose')}
          />
          <QuickAction
            icon={CornstarchIcon}
            label="Cornstarch"
            onClick={() => handleQuickAction('cornstarch')}
          />
          <QuickAction
            icon={MealIcon}
            label="Meal"
            onClick={() => handleQuickAction('meal')}
          />
          <QuickAction
            icon={SymptomIcon}
            label="Symptom"
            onClick={() => handleQuickAction('symptom')}
          />
        </div>
      </section>
    </div>
  );
};
