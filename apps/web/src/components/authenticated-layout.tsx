import Link from "next/link";
import type { ReactNode } from "react";

const navigation = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/accounts", label: "Comptes" },
  { href: "/transactions", label: "Transactions" },
  { href: "/documents", label: "Documents" },
  { href: "/reminders", label: "Rappels" },
  { href: "/settings", label: "Paramètres" },
];

function MainNavigation({ compact = false }: Readonly<{ compact?: boolean }>) {
  return (
    <nav className={compact ? "nav-links nav-links--compact" : "nav-links"} aria-label="Navigation principale">
      {navigation.map((item) => (
        <Link key={item.href} href={item.href}>{item.label}</Link>
      ))}
    </nav>
  );
}

export function AuthenticatedLayout({ children }: Readonly<{ children: ReactNode }>) {
  const userName = "Camille Martin";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/dashboard">Life Pilot</Link>
        <MainNavigation />
      </aside>

      <div className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Espace authentifié</p>
            <h1>Bonjour, {userName}</h1>
          </div>
          <div className="topbar__actions">
            <span className="user-pill" aria-label={`Utilisateur connecté : ${userName}`}>{userName}</span>
            <Link className="logout-link" href="/login">Déconnexion</Link>
          </div>
        </header>

        <div className="mobile-nav" aria-label="Navigation mobile">
          <MainNavigation compact />
        </div>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}
