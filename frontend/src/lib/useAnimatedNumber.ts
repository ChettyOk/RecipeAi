import { useEffect, useRef, useState } from "react";

function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3;
}

/** Smoothly tween a number when the target value changes. */
export function useAnimatedNumber(value: number | null | undefined, duration = 150): number {
  const target = value ?? 0;
  const [display, setDisplay] = useState(target);
  const fromRef = useRef(target);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const from = fromRef.current;
    if (Math.abs(target - from) < 0.01) {
      setDisplay(target);
      return;
    }

    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = easeOutCubic(t);
      setDisplay(from + (target - from) * eased);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
        setDisplay(target);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [target, duration]);

  return display;
}

export function formatAnimatedInt(n: number): string {
  return String(Math.round(n));
}

export function formatAnimatedDecimal(n: number, decimals = 1): string {
  const f = 10 ** decimals;
  return String(Math.round(n * f) / f);
}
