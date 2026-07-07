import { ActionButton, EmptyState, StatusBadge } from "@/components/ui";

export default function DocumentsPage() {
  return (
    <section className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Archivage</p><h2>Documents</h2><p>Organisez les justificatifs, factures et documents administratifs importants.</p></div><ActionButton>Déposer un document</ActionButton></div>
      <div className="page-card"><h3>Traitement automatique</h3><StatusBadge variant="info">OCR prêt</StatusBadge></div>
      <EmptyState title="Aucun document en attente" description="Les nouveaux justificatifs apparaîtront ici dès leur dépôt ou leur import automatique." />
    </section>
  );
}
