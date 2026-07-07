import { ActionButton, Alert, DataTable, EmptyState, StatCard, StatusBadge } from "@/components/ui";

const DASHBOARD_SUMMARY_ENDPOINT = "/api/dashboard/summary";

type DashboardSummary = Readonly<{
  totalBankBalance: number;
  monthlyExpenses: number;
  monthlyIncome: number;
  estimatedSavings: number;
  importantAlerts: number;
  upcomingDeadlines: number;
  documentsToProcess: number;
  transactionsToReview: number;
}>;

const EMPTY_DASHBOARD_SUMMARY: DashboardSummary = {
  totalBankBalance: 0,
  monthlyExpenses: 0,
  monthlyIncome: 0,
  estimatedSavings: 0,
  importantAlerts: 0,
  upcomingDeadlines: 0,
  documentsToProcess: 0,
  transactionsToReview: 0,
};

async function getDashboardSummary(): Promise<DashboardSummary> {
  // Future API hook: this page is intentionally wired around the shape expected from /api/dashboard/summary.
  // Until the route exists, the dashboard renders a safe empty state with zeroed metrics.
  return EMPTY_DASHBOARD_SUMMARY;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("fr-FR", { currency: "EUR", style: "currency" }).format(value);
}

export default async function DashboardPage() {
  const summary = await getDashboardSummary();

  const hasNoActivity = Object.values(summary).every((value) => value === 0);

  const reviewRows = [
    ["Alertes importantes", "Priorités", <StatusBadge key="alerts" variant="neutral">{summary.importantAlerts}</StatusBadge>],
    ["Prochaines échéances", "Calendrier", <StatusBadge key="deadlines" variant="neutral">{summary.upcomingDeadlines}</StatusBadge>],
    ["Documents à traiter", "Documents", <StatusBadge key="documents" variant="neutral">{summary.documentsToProcess}</StatusBadge>],
    ["Transactions à vérifier", "Transactions", <StatusBadge key="transactions" variant="neutral">{summary.transactionsToReview}</StatusBadge>],
  ];

  return (
    <section className="page-stack" data-api-endpoint={DASHBOARD_SUMMARY_ENDPOINT}>
      <div className="page-header">
        <div>
          <p className="eyebrow">Vue d'ensemble</p>
          <h2>Dashboard</h2>
          <p>
            Synthèse financière préparée pour la future route API de consolidation des comptes,
            transactions, documents et échéances.
          </p>
        </div>
        <ActionButton href="/transactions">Importer des transactions</ActionButton>
      </div>

      <div className="stats-grid stats-grid--dashboard">
        <StatCard label="Solde bancaire total" value={formatCurrency(summary.totalBankBalance)} trend="Tous comptes confondus" icon="€" />
        <StatCard label="Dépenses du mois" value={formatCurrency(summary.monthlyExpenses)} trend="Mois en cours" icon="−" />
        <StatCard label="Revenus du mois" value={formatCurrency(summary.monthlyIncome)} trend="Mois en cours" icon="+" />
        <StatCard label="Épargne estimée" value={formatCurrency(summary.estimatedSavings)} trend="Revenus moins dépenses" icon="↗" />
      </div>

      <Alert title="Source de données préparée" variant="info">
        Cette page consommera la route {DASHBOARD_SUMMARY_ENDPOINT} dès qu'elle sera disponible. Les indicateurs sont actuellement initialisés à zéro.
      </Alert>

      <div className="dashboard-panels">
        <div className="page-card">
          <h3>Points d'attention</h3>
          <DataTable
            caption="Éléments à surveiller dans votre espace Life Pilot"
            columns={["Élément", "Catégorie", "Volume"]}
            rows={reviewRows}
          />
        </div>

        {hasNoActivity ? (
          <EmptyState
            action={<ActionButton href="/transactions">Importer mes premières transactions</ActionButton>}
            title="Aucune donnée à afficher pour le moment"
            description="Importez vos premières transactions pour calculer votre solde, vos dépenses, vos revenus et vos prochaines actions prioritaires."
          />
        ) : null}
      </div>
    </section>
  );
}
