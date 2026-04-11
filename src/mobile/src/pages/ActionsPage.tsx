import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '../components/Card';
import {
  GlucoseForm,
  CornstarchForm,
  MealForm,
  SymptomForm,
  GlucoseIcon,
  CornstarchIcon,
  MealIcon,
  SymptomIcon,
} from '../components';
import { useOnlineStatus } from '../hooks';

type FormType = 'glucose' | 'cornstarch' | 'meal' | 'symptom' | null;

interface ActionCardProps {
  icon: React.FC<{ size?: number; color?: string }>;
  title: string;
  description: string;
  onClick: () => void;
}

const ActionCard: React.FC<ActionCardProps> = ({
  icon: Icon,
  title,
  description,
  onClick,
}) => (
  <Card variant="outlined" onClick={onClick} className="cursor-pointer">
    <CardContent>
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-[#F6F7F9] flex items-center justify-center">
          <Icon size={24} color="#315BFF" />
        </div>
        <div className="flex-1">
          <p className="font-semibold text-[#1A1D21]">{title}</p>
          <p className="text-sm text-[#8A8E97] mt-0.5">{description}</p>
        </div>
        <span className="text-[#8A8E97]">→</span>
      </div>
    </CardContent>
  </Card>
);

export const ActionsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [selectedForm, setSelectedForm] = useState<FormType>(null);
  const online = useOnlineStatus();

  useEffect(() => {
    const formParam = searchParams.get('form');
    if (formParam && ['glucose', 'cornstarch', 'meal', 'symptom'].includes(formParam)) {
      setSelectedForm(formParam as FormType);
    }
  }, [searchParams]);

  const handleFormSuccess = (): void => {
    setSelectedForm(null);
  };

  const handleFormCancel = (): void => {
    setSelectedForm(null);
  };

  if (selectedForm) {
    return (
      <div className="min-h-screen bg-[#F6F7F9] pb-20">
        <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
          <button
            onClick={handleFormCancel}
            className="text-[#315BFF] font-medium mb-2"
          >
            ← Back
          </button>
          <h1 className="text-2xl font-bold text-[#1A1D21]">
            {selectedForm === 'glucose' && 'Log Glucose'}
            {selectedForm === 'cornstarch' && 'Log Cornstarch'}
            {selectedForm === 'meal' && 'Log Meal'}
            {selectedForm === 'symptom' && 'Log Symptom'}
          </h1>
        </header>
        <main className="px-4 py-6">
          {selectedForm === 'glucose' && (
            <GlucoseForm onSuccess={handleFormSuccess} onCancel={handleFormCancel} />
          )}
          {selectedForm === 'cornstarch' && (
            <CornstarchForm onSuccess={handleFormSuccess} onCancel={handleFormCancel} />
          )}
          {selectedForm === 'meal' && (
            <MealForm onSuccess={handleFormSuccess} onCancel={handleFormCancel} />
          )}
          {selectedForm === 'symptom' && (
            <SymptomForm onSuccess={handleFormSuccess} onCancel={handleFormCancel} />
          )}
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F6F7F9] pb-20">
      {/* Header */}
      <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
        <h1 className="text-2xl font-bold text-[#1A1D21]">Actions</h1>
        <p className="text-sm text-[#8A8E97] mt-0.5">
          Log your daily entries
        </p>
      </header>

      {/* Offline Banner */}
      {!online && (
        <div className="mx-4 mt-4 p-3 bg-[#FEF3C7] rounded-xl">
          <p className="text-sm text-[#92400E]">
            ⚠️ You're offline. Entries will be saved locally and synced when
            you're back online.
          </p>
        </div>
      )}

      {/* Action Cards */}
      <section className="px-4 py-6 space-y-3">
        <ActionCard
          icon={GlucoseIcon}
          title="Log Glucose"
          description="Record your blood glucose reading"
          onClick={() => setSelectedForm('glucose')}
        />
        <ActionCard
          icon={CornstarchIcon}
          title="Log Cornstarch"
          description="Log your cornstarch intake (5.15h coverage)"
          onClick={() => setSelectedForm('cornstarch')}
        />
        <ActionCard
          icon={MealIcon}
          title="Log Meal"
          description="Record what you ate"
          onClick={() => setSelectedForm('meal')}
        />
        <ActionCard
          icon={SymptomIcon}
          title="Log Symptom"
          description="Note any symptoms you're experiencing"
          onClick={() => setSelectedForm('symptom')}
        />
      </section>

      {/* Tips */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardContent>
            <h3 className="font-semibold text-[#1A1D21] mb-3">💡 Tips</h3>
            <ul className="space-y-2 text-sm text-[#8A8E97]">
              <li>• Log glucose before meals for most accurate readings</li>
              <li>• Take cornstarch 15-30 minutes before meals</li>
              <li>• Note symptoms even if they seem minor</li>
              <li>• All entries work offline — no internet needed</li>
            </ul>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};
