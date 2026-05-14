import * as React from "react";

/**
 * Pixel width từ đó trở lên được coi là desktop cho admin (khớp Tailwind `md:`).
 * Mobile: `max-width: MOBILE_BREAKPOINT_PX - 1` (≤767px).
 */
export const MOBILE_BREAKPOINT_PX = 768;

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined);

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT_PX);
    };
    mql.addEventListener("change", onChange);
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT_PX);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return !!isMobile;
}

/** Giống `useIsMobile`: viewport &lt; {@link MOBILE_BREAKPOINT_PX}px. */
export function useMobile() {
  return useIsMobile();
}
