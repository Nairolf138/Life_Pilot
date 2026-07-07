import Link from "next/link";

const navigation = [
  { href: "/dashboard", label: "Tableau de bord" },
  { href: "/accounts", label: "Comptes" },
  { href: "/transactions", label: "Transactions" },
  { href: "/documents", label: "Documents" },
  { href: "/reminders", label: "Rappels" },
  { href: "/settings", label: "Paramètres" },
];

export function AuthenticatedLayout({ children }: Readonly<{ children: import("react").ReactNode }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Navigation principale">
        <Link className="brand" href="/dashboard">Life Pilot</Link>
        <nav className="nav-links">
          {navigation.map((item) => (
            <Link key={item.href} href={item.href}>{item.label}</Link>
          ))}
        </nav>
      </aside>
      <div className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Espace authentifié</p>
            <h1>Console Life Pilot</h1>
          </div>
          <Link className="logout-link" href="/login">Déconnexion</Link>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
