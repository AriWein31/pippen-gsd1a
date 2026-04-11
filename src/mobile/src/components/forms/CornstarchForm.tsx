import React, { useState } from 'react';
import { Button } from '../Button';
import { Input } from '../Input';
import { Card, CardHeader, CardContent, CardFooter } from '../Card';
import { CornstarchIcon, MoonIcon } from '../Icons';
import { addEntry, queueEntrySync } from '../../db/database';
import { validateCornstarch } from '../../utils/helpers';
import type { CornstarchEntry } from '../../types';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID || 'default-patient';

interface CornstarchFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export const CornstarchForm: React.FC<CornstarchFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [grams, setGrams] = useState<string>('');
  const [brand, setBrand] = useState<string>('');
  const [isBedtime, setIsBedtime] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (saving) return;
    setError(undefined);

    const numGrams = parseFloat(grams);
    const validation = validateCornstarch(numGrams);
    if (!validation.valid) {
      setError(validation.error);
      return;
    }

    setSaving(true);

    try {
      const entry: Omit<CornstarchEntry, 'id'> = {
        type: 'cornstarch',
        patientId: PATIENT_ID,
        grams: numGrams,
        brand: brand || undefined,
        isBedtime,
        createdAt: new Date(),
        syncStatus: 'pending',
      };

      const id = await addEntry(entry as CornstarchEntry);
      await queueEntrySync(entry as CornstarchEntry, id as number);

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
            <MoonIcon size={32} color="#10B981" />
          </div>
          <p className="text-lg font-semibold text-[#1A1D21]">Cornstarch Logged!</p>
          <p className="text-sm text-[#8A8E97] mt-1">
            {grams}g{isBedtime ? ' (bedtime)' : ''} — 5.15h coverage started
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CornstarchIcon size={24} color="#315BFF" />
          Log Cornstarch
        </div>
      </CardHeader>
      <form onSubmit={void handleSubmit}>
        <CardContent className="space-y-4">
          <Input
            type="number"
            label="Grams"
            placeholder="Enter amount (1-100)"
            value={grams}
            onChange={(e) => setGrams(e.target.value)}
            error={error}
            min={1}
            max={100}
            step={0.5}
            autoFocus
          />

          <Input
            type="text"
            label="Brand/Type (optional)"
            placeholder="e.g., Great Plains, Argo"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
          />

          <div className="flex items-center justify-between p-4 bg-[#F6F7F9] rounded-xl">
            <div>
              <p className="font-medium text-[#1A1D21]">🌙 Bedtime Dose</p>
              <p className="text-sm text-[#8A8E97]">
                Sets expectations for overnight coverage
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={isBedtime}
              onClick={() => setIsBedtime(!isBedtime)}
              className={`w-12 h-7 rounded-full transition-colors duration-200 ${
                isBedtime ? 'bg-[#315BFF]' : 'bg-[#E5E7EB]'
              }`}
            >
              <span
                className={`block w-5 h-5 bg-white rounded-full shadow transform transition-transform duration-200 ${
                  isBedtime ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <p className="text-sm text-[#8A8E97]">
            💾 Saved locally. API call starts 5.15h coverage.
          </p>
        </CardContent>

        <CardFooter className="flex gap-3">
          {onCancel && (
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" variant="primary" fullWidth loading={saving} disabled={saving}>
            Save Cornstarch
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
