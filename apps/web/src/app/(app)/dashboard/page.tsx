import { ActionButton, Alert, DataTable, LoadingState, StatCard, StatusBadge } from "@/components/ui";

export default function DashboardPage() {
  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Vue d'ensemble</p>
          <h2>Dashboard</h2>
          <p>Vue synthétique des comptes, transactions récentes, documents à traiter et rappels prioritaires.</p>
        </div>
        <ActionButton>Nouvelle action</ActionButton>
      </div>

      <div className="stats-grid">
        <StatCard label="Solde total" value="24 850 €" trend="+8,2 % ce mois" icon="€" />
        <StatCard label="Documents" value="12" trend="3 à classer" icon="□" />
        <StatCard label="Rappels" value="5" trend="2 cette semaine" icon="!" />
      </div>

      <Alert title="Synchronisation active">Les données bancaires et documents sont prêts à être consolidés.</Alert>

      <div className="page-card">
        <h3>Activité récente</h3>
        <DataTable
          caption="Dernières opérations suivies par Life Pilot"
          columns={["Élément", "Catégorie", "Statut", "Montant"]}
          rows={[
            ["Loyer juillet", "Logement", <StatusBadge key="s1" variant="success">Validé</StatusBadge>, "-1 050 €"],
            ["Facture énergie", "Maison", <StatusBadge key="s2" variant="warning">À vérifier</StatusBadge>, "-94 €"],
            ["Salaire", "Revenus", <StatusBadge key="s3" variant="info">Importé</StatusBadge>, "+3 200 €"],
          ]}
        />
      </div>

      <LoadingState label="Préparation des recommandations personnalisées" />
    </section>
  );
}
