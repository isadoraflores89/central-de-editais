// Ícones próprios em SVG (sem emojis). Decorativos: aria-hidden.
import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;

function Base({ children, ...p }: P & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="1.25em"
      height="1.25em"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...p}
    >
      {children}
    </svg>
  );
}

export const IconeBusca = (p: P) => (
  <Base {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Base>
);
export const IconeFiltro = (p: P) => (
  <Base {...p}><path d="M3 5h18M6 12h12M10 19h4" /></Base>
);
export const IconeCalendario = (p: P) => (
  <Base {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></Base>
);
export const IconeExterno = (p: P) => (
  <Base {...p}><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></Base>
);
export const IconeDownload = (p: P) => (
  <Base {...p}><path d="M12 4v11M7 10l5 5 5-5M5 20h14" /></Base>
);
export const IconeAlerta = (p: P) => (
  <Base {...p}><path d="M12 3 2 20h20L12 3Z" /><path d="M12 10v4M12 17.5v.5" /></Base>
);
export const IconeEstrela = (p: P) => (
  <Base {...p}><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3 6.5 20.2l1-6.2L3 9.6l6.2-.9L12 3Z" /></Base>
);
export const IconeFechar = (p: P) => (
  <Base {...p}><path d="M6 6l12 12M18 6 6 18" /></Base>
);
export const IconeSeta = (p: P) => (
  <Base {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Base>
);
export const IconeMoeda = (p: P) => (
  <Base {...p}><circle cx="12" cy="12" r="9" /><path d="M15 9.5c-.5-1-1.6-1.5-3-1.5-1.7 0-3 .9-3 2s1.3 1.7 3 2 3 .9 3 2-1.3 2-3 2c-1.4 0-2.5-.5-3-1.5M12 6v2M12 16v2" /></Base>
);
export const IconeLocal = (p: P) => (
  <Base {...p}><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.5" /></Base>
);
