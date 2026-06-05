import { NavLink, useLocation } from "react-router-dom";

const tabs: Array<{ to: string; label: string; icon: string; fab?: boolean }> = [
  { to: "/home", label: "Home", icon: "⌂" },
  { to: "/discover", label: "Discover", icon: "◎" },
  { to: "/import", label: "Import", icon: "+", fab: true },
  { to: "/cookbook", label: "Cookbook", icon: "▤" },
  { to: "/profile", label: "Profile", icon: "◉" },
];

export function BottomNav() {
  const { pathname } = useLocation();
  if (pathname.startsWith("/onboarding")) return null;

  return (
    <nav className="bottom-nav" aria-label="Main">
      {tabs.map((t) =>
        t.fab ? (
          <NavLink key={t.to} to={t.to} className="bottom-nav__fab" aria-label="Import recipe">
            <span>{t.icon}</span>
          </NavLink>
        ) : (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) => `bottom-nav__item ${isActive ? "bottom-nav__item--active" : ""}`}
          >
            <span className="bottom-nav__icon">{t.icon}</span>
            <span>{t.label}</span>
          </NavLink>
        ),
      )}
    </nav>
  );
}
