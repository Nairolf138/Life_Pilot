import { ActionButton, Alert, StatusBadge } from "@/components/ui";

export default function SettingsPage() {
  return (
    <section className="page-stack">
      <div className="page-header"><div><p className="eyebrow">Préférences</p><h2>Paramètres</h2><p>Configurez le profil, les intégrations, la sécurité et les préférences applicatives.</p></div><ActionButton>Enregistrer</ActionButton></div>
      <Alert title="Sécurité" variant="success">L'authentification forte est activée pour ce compte.</Alert>
      <div className="page-card"><h3>Profil</h3><p><StatusBadge variant="success">Compte vérifié</StatusBadge></p><p>Nom affiché : Camille Martin</p></div>
    </section>
  );
}
