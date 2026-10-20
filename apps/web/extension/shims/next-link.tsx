import type { AnchorHTMLAttributes } from "react";

/** Stands in for `next/link` in the extension build; shared components only pass a string href. */
export default function Link({ href, ...props }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  return <a href={href} {...props} />;
}
