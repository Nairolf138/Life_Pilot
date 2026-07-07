import { ActionButton, DataTable, StatusBadge } from "@/components/ui";

export default function TransactionsPage() {
  return (
    <section className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Mouvements</p><h2>Transactions</h2><p>Consultez, catégorisez et contrôlez les mouvements financiers agrégés.</p></div><ActionButton>Importer</ActionButton></div>
      <div className="page-card"><h3>Transactions à traiter</h3><DataTable columns={["Date", "Libellé", "Statut", "Montant"]} rows={[["07/07/2026", "Assurance habitation", <StatusBadge key="1" variant="warning">À catégoriser</StatusBadge>, "-28 €"], ["05/07/2026", "Courses", <StatusBadge key="2" variant="success">Classée</StatusBadge>, "-83 €"]]} /></div>
    </section>
  );
}
