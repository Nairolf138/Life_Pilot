import { ActionButton, EmptyState, StatCard, StatusBadge } from "@/components/ui";

export default function AccountsPage() {
  return (
    <section className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Finance</p><h2>Comptes</h2><p>Centralisez les comptes bancaires, portefeuilles et sources financières suivies par Life Pilot.</p></div><ActionButton>Ajouter un compte</ActionButton></div>
      <div className="stats-grid"><StatCard label="Comptes connectés" value="4" trend="Tous synchronisés" /><StatCard label="Épargne" value="8 420 €" trend="+320 €" /><StatCard label="Risque" value="Faible" trend="Profil stable" /></div>
      <div className="page-card"><h3>État des connexions</h3><StatusBadge variant="success">Connexion bancaire opérationnelle</StatusBadge></div>
      <EmptyState title="Aucun portefeuille externe" description="Ajoutez un courtier ou une assurance-vie pour compléter la vision patrimoniale." action={<ActionButton>Connecter une source</ActionButton>} />
    </section>
  );
}
