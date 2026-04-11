import { useState, useEffect, useRef } from 'react';

interface CountdownState {
  hours: number;
  minutes: number;
  seconds: number;
  totalSeconds: number;
  isExpired: boolean;
  percentRemaining: number;
}

export function useCountdown(
  endsAt: Date,
  startedAt?: Date
): CountdownState {
  const [state, setState] = useState<CountdownState>(() => calculateState(endsAt, startedAt));
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const tick = (): void => {
      setState(calculateState(endsAt, startedAt));
      frameRef.current = requestAnimationFrame(tick);
    };

    // Initial calculation
    setState(calculateState(endsAt, startedAt));

    // Update every second for countdown
    const intervalId = setInterval(() => {
      setState(calculateState(endsAt, startedAt));
    }, 1000);

    // Smooth animation frame updates for progress bar
    frameRef.current = requestAnimationFrame(tick);

    return () => {
      clearInterval(intervalId);
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [endsAt, startedAt]);

  return state;
}

function calculateState(
  endsAt: Date,
  startedAt?: Date
): CountdownState {
  const now = new Date();
  const end = new Date(endsAt);
  const diff = end.getTime() - now.getTime();

  if (diff <= 0) {
    return {
      hours: 0,
      minutes: 0,
      seconds: 0,
      totalSeconds: 0,
      isExpired: true,
      percentRemaining: 0,
    };
  }

  const totalSeconds = Math.floor(diff / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  let percentRemaining = 100;
  if (startedAt) {
    const totalDuration = end.getTime() - new Date(startedAt).getTime();
    if (totalDuration > 0) {
      percentRemaining = Math.max(0, (diff / totalDuration) * 100);
    }
  }

  return {
    hours,
    minutes,
    seconds,
    totalSeconds,
    isExpired: false,
    percentRemaining,
  };
}
