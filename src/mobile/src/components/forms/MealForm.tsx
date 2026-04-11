import React, { useState } from 'react';
import { Button } from '../Button';
import { TextArea } from '../Input';
import { Select } from '../Input';
import { Card, CardHeader, CardContent, CardFooter } from '../Card';
import { MealIcon } from '../Icons';
import { addEntry, queueEntrySync } from '../../db/database';
import type { MealEntry, MealType } from '../../types';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID || 'default-patient';

interface MealFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

const mealTypeOptions = [
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch', label: 'Lunch' },
  { value: 'dinner', label: 'Dinner' },
  { value: 'snack', label: 'Snack' },
];

export const MealForm: React.FC<MealFormProps> = ({ onSuccess, onCancel }) => {
  const [mealType, setMealType] = useState<MealType>('breakfast');
  const [description, setDescription] = useState<string>('');
  const [containsCornstarch, setContainsCornstarch] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (saving) return;
    setError(undefined);

    if (!description.trim()) {
      setError('Please add a short meal description.');
      return;
    }

    setSaving(true);

    try {
      const entry: Omit<MealEntry, 'id'> = {
        type: 'meal',
        patientId: PATIENT_ID,
        mealType,
        description: description.trim(),
        containsCornstarch,
        createdAt: new Date(),
        syncStatus: 'pending',
      };

      const id = await addEntry(entry as MealEntry);
      await queueEntrySync(entry as MealEntry, id as number);

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save meal');
    } finally {
      setSaving(false);
    }
  };

  if (success) {
    return (
      <Card>
        <CardContent className="text-center py-8">
          <div className="w-16 h-16 rounded-full bg-[#D1FAE5] mx-auto mb-4 flex items-center justify-center">
            <MealIcon size={32} color="#10B981" />
          </div>
          <p className="text-lg font-semibold text-[#1A1D21]">Meal Logged!</p>
          <p className="text-sm text-[#8A8E97] mt-1">
            {mealType.charAt(0).toUpperCase() + mealType.slice(1)}
            {containsCornstarch ? ' (with cornstarch)' : ''}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <MealIcon size={24} color="#315BFF" />
          Log Meal
        </div>
      </CardHeader>
      <form onSubmit={void handleSubmit}>
        <CardContent className="space-y-4">
          <Select
            label="Meal Type"
            value={mealType}
            onChange={(e) => setMealType(e.target.value as MealType)}
            options={mealTypeOptions}
          />

          <TextArea
            label="Description"
            placeholder="What did you eat?"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />

          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          <div className="flex items-center justify-between p-4 bg-[#F6F7F9] rounded-xl">
            <div>
              <p className="font-medium text-[#1A1D21]">🌽 Contains Cornstarch</p>
              <p className="text-sm text-[#8A8E97]">
                Triggers separate cornstarch coverage
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={containsCornstarch}
              onClick={() => setContainsCornstarch(!containsCornstarch)}
              className={`w-12 h-7 rounded-full transition-colors duration-200 ${
                containsCornstarch ? 'bg-[#315BFF]' : 'bg-[#E5E7EB]'
              }`}
            >
              <span
                className={`block w-5 h-5 bg-white rounded-full shadow transform transition-transform duration-200 ${
                  containsCornstarch ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <p className="text-sm text-[#8A8E97]">
            💾 Saved locally. Meal creates 2h course unless cornstarch.
          </p>
        </CardContent>

        <CardFooter className="flex gap-3">
          {onCancel && (
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
          )}
          <Button type="submit" variant="primary" fullWidth loading={saving} disabled={saving}>
            Save Meal
          </Button>
        </CardFooter>
      </form>
    </Card>
  );
};
