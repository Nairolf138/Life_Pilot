import { ActionButton, Alert, StatusBadge } from "@/components/ui";

export default function SettingsPage() {
  return (
    <section className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Préférences</p><h2>Paramètres</h2><p>Configurez le profil, les intégrations, la sécurité et les préférences applicatives.</p></div><ActionButton>Enregistrer</ActionButton></div>
      <Alert title="Sécurité" variant="success">L'authentification forte est activée pour ce compte.</Alert>
      <div className="page-card"><h3>Profil</h3><p><StatusBadge variant="success">Compte vérifié</StatusBadge></p><p>Nom affiché : Camille Martin</p></div>
      <div className="page-card">
        <h3>Justificatifs</h3>
        <p className="muted-text">
          L'API <code>/settings</code> permet d'enregistrer les catégories à ignorer via
          <code> ignored_document_category_ids</code>. Ces catégories sont exclues du filtre
          <code> /transactions?without_document=true</code> et des indicateurs du dashboard.
        </p>
        <label>
          Catégories ignorées pour les justificatifs
          <input placeholder="UUID de catégories séparés par des virgules" />
        </label>
        <p className="muted-text">Les catégories professionnelles, fiscales ou au-dessus du seuil configurable restent prises en compte sauf exclusion explicite.</p>
      </div>
    </section>
  );
}
