import { ActionButton, Alert, DataTable, EmptyState, StatCard, StatusBadge } from "@/components/ui";
import { apiClient } from "@/lib/api-client";

const DASHBOARD_MONTHLY_SUMMARY_ENDPOINT = "/api/dashboard/monthly-summary";

type MonthlyCategorySummary = Readonly<{
  category_id: string | null;
  category_name: string;
  amount: string;
  transaction_count: number;
}>;

type MonthlyTransactionAttention = Readonly<{
  id: string;
  booking_date: string;
  label: string;
  amount: string;
  category_name: string | null;
  confidence_score: string | null;
  linked_document_id: string | null;
}>;

type MonthlySummary = Readonly<{
  month: string;
  period_start: string;
  period_end: string;
  income: string;
  expenses: string;
  estimated_savings: string;
  estimated_remaining: string;
  expenses_by_category: MonthlyCategorySummary[];
  top_categories: MonthlyCategorySummary[];
  uncategorized_transactions: MonthlyTransactionAttention[];
  low_confidence_transactions: MonthlyTransactionAttention[];
  transactions_without_document: MonthlyTransactionAttention[];
  financial_unmatched_documents_count: number;
}>;

const currentMonth = () => new Date().toISOString().slice(0, 7);

const emptyMonthlySummary = (month: string): MonthlySummary => ({
  month,
  period_start: `${month}-01`,
  period_end: `${month}-01`,
  income: "0",
  expenses: "0",
  estimated_savings: "0",
  estimated_remaining: "0",
  expenses_by_category: [],
  top_categories: [],
  uncategorized_transactions: [],
  low_confidence_transactions: [],
  transactions_without_document: [],
  financial_unmatched_documents_count: 0,
});

async function getMonthlySummary(month: string): Promise<{ data: MonthlySummary; isFallback: boolean }> {
  try {
    const data = await apiClient<MonthlySummary>(`/dashboard/monthly-summary?month=${month}`, {
      cache: "no-store",
    });
    return { data, isFallback: false };
  } catch {
    return { data: emptyMonthlySummary(month), isFallback: true };
  }
}

function toNumber(value: string) {
  return Number(value) || 0;
}

function formatCurrency(value: string | number) {
  return new Intl.NumberFormat("fr-FR", { currency: "EUR", style: "currency" }).format(
    typeof value === "number" ? value : toNumber(value),
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

function attentionRows(transactions: MonthlyTransactionAttention[]) {
  return transactions.map((transaction) => [
    formatDate(transaction.booking_date),
    transaction.label,
    formatCurrency(transaction.amount),
    transaction.category_name ?? "Non catégorisé",
  ]);
}

export default async function DashboardPage() {
  const { data: summary, isFallback } = await getMonthlySummary(currentMonth());

  const transactionsToReview = new Set([
    ...summary.uncategorized_transactions.map((transaction) => transaction.id),
    ...summary.low_confidence_transactions.map((transaction) => transaction.id),
    ...summary.transactions_without_document.map((transaction) => transaction.id),
  ]).size;
  const hasNoActivity =
    toNumber(summary.income) === 0 &&
    toNumber(summary.expenses) === 0 &&
    summary.expenses_by_category.length === 0 &&
    transactionsToReview === 0;

  const reviewRows = [
    ["Transactions non catégorisées", "Catégorisation", <StatusBadge key="uncategorized" variant="warning">{summary.uncategorized_transactions.length}</StatusBadge>],
    ["Transactions à faible confiance", "Catégorisation", <StatusBadge key="confidence" variant="warning">{summary.low_confidence_transactions.length}</StatusBadge>],
    ["Transactions sans justificatif", "Documents", <StatusBadge key="documents" variant="neutral">{summary.transactions_without_document.length}</StatusBadge>],
    ["Documents financiers non rapprochés", "Documents", <StatusBadge key="financial-documents" variant="warning">{summary.financial_unmatched_documents_count}</StatusBadge>],
    ["Transactions à vérifier", "Priorités", <StatusBadge key="transactions" variant="info">{transactionsToReview}</StatusBadge>],
  ];

  const categoryRows = summary.expenses_by_category.map((category) => [
    category.category_name,
    formatCurrency(category.amount),
    category.transaction_count.toString(),
  ]);

  const topCategoryRows = summary.top_categories.map((category, index) => [
    `#${index + 1}`,
    category.category_name,
    formatCurrency(category.amount),
  ]);

  return (
    <section className="page-stack" data-api-endpoint={DASHBOARD_MONTHLY_SUMMARY_ENDPOINT}>
      <div className="page-header">
        <div>
          <p className="eyebrow">Vue d'ensemble · {summary.month}</p>
          <h2>Dashboard</h2>
          <p>
            Synthèse mensuelle des revenus, dépenses, épargne estimée, reste à vivre estimé
            et points d'attention issus des transactions bancaires.
          </p>
        </div>
        <ActionButton href="/transactions">Importer des transactions</ActionButton>
      </div>

      <div className="stats-grid stats-grid--dashboard">
        <StatCard label="Revenus du mois" value={formatCurrency(summary.income)} trend="Entrées hors virements internes" icon="+" />
        <StatCard label="Dépenses du mois" value={formatCurrency(summary.expenses)} trend="Sorties hors virements internes" icon="−" />
        <StatCard label="Épargne estimée" value={formatCurrency(summary.estimated_savings)} trend="Revenus moins dépenses" icon="↗" />
        <StatCard label="Reste à vivre estimé" value={formatCurrency(summary.estimated_remaining)} trend="Après dépenses du mois" icon="=" />
        <StatCard
          label="Documents financiers non rapprochés"
          value={summary.financial_unmatched_documents_count.toString()}
          trend={<a href="/documents?filter=financial-unmatched">Voir les documents à rapprocher</a>}
          icon="!"
        />
      </div>

      {isFallback ? (
        <Alert title="Synthèse indisponible" variant="warning">
          La route {DASHBOARD_MONTHLY_SUMMARY_ENDPOINT} n'a pas pu être appelée depuis le frontend. Connectez-vous ou vérifiez l'API pour afficher les données réelles.
        </Alert>
      ) : null}

      <div className="dashboard-panels">
        <div className="page-card">
          <h3>Points d'attention</h3>
          <DataTable
            caption="Contrôles qualité des transactions du mois"
            columns={["Élément", "Catégorie", "Volume"]}
            rows={reviewRows}
          />
        </div>

        <div className="page-card">
          <h3>Top catégories</h3>
          {topCategoryRows.length > 0 ? (
            <DataTable
              caption="Catégories les plus dépensières"
              columns={["Rang", "Catégorie", "Montant"]}
              rows={topCategoryRows}
            />
          ) : (
            <p className="muted-text">Aucune dépense catégorisée sur ce mois.</p>
          )}
        </div>
      </div>

      <div className="page-card">
        <h3>Dépenses par catégorie</h3>
        {categoryRows.length > 0 ? (
          <DataTable
            caption="Répartition des dépenses mensuelles par catégorie"
            columns={["Catégorie", "Montant", "Transactions"]}
            rows={categoryRows}
          />
        ) : (
          <p className="muted-text">Aucune dépense à afficher pour ce mois.</p>
        )}
      </div>

      <div className="dashboard-panels dashboard-panels--attention">
        <div className="page-card">
          <h3>Non catégorisées</h3>
          <DataTable
            caption="Transactions sans catégorie"
            columns={["Date", "Libellé", "Montant", "Catégorie"]}
            rows={attentionRows(summary.uncategorized_transactions)}
          />
        </div>
        <div className="page-card">
          <h3>Faible confiance</h3>
          <DataTable
            caption="Transactions à recatégoriser ou confirmer"
            columns={["Date", "Libellé", "Montant", "Catégorie"]}
            rows={attentionRows(summary.low_confidence_transactions)}
          />
        </div>
      </div>

      <div className="page-card">
        <h3>Sans justificatif</h3>
        <DataTable
          caption="Transactions non rattachées à un document"
          columns={["Date", "Libellé", "Montant", "Catégorie"]}
          rows={attentionRows(summary.transactions_without_document)}
        />
      </div>

      {hasNoActivity ? (
        <EmptyState
          action={<ActionButton href="/transactions">Importer mes premières transactions</ActionButton>}
          title="Aucune donnée à afficher pour le moment"
          description="Importez vos premières transactions pour calculer vos revenus, dépenses, catégories prioritaires et contrôles qualité."
        />
      ) : null}
    </section>
  );
}
