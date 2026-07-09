import { ActionButton, Alert, DataTable, EmptyState, StatusBadge } from "@/components/ui";
import { apiClient } from "@/lib/api-client";

type DocumentRecord = Readonly<{
  id: string;
  document_type: string;
  title: string;
  issuer: string | null;
  issue_date: string | null;
  amount: string | null;
  currency: string;
  extraction_status: string | null;
  confidence_score: string | null;
  linked_transaction_id: string | null;
  created_at: string;
}>;

type DocumentsPageProps = Readonly<{
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}>;

const FINANCIAL_UNMATCHED_FILTER = "financial-unmatched";

async function getDocuments(financialUnmatched: boolean): Promise<{ data: DocumentRecord[]; isFallback: boolean }> {
  try {
    const query = financialUnmatched ? "?financial_unmatched=true" : "";
    const data = await apiClient<DocumentRecord[]>(`/documents${query}`, { cache: "no-store" });
    return { data, isFallback: false };
  } catch {
    return { data: [], isFallback: true };
  }
}

function formatDate(value: string | null) {
  if (!value) {
    return "—";
  }

  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value));
}

function formatAmount(value: string | null, currency: string) {
  if (!value) {
    return "—";
  }

  return new Intl.NumberFormat("fr-FR", { currency, style: "currency" }).format(Number(value));
}

function extractionNeedsReview(document: DocumentRecord) {
  const confidenceScore = Number(document.confidence_score ?? 1);
  return document.extraction_status === "pending" || confidenceScore < 0.75;
}

function documentStatusBadge(document: DocumentRecord) {
  if (document.extraction_status === "failed" || document.extraction_status === "error") {
    return <StatusBadge variant="danger">Échec extraction</StatusBadge>;
  }

  if (extractionNeedsReview(document)) {
    return <StatusBadge variant="warning">Extraction à vérifier</StatusBadge>;
  }

  if (document.linked_transaction_id) {
    return <StatusBadge variant="success">Rapproché</StatusBadge>;
  }

  return <StatusBadge variant="info">À rapprocher</StatusBadge>;
}

export default async function DocumentsPage({ searchParams }: DocumentsPageProps) {
  const params = await searchParams;
  const filter = Array.isArray(params?.filter) ? params?.filter[0] : params?.filter;
  const financialUnmatched = filter === FINANCIAL_UNMATCHED_FILTER;
  const { data: documents, isFallback } = await getDocuments(financialUnmatched);
  const rows = documents.map((document) => [
    document.title,
    document.document_type,
    document.issuer ?? "—",
    formatDate(document.issue_date),
    formatAmount(document.amount, document.currency),
    documentStatusBadge(document),
  ]);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Archivage</p>
          <h2>Documents</h2>
          <p>Organisez les justificatifs, factures et documents administratifs importants.</p>
        </div>
        <ActionButton>Déposer un document</ActionButton>
      </div>

      <div className="page-card">
        <h3>Traitement automatique</h3>
        <StatusBadge variant="info">OCR prêt</StatusBadge>
      </div>

      {financialUnmatched ? (
        <Alert title="Filtre actif" variant="info">
          Seuls les documents financiers avec montant et sans transaction rapprochée sont affichés.
        </Alert>
      ) : null}

      {isFallback ? (
        <Alert title="Documents indisponibles" variant="warning">
          La liste des documents n'a pas pu être chargée depuis l'API.
        </Alert>
      ) : null}

      {rows.length > 0 ? (
        <div className="page-card">
          <h3>Documents archivés</h3>
          <DataTable
            caption="Liste des documents et statut de rapprochement"
            columns={["Titre", "Type", "Émetteur", "Date", "Montant", "Statut"]}
            rows={rows}
          />
        </div>
      ) : (
        <EmptyState title="Aucun document en attente" description="Les nouveaux justificatifs apparaîtront ici dès leur dépôt ou leur import automatique." />
      )}
    </section>
  );
}
