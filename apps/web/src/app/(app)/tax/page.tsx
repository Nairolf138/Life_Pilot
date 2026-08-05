import { ActionButton, Alert, DataTable, EmptyState, StatCard, StatusBadge } from "@/components/ui";
import { apiClient } from "@/lib/api-client";

type ChecklistItem = Readonly<Record<string, string | number | boolean | null | undefined>>;

type TaxChecklist = Readonly<{
  known_income_to_verify?: ChecklistItem[];
  found_tax_documents?: ChecklistItem[];
  probable_missing_documents?: ChecklistItem[];
  bank_interests_to_verify?: ChecklistItem[];
  crypto_operations_to_analyze?: ChecklistItem[];
  broker_operations_to_analyze?: ChecklistItem[];
  address_to_confirm?: string | null;
  donations_or_real_expenses_to_confirm_manually?: ChecklistItem[];
  human_intervention_points?: string[];
  pdf_export_available?: boolean;
  pdf_export_note?: string;
}>;

type TaxYearFile = Readonly<{
  id: string;
  tax_year: number;
  income_year: number;
  status: string;
  summary_markdown: string | null;
  checklist_json: TaxChecklist | ChecklistItem[] | null;
  created_at: string;
  updated_at: string;
}>;

const emptyChecklist: TaxChecklist = {
  known_income_to_verify: [],
  found_tax_documents: [],
  probable_missing_documents: [
    { type: "bank_tax_document", status: "missing_probable" },
    { type: "income_proof", status: "missing_probable" },
  ],
  bank_interests_to_verify: [],
  crypto_operations_to_analyze: [],
  broker_operations_to_analyze: [],
  address_to_confirm: null,
  donations_or_real_expenses_to_confirm_manually: [],
  human_intervention_points: [
    "Créer ou sélectionner un dossier fiscal pour générer la checklist complète.",
    "Confirmer manuellement l'adresse, les dons et les frais réels.",
  ],
  pdf_export_available: false,
  pdf_export_note: "Export PDF prévu ultérieurement à partir du Markdown.",
};

async function getTaxYearFiles(): Promise<{ data: TaxYearFile[]; isFallback: boolean }> {
  try {
    const data = await apiClient<TaxYearFile[]>("/tax/year-files", { cache: "no-store" });
    return { data, isFallback: false };
  } catch {
    return { data: [], isFallback: true };
  }
}

function normalizeChecklist(value: TaxYearFile["checklist_json"]): TaxChecklist {
  if (!value || Array.isArray(value)) {
    return emptyChecklist;
  }
  return { ...emptyChecklist, ...value };
}

function itemLabel(item: ChecklistItem | string): string {
  if (typeof item === "string") {
    return item;
  }
  const label = item.label ?? item.title ?? item.name ?? item.type ?? item.symbol ?? item.id ?? "Élément à vérifier";
  const amount = item.amount ?? item.current_value;
  const currency = item.currency ? ` ${item.currency}` : "";
  const date = item.date ?? item.issue_date;
  return [date, label, amount ? `${amount}${currency}` : null].filter(Boolean).join(" — ");
}

function checklistRows(items: readonly (ChecklistItem | string)[] = []) {
  if (items.length === 0) {
    return [["Aucun élément détecté automatiquement", <StatusBadge key="empty" variant="neutral">À compléter</StatusBadge>]];
  }
  return items.map((item) => [itemLabel(item), <StatusBadge key={itemLabel(item)} variant="warning">À vérifier</StatusBadge>]);
}

export default async function TaxPage() {
  const { data: taxYearFiles, isFallback } = await getTaxYearFiles();
  const currentFile = taxYearFiles[0];
  const checklist = normalizeChecklist(currentFile?.checklist_json ?? null);
  const markdownHref = currentFile ? `/tax/year-files/${currentFile.id}/checklist/markdown` : undefined;

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Assistant fiscal</p>
          <h2>Checklist fiscale</h2>
          <p>
            Vérifiez les revenus connus, documents fiscaux, intérêts bancaires, opérations crypto/broker,
            adresse, dons, frais réels et points qui nécessitent une intervention humaine.
          </p>
        </div>
        {markdownHref ? <ActionButton href={markdownHref}>Exporter Markdown</ActionButton> : <ActionButton>Créer un dossier</ActionButton>}
      </div>

      {isFallback ? (
        <Alert title="API fiscale indisponible" variant="warning">
          La page affiche la structure de checklist attendue. Les données réelles apparaîtront dès que l'API sera accessible.
        </Alert>
      ) : null}

      <div className="stats-grid">
        <StatCard label="Dossier fiscal" value={currentFile ? `${currentFile.tax_year}` : "À créer"} trend={currentFile ? `Revenus ${currentFile.income_year}` : "Aucun dossier détecté"} />
        <StatCard label="Documents trouvés" value={(checklist.found_tax_documents?.length ?? 0).toString()} trend="Documents fiscaux rattachés" />
        <StatCard label="Interventions humaines" value={(checklist.human_intervention_points?.length ?? 0).toString()} trend="Contrôles manuels restants" />
      </div>

      <Alert title="Export PDF" variant="info">
        {checklist.pdf_export_note ?? "L'export PDF est prévu ultérieurement ; le Markdown sert de source d'export."}
      </Alert>

      <div className="dashboard-panels dashboard-panels--attention">
        <div className="page-card">
          <h3>Adresse à confirmer</h3>
          <p className="muted-text">{checklist.address_to_confirm ?? "Adresse fiscale à confirmer manuellement."}</p>
        </div>
        <div className="page-card">
          <h3>Points nécessitant intervention humaine</h3>
          <DataTable columns={["Point", "Statut"]} rows={checklistRows(checklist.human_intervention_points)} />
        </div>
      </div>

      <div className="page-card"><h3>Salaires ou revenus connus à vérifier</h3><DataTable columns={["Élément", "Statut"]} rows={checklistRows(checklist.known_income_to_verify)} /></div>
      <div className="page-card"><h3>Documents fiscaux trouvés</h3><DataTable columns={["Document", "Statut"]} rows={checklistRows(checklist.found_tax_documents)} /></div>
      <div className="page-card"><h3>Documents manquants probables</h3><DataTable columns={["Document", "Statut"]} rows={checklistRows(checklist.probable_missing_documents)} /></div>
      <div className="page-card"><h3>Intérêts bancaires à vérifier</h3><DataTable columns={["Opération", "Statut"]} rows={checklistRows(checklist.bank_interests_to_verify)} /></div>
      <div className="page-card"><h3>Opérations crypto à analyser</h3><DataTable columns={["Actif / opération", "Statut"]} rows={checklistRows(checklist.crypto_operations_to_analyze)} /></div>
      <div className="page-card"><h3>Opérations broker à analyser</h3><DataTable columns={["Actif / opération", "Statut"]} rows={checklistRows(checklist.broker_operations_to_analyze)} /></div>
      <div className="page-card"><h3>Dons ou frais réels à confirmer manuellement</h3><DataTable columns={["Élément", "Statut"]} rows={checklistRows(checklist.donations_or_real_expenses_to_confirm_manually)} /></div>

      {!currentFile && !isFallback ? (
        <EmptyState title="Aucun dossier fiscal" description="Créez un dossier fiscal annuel pour générer automatiquement la checklist JSON et Markdown." />
      ) : null}
    </section>
  );
}
