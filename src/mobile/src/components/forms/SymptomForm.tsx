import React, { useState } from 'react';
import { Button } from '../Button';
import { TextArea } from '../Input';
import { Select } from '../Input';
import { Card, CardHeader, CardContent, CardFooter } from '../Card';
import { SymptomIcon } from '../Icons';
import { addEntry, queueEntrySync } from '../../db/database';
import { validateSeverity } from '../../utils/helpers';
import type { SymptomEntry, SymptomType } from '../../types';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID;

interface SymptomFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

const symptomTypeOptions = [
  { value: 'hypoglycemia', label: 'Hypoglycemia (low blood sugar)' },
  { value: 'hyperglycemia', label: 'Hyperglycemia (high blood sugar)' },
  { value: 'fatigue', label: 'Fatigue' },
  { value: 'dizziness', label: 'Dizziness' },
  { value: 'headache', label: 'Headache' },
  { value: 'nausea', label: 'Nausea' },
  { value: 'other', label: 'Other' },
];

export const SymptomForm: React.FC<SymptomFormProps> = ({ onSuccess, onCancel }) => {
  const [symptomType, setSymptomType] = useState<SymptomType>('hypoglycemia');
  const [severity, setSeverity] = useState<string>('5');
  const [notes, setNotes] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (saving) return;
    setError(undefined);

    const numSeverity = parseInt(severity, 10);
    const validation = validateSeverity(numSeverity);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }

    setSaving(true);

    try {
      const entry: Omit<SymptomEntry, 'id'> = {
        type: 'symptom',
        patientId: PATIENT_ID,
        symptomType,
        severity: numSeverity,
        notes: notes.trim() || undefined,
        createdAt: new Date(),
        syncStatus: 'pending',
      };

      const id = await addEntry(entry as SymptomEntry);
      await queueEntrySync(entry as SymptomEntry, id as number);

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save symptom');
    } finally {
      setSaving(false);
    }
  };

  if (success) {
    return (
      <Card>
        <CardContent className="text-center py-8">
          <div className="w-16 h-16 rounded-full bg-[#D1FAE5] mx-auto mb-4 flex items-center justify-center">
            <SymptomIcon size={32} color="#10B981" />
          </div>
          <p className="text-lg font-semibold text-[#1A1D21]">Symptom Logged!</p>
          <p className="text-sm text-[#8A8E97] mt-1">
            {symptomType} — Severity {severity}/10
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <SymptomIcon size={24} color="#315BFF" />
          Log Symptom
        </div>
      </CardHeader>
      <form onSubmit={void handleSubmit}>
        <CardContent className="space-y-4">
          <Select
            label="Symptom Type"
            value={symptomType}
            onChange={(e) => setSymptomType(e.target.value as SymptomType)}
            options={symptomTypeOptions}
          />

          <div>
            <label className="block text-sm font-medium text-[#1A1D21] mb-3">
              Severity: {severity}/10
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full h-2 bg-[#E5E7EB] rounded-lg appearance-none cursor-pointer accent-[#315BFF]"
            />
            <div className="flex justify-between text-xs text-[#8A8E97] mt-1">
              <span>Mild</span>
              <span>Severe</span>
            </div>
          </div>

          <TextArea
            label="Notes (optional)"
            placeholder="Any additional details..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
          />

          {error && <p className="text-sm text-red-500">{error}</p>}

          <p className="text-sm text-[#8A8E97]">
            💾 Saved locally and synced when online
          </p>
        </CardContent>

        <CardFooter className="flex gap-3">
          {onCancel && (
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" variant="primary" fullWidth loading={saving} disabled={saving}>
            Save Symptom
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
