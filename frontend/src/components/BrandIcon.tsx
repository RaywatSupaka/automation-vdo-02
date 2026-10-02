import type { SVGProps } from 'react';

// Owner-authorized artwork from the original SmartFlow UI, rendered through React.
const shapes = {
  story: <><rect x="6" y="2" width="12" height="20" rx="3"/><path d="m10 8 5 4-5 4Z"/></>,
  image: <><rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="9" cy="8" r="2"/><path d="m3 17 5-4 4 3 5-7 4 5"/></>,
  voice: <path d="M3 10v4m4-7v10m5-14v18m5-16v14m4-9v4"/>,
  sparkle: <path d="m12 3 2.6 6.4L21 12l-6.4 2.6L12 21l-2.6-6.4L3 12l6.4-2.6ZM20 2v4m-2-2h4"/>,
};

export function BrandIcon({ name, size = 22, ...props }: SVGProps<SVGSVGElement> & { name: keyof typeof shapes; size?: number }) {
  return <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor"
    strokeWidth={1.65} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false" {...props}>{shapes[name]}</svg>;
}
