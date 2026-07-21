import Image from "next/image";

type Variant = "lockup" | "wordmark" | "mark";

/**
 * Intrinsic sizes match the source artwork so next/image never distorts the
 * aspect ratio. Lockup ~1869×842; wordmark ("StrataMetric" only) ~1200×145;
 * square mark 1254×1254.
 */
const ASSETS: Record<Variant, { light: string; dark: string; w: number; h: number }> = {
  lockup: { light: "/logo-light.png", dark: "/logo-dark.png", w: 1869, h: 842 },
  wordmark: { light: "/wordmark-light.png", dark: "/wordmark-dark.png", w: 1200, h: 145 },
  mark: { light: "/icon-light.png", dark: "/icon-dark.png", w: 1254, h: 1254 },
};

type Props = {
  /** "lockup" = full lockup w/ taglines; "wordmark" = "StrataMetric" only; "mark" = square SM badge. */
  variant: Variant;
  /** Sizing/appearance classes (e.g. "h-auto w-56"). Applied to both variants. */
  className?: string;
  alt: string;
  priority?: boolean;
};

/**
 * Theme-aware brand image. Renders both the light-ground and dark-ground
 * artwork and reveals exactly one via the site's `.dark` class. Because the
 * hidden variant is `display:none`, it is dropped from the accessibility tree,
 * so both can carry the same alt text and only the visible one is announced.
 * The swap is instant when the on-page theme toggle flips.
 */
export function BrandImage({ variant, className, alt, priority }: Props) {
  const a = ASSETS[variant];
  const base = className ? `${className} ` : "";
  return (
    <>
      <Image
        src={a.light}
        width={a.w}
        height={a.h}
        alt={alt}
        priority={priority}
        className={`${base}dark:hidden`}
      />
      <Image
        src={a.dark}
        width={a.w}
        height={a.h}
        alt={alt}
        priority={priority}
        className={`${base}hidden dark:block`}
      />
    </>
  );
}
