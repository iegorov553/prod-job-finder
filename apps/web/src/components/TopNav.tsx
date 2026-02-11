import Link from "next/link";

import { copy } from "@/resources/en";

export const TopNav = () => (
  <nav className="top-nav">
    <div className="brand">
      <span>{copy.appName}</span>
    </div>
    <div className="nav-links">
      <Link href="/">{copy.nav.dashboard}</Link>
      <Link href="/settings">{copy.nav.settings}</Link>
    </div>
  </nav>
);
