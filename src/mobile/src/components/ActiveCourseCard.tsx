import React from 'react';
import { Card, CardContent } from './Card';
import { useCountdown } from '../hooks';
import { MoonIcon, SunIcon, SyncIcon } from './Icons';
import type { StoredActiveCourse } from '../db/database';

interface ActiveCourseCardProps {
  course: StoredActiveCourse | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const ActiveCourseCard: React.FC<ActiveCourseCardProps> = ({
  course,
  loading,
  error,
  onRefresh,
}) => {
  if (loading && !course) {
    return (
      <Card className="animate-pulse">
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#E5E7EB]" />
            <div className="flex-1">
              <div className="h-4 bg-[#E5E7EB] rounded w-1/2 mb-2" />
              <div className="h-3 bg-[#E5E7EB] rounded w-1/3" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !course) {
    return (
      <Card variant="outlined">
        <CardContent>
          <div className="flex items-center gap-3 text-red-500">
            <SyncIcon size={24} />
            <div>
              <p className="font-medium">Unable to load coverage</p>
              <p className="text-sm opacity-75">{error}</p>
            </div>
          </div>
          <button
            onClick={onRefresh}
            className="mt-3 text-sm text-[#315BFF] font-medium"
          >
            Try again
          </button>
        </CardContent>
      </Card>
    );
  }

  if (!course) {
    return (
      <Card variant="outlined">
        <CardContent>
          <div className="text-center py-4">
            <p className="text-[#8A8E97] font-medium">No active coverage</p>
            <p className="text-sm text-[#8A8E97] mt-1">
              Log cornstarch or a meal to start coverage
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const { hours, minutes, percentRemaining, isExpired } = useCountdown(
    new Date(course.endsAt),
    new Date(course.startedAt)
  );

  const TypeIcon = course.type === 'cornstarch' ? MoonIcon : SunIcon;
  const typeLabel = course.type === 'cornstarch'
    ? course.grams
      ? `${course.grams}g Cornstarch`
      : 'Cornstarch'
    : course.mealType
    ? `${course.mealType.charAt(0).toUpperCase() + course.mealType.slice(1)}`
    : 'Meal';

  const isBedtime = course.type === 'cornstarch';

  return (
    <Card variant={isActive(course) ? 'active' : 'default'}>
      <CardContent>
        <div className="flex items-center gap-3 mb-4">
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center ${
              isActive(course)
                ? 'bg-white/20'
                : 'bg-[#F6F7F9]'
            }`}
          >
            <TypeIcon
              size={24}
              color={isActive(course) ? '#FFFFFF' : '#315BFF'}
            />
          </div>
          <div>
            <p
              className={`font-semibold text-lg ${
                isActive(course) ? 'text-white' : 'text-[#1A1D21]'
              }`}
            >
              {isBedtime && '🌙 '}
              {typeLabel}
              {isBedtime && ' Coverage'}
            </p>
            <p
              className={`text-sm ${
                isActive(course) ? 'text-white/80' : 'text-[#8A8E97]'
              }`}
            >
              {isExpired ? 'Coverage ended' : `${hours}h ${minutes}m remaining`}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-3">
          <div
            className={`h-3 rounded-full overflow-hidden ${
              isActive(course) ? 'bg-white/20' : 'bg-[#E5E7EB]'
            }`}
          >
            <div
              className={`h-full rounded-full transition-all duration-1000 ${
                isActive(course) ? 'bg-white' : 'bg-[#315BFF]'
              }`}
              style={{ width: `${Math.max(0, 100 - percentRemaining)}%` }}
            />
          </div>
          <p
            className={`text-sm mt-1 ${
              isActive(course) ? 'text-white/80' : 'text-[#8A8E97]'
            }`}
          >
            {Math.round(Math.max(0, 100 - percentRemaining))}% complete
          </p>
        </div>

        {/* Next dose time */}
        {!isExpired && (
          <div
            className={`text-sm ${
              isActive(course) ? 'text-white/80' : 'text-[#8A8E97]'
            }`}
          >
            Next dose:{' '}
            <span
              className={`font-medium ${
                isActive(course) ? 'text-white' : 'text-[#1A1D21]'
              }`}
            >
              ~{new Date(course.endsAt).toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                hour12: true,
              })}
            </span>
          </div>
        )}

        {isExpired && (
          <div className="mt-2">
            <p
              className={`text-sm font-medium ${
                isActive(course) ? 'text-white' : 'text-[#315BFF]'
              }`}
            >
              Coverage has ended. Consider your next dose.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

function isActive(course: StoredActiveCourse): boolean {
  return new Date(course.endsAt).getTime() > Date.now();
}
