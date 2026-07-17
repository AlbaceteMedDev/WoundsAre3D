"use client";

import { useEffect, useRef } from "react";

type Props = {
  children: React.ReactNode;
  /** Stagger delay in ms applied via CSS var. */
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li" | "span";
};

/**
 * Scroll-reveal wrapper: adds `.is-visible` the first time the element
 * enters the viewport. Pure IntersectionObserver — no animation library.
 */
export function Reveal({ children, delay = 0, className = "", as = "div" }: Props) {
  const ref = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const Tag = as as React.ElementType;
  return (
    <Tag
      ref={ref}
      className={`reveal ${className}`}
      style={{ "--reveal-delay": `${delay}ms` } as React.CSSProperties}
    >
      {children}
    </Tag>
  );
}
