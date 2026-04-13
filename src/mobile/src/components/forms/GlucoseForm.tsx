import React, { useState } from 'react';
import { Button } from '../Button';
import { Input } from '../Input';
import { Select } from '../Input';
import { Card, CardHeader, CardContent, CardFooter } from '../Card';
import { GlucoseIcon } from '../Icons';
import { addEntry, queueEntrySync } from '../../db/database';
import { isOnline } from '../../api/client';
import { validateGlucose } from '../../utils/helpers';
import type { GlucoseEntry, GlucoseContext } from '../../types';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID;

interface GlucoseFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

const contextOptions = [
  { value: 'fasting', label: 'Fasting' },
  { value: 'post-meal', label: 'Post-meal' },
  { value: 'bedtime', label: 'Bedtime' },
];

export const GlucoseForm: React.FC<GlucoseFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [value, setValue] = useState<string>('');
  const [context, setContext] = useState<GlucoseContext>('fasting');
  const [time, setTime] = useState<string>(
    new Date().toTimeString().slice(0, 5)
  );
  const [error, setError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (saving) return;
    setError(undefined);

    const numValue = parseFloat(value);
    const validation = validateGlucose(numValue);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }

    setSaving(true);

    try {
      const measuredAt = new Date();
      const [hours, minutes] = time.split(':').map(Number);
      measuredAt.setHours(hours, minutes, 0, 0);

      const entry: Omit<GlucoseEntry, 'id'> = {
        type: 'glucose',
        patientId: PATIENT_ID,
        value: numValue,
        context,
        measuredAt,
        createdAt: new Date(),
        syncStatus: isOnline() ? 'pending' : 'pending',
      };

      const id = await addEntry(entry as GlucoseEntry);
      await queueEntrySync(entry as GlucoseEntry, id as number);

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (success) {
    return (
      <Card>
        <CardContent className="text-center py-8">
          <div className="w-16 h-16 rounded-full bg-[#D1FAE5] mx-auto mb-4 flex items-center justify-center">
            <GlucoseIcon size={32} color="#10B981" />
          </div>
          <p className="text-lg font-semibold text-[#1A1D21]">Glucose Logged!</p>
          <p className="text-sm text-[#8A8E97] mt-1">
            {value} mg/dL ({context})
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <GlucoseIcon size={24} color="#315BFF" />
          Log Glucose
        </div>
      </CardHeader>
      <form onSubmit={void handleSubmit}>
        <CardContent className="space-y-4">
          <Input
            type="number"
            label="Glucose (mg/dL)"
            placeholder="Enter value (20-600)"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            error={error}
            min={20}
            max={600}
            step={1}
            autoFocus
          />

          <Select
            label="Context"
            value={context}
            onChange={(e) => setContext(e.target.value as GlucoseContext)}
            options={contextOptions}
          />

          <Input
            type="time"
            label="Time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />

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
            Save Glucose
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
