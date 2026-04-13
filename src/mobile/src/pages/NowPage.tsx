import React from 'react';
import { Card, CardContent } from '../components/Card';
import { ActiveCourseCard } from '../components/ActiveCourseCard';
import { IntelligenceCard } from '../components/IntelligenceCard';
import { SyncStatus } from '../components/SyncStatus';
import { useActiveCourse } from '../hooks';
import { useIntelligence } from '../hooks/useIntelligence';
import { GlucoseIcon, CornstarchIcon, MealIcon, SymptomIcon, ChevronRightIcon } from '../components/Icons';
import { useNavigate } from 'react-router-dom';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID;

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

export const NowPage: React.FC = () => {
  const navigate = useNavigate();
  const { course, loading, error, refetch } = useActiveCourse(PATIENT_ID);
  const { risk, baselines, patterns, brief, isLoading: intelLoading, hasSufficientData, isDegraded, isConfigured, refetch: refetchIntel } = useIntelligence();

  const handleQuickAction = (path: string): void => {
    navigate(`/actions?form=${path}`);
  };

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
          <SyncStatus pendingCount={0} />
        </div>
      </header>

      {/* Active Coverage */}
      <section className="px-4 py-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Current Coverage
        </h2>
        <ActiveCourseCard
          course={course}
          loading={loading}
          error={error}
          onRefresh={refetch}
        />
      </section>

      {/* Intelligence Panel */}
      <section className="px-4 py-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Overnight Intelligence
        </h2>
        <IntelligenceCard
          risk={risk}
          brief={brief}
          baselines={baselines}
          patterns={patterns}
          isLoading={intelLoading}
          hasSufficientData={hasSufficientData}
          isDegraded={isDegraded}
          isConfigured={isConfigured}
          onRefresh={refetchIntel}
        />
      </section>

      {/* Quick Actions */}
      <section className="px-4 py-6">
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

      {/* Recent Activity */}
      <section className="px-4 py-6">
        <h2 className="text-sm font-semibold text-[#8A8E97] uppercase tracking-wide mb-3">
          Recent Activity
        </h2>
        <Card variant="outlined">
          <CardContent>
            <div className="text-center py-6">
              <p className="text-[#8A8E97]">No recent activity</p>
              <p className="text-sm text-[#8A8E97] mt-1">
                Start logging to see your history here
              </p>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Intelligence Preview */}
      <section className="px-4 py-6">
        <Card
          variant="outlined"
          onClick={() => navigate('/trends')}
          className="cursor-pointer"
        >
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-[#1A1D21]">📊 View Trends</p>
                <p className="text-sm text-[#8A8E97] mt-1">
                  See your glucose patterns over time
                </p>
              </div>
              <ChevronRightIcon size={20} color="#8A8E97" />
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};