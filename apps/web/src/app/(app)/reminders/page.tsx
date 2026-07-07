import { ActionButton, Alert, DataTable, StatusBadge } from "@/components/ui";

export default function RemindersPage() {
  return (
    <section className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Planification</p><h2>Rappels</h2><p>Suivez les échéances administratives, paiements récurrents et actions à réaliser.</p></div><ActionButton>Créer un rappel</ActionButton></div>
      <Alert title="Échéance proche" variant="warning">Un renouvellement d'assurance arrive dans moins de 10 jours.</Alert>
      <div className="page-card"><h3>Prochains rappels</h3><DataTable columns={["Date", "Rappel", "Statut"]} rows={[["15/07/2026", "Renouveler assurance", <StatusBadge key="1" variant="warning">À venir</StatusBadge>], ["01/08/2026", "Déclaration trimestrielle", <StatusBadge key="2">Planifié</StatusBadge>]]} /></div>
    </section>
  );
}
