"use client";

import { FormEvent, useState } from "react";

import { apiClient } from "@/lib/api-client";
import { ActionButton, DataTable, StatusBadge } from "@/components/ui";

type LearningScope =
  | "transaction_only"
  | "future_similar"
  | "past_and_future_similar";

type TransactionCategoryPatch = {
  category_id: string | null;
  subcategory_id: string | null;
  notes: string | null;
  confidence_score: string;
  learning_scope: LearningScope;
};

const demoTransactionId = "00000000-0000-0000-0000-000000000000";

export default function TransactionsPage() {
  const [categoryId, setCategoryId] = useState("");
  const [subcategoryId, setSubcategoryId] = useState("");
  const [notes, setNotes] = useState("");
  const [confidenceScore, setConfidenceScore] = useState("1.0000");
  const [learningScope, setLearningScope] =
    useState<LearningScope>("transaction_only");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const changeCategory = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatusMessage("Changement de catégorie en cours...");

    const payload: TransactionCategoryPatch = {
      category_id: categoryId.trim() || null,
      subcategory_id: subcategoryId.trim() || null,
      notes: notes.trim() || null,
      confidence_score: confidenceScore,
      learning_scope: learningScope,
    };

    try {
      await apiClient(`/transactions/${demoTransactionId}/category`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setStatusMessage("Catégorie mise à jour avec l'option d'apprentissage choisie.");
    } catch {
      setStatusMessage(
        "Impossible d'appliquer la démo sans transaction réelle sélectionnée.",
      );
    }
  };

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">Mouvements</p>
          <h2>Transactions</h2>
          <p>Consultez, catégorisez et contrôlez les mouvements financiers agrégés.</p>
        </div>
        <ActionButton>Importer</ActionButton>
      </div>

      <div className="page-card">
        <h3>Transactions à traiter</h3>
        <DataTable
          columns={["Date", "Libellé", "Statut", "Montant", "Action"]}
          rows={[
            [
              "07/07/2026",
              "Assurance habitation",
              <StatusBadge key="1" variant="warning">À catégoriser</StatusBadge>,
              "-28 €",
              <ActionButton key="change-category">Changer la catégorie</ActionButton>,
            ],
            [
              "05/07/2026",
              "Courses",
              <StatusBadge key="2" variant="success">Classée</StatusBadge>,
              "-83 €",
              <ActionButton key="change-category-2">Modifier</ActionButton>,
            ],
          ]}
        />
      </div>

      <form className="page-card" onSubmit={changeCategory}>
        <h3>Changer la catégorie</h3>
        <label>
          Catégorie
          <input value={categoryId} onChange={(e) => setCategoryId(e.target.value)} placeholder="UUID de catégorie" />
        </label>
        <label>
          Sous-catégorie
          <input value={subcategoryId} onChange={(e) => setSubcategoryId(e.target.value)} placeholder="UUID de sous-catégorie" />
        </label>
        <label>
          Note éventuelle
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Note interne" />
        </label>
        <label>
          Niveau de confiance
          <input type="number" min="0" max="1" step="0.0001" value={confidenceScore} onChange={(e) => setConfidenceScore(e.target.value)} />
        </label>
        <fieldset>
          <legend>Après correction</legend>
          <label><input type="radio" checked={learningScope === "transaction_only"} onChange={() => setLearningScope("transaction_only")} /> Appliquer seulement à cette transaction</label>
          <label><input type="radio" checked={learningScope === "future_similar"} onChange={() => setLearningScope("future_similar")} /> Appliquer aux transactions similaires futures</label>
          <label><input type="radio" checked={learningScope === "past_and_future_similar"} onChange={() => setLearningScope("past_and_future_similar")} /> Appliquer aussi aux transactions similaires passées</label>
        </fieldset>
        <ActionButton type="submit">Enregistrer la correction</ActionButton>
        {statusMessage ? <p>{statusMessage}</p> : null}
      </form>
    </section>
  );
}
