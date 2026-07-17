"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  /** Final value. */
  to: number;
  /** Decimal places to render. */
  decimals?: number;
  /** Animation duration ms. */
  duration?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
};

/**
 * Animated number that counts from 0 to `to` when scrolled into view.
 * Respects prefers-reduced-motion by jumping straight to the final value.
 */
export function CountUp({
  to,
  decimals = 0,
  duration = 1600,
  prefix = "",
  suffix = "",
  className = "",
}: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const [value, setValue] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;

    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting)) return;
        io.disconnect();
        if (reduced) {
          setValue(to);
          return;
        }
        const start = performance.now();
        const tick = (now: number) => {
          const t = Math.min(1, (now - start) / duration);
          // ease-out-expo
          const eased = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
          setValue(to * eased);
          if (t < 1) raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [to, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}
