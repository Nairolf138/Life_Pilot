"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { ActionButton, Alert, EmptyState, StatusBadge } from "@/components/ui";
import { ApiError, apiClient } from "@/lib/api-client";

const ASSISTANT_HISTORY_KEY = "life-pilot-assistant-history";
const ASSISTANT_QUERY_ENDPOINT = "/assistant/query";

const DOMAIN_LABELS: Record<AssistantDomain, string> = {
  transactions: "Transactions",
  documents: "Documents",
  contrats: "Contrats",
  rappels: "Rappels",
  vehicules: "Véhicules",
  actifs: "Actifs",
  dossier_fiscal: "Dossier fiscal",
};

const SECTION_DEFINITIONS: ReadonlyArray<{
  key: AssistantResponseSection;
  label: string;
  tone: "success" | "info" | "warning" | "danger";
  description: string;
}> = [
  { key: "facts_verified", label: "Faits vérifiés", tone: "success", description: "Éléments lus directement dans les données internes." },
  { key: "estimations", label: "Estimations", tone: "info", description: "Calculs ou agrégats dépendant de données potentiellement incomplètes." },
  { key: "hypotheses", label: "Hypothèses", tone: "warning", description: "Correspondances probables à vérifier avant décision." },
  { key: "recommended_actions", label: "Actions recommandées", tone: "info", description: "Prochaines étapes non bloquantes proposées par l'assistant." },
  { key: "required_actions", label: "Actions sensibles ou requises", tone: "danger", description: "Actions qui nécessitent une validation explicite avant exécution." },
];

type AssistantDomain = "transactions" | "documents" | "contrats" | "rappels" | "vehicules" | "actifs" | "dossier_fiscal";
type AssistantResponseSection = "facts_verified" | "estimations" | "hypotheses" | "recommended_actions" | "required_actions";

type AssistantInsight = Readonly<{
  category: string;
  domain: AssistantDomain;
  title: string;
  detail: string;
  data?: Record<string, unknown>;
}>;

type AssistantQueryResponse = Readonly<Record<AssistantResponseSection, AssistantInsight[]> & { question: string }>;

type HistoryEntry = Readonly<{
  id: string;
  askedAt: string;
  response: AssistantQueryResponse;
}>;

function confidenceFor(response: AssistantQueryResponse) {
  const facts = response.facts_verified.length;
  const estimates = response.estimations.length;
  const hypotheses = response.hypotheses.length;
  const total = facts + estimates + hypotheses + response.recommended_actions.length + response.required_actions.length;
  if (total === 0) return { label: "À confirmer", variant: "warning" as const, score: 0 };
  const score = Math.max(15, Math.round(((facts + estimates * 0.72 + hypotheses * 0.45) / Math.max(1, facts + estimates + hypotheses)) * 100));
  if (score >= 80) return { label: "Confiance élevée", variant: "success" as const, score };
  if (score >= 55) return { label: "Confiance moyenne", variant: "info" as const, score };
  return { label: "Confiance limitée", variant: "warning" as const, score };
}

function readHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const value = window.localStorage.getItem(ASSISTANT_HISTORY_KEY);
    return value ? (JSON.parse(value) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function getInternalSources(insight: AssistantInsight) {
  const sources = [`Domaine interne : ${DOMAIN_LABELS[insight.domain]}`];
  const recentItems = insight.data?.recent_items;
  const matchingItems = insight.data?.matching_items;
  if (Array.isArray(recentItems) && recentItems.length > 0) sources.push(`${recentItems.length} élément(s) récent(s) consulté(s)`);
  if (Array.isArray(matchingItems) && matchingItems.length > 0) sources.push(`${matchingItems.length} correspondance(s) interne(s)`);
  if (insight.data?.metrics && typeof insight.data.metrics === "object") sources.push("Métriques agrégées internes");
  return sources;
}

function InsightCard({ insight, section }: Readonly<{ insight: AssistantInsight; section: AssistantResponseSection }>) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const requiresConfirmation = section === "required_actions" || insight.category === "action_requise";
  const sources = getInternalSources(insight);

  return (
    <article className="assistant-insight">
      <div className="assistant-insight__header">
        <div>
          <StatusBadge variant={requiresConfirmation ? "danger" : "neutral"}>{DOMAIN_LABELS[insight.domain]}</StatusBadge>
          <h4>{insight.title}</h4>
        </div>
        <span className="assistant-insight__type">{insight.category.replaceAll("_", " ")}</span>
      </div>
      <p>{insight.detail}</p>
      {Object.keys(insight.data ?? {}).length > 0 ? <pre>{JSON.stringify(insight.data, null, 2)}</pre> : null}
      <div className="assistant-sources" aria-label="Sources internes citées">
        <strong>Sources internes citées</strong>
        <ul>{sources.map((source) => <li key={source}>{source}</li>)}</ul>
      </div>
      {requiresConfirmation ? (
        <div className="assistant-confirmation">
          <p>Cette action est sensible : confirmez explicitement avant toute exécution hors de cette page.</p>
          {isConfirming ? (
            <div className="assistant-confirmation__actions">
              <ActionButton onClick={() => { setIsConfirmed(true); setIsConfirming(false); }}>Confirmer l'action sensible</ActionButton>
              <button className="secondary-button" type="button" onClick={() => setIsConfirming(false)}>Annuler</button>
            </div>
          ) : <ActionButton onClick={() => setIsConfirming(true)}>{isConfirmed ? "Action confirmée localement" : "Demander confirmation"}</ActionButton>}
        </div>
      ) : null}
    </article>
  );
}

export default function AssistantPage() {
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => setHistory(readHistory()), []);
  useEffect(() => {
    if (typeof window !== "undefined") window.localStorage.setItem(ASSISTANT_HISTORY_KEY, JSON.stringify(history.slice(0, 10)));
  }, [history]);

  const latest = history[0]?.response;
  const confidence = useMemo(() => (latest ? confidenceFor(latest) : null), [latest]);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) return;
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient<AssistantQueryResponse>(ASSISTANT_QUERY_ENDPOINT, {
        method: "POST",
        body: JSON.stringify({ question: trimmedQuestion }),
      });
      setHistory((current) => [{ id: crypto.randomUUID(), askedAt: new Date().toISOString(), response }, ...current].slice(0, 10));
      setQuestion("");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? `Erreur API ${requestError.status}` : "Impossible de joindre l'assistant.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="page-stack assistant-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Assistant transversal</p>
          <h2>Assistant Life Pilot</h2>
          <p>Posez une question sur vos données internes. Les réponses distinguent faits, estimations, hypothèses et actions.</p>
        </div>
        {confidence ? <StatusBadge variant={confidence.variant}>{confidence.label} · {confidence.score}%</StatusBadge> : null}
      </div>

      <form className="assistant-query page-card" onSubmit={submitQuestion}>
        <label htmlFor="assistant-question">Votre question</label>
        <div className="assistant-query__row">
          <textarea id="assistant-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ex. Quels rappels et documents dois-je vérifier cette semaine ?" rows={3} />
          <ActionButton type="submit" disabled={isLoading}>{isLoading ? "Analyse..." : "Interroger"}</ActionButton>
        </div>
      </form>

      {error ? <Alert title="Assistant indisponible" variant="warning">{error}</Alert> : null}

      {!latest ? <EmptyState title="Aucun échange" description="L'historique est conservé localement dans ce navigateur après votre première question." /> : (
        <div className="assistant-layout">
          <aside className="page-card assistant-history">
            <h3>Historique local</h3>
            {history.map((entry) => <button key={entry.id} type="button" onClick={() => setHistory((current) => [entry, ...current.filter((item) => item.id !== entry.id)])}><strong>{entry.response.question}</strong><span>{new Date(entry.askedAt).toLocaleString("fr-FR")}</span></button>)}
          </aside>
          <div className="page-card assistant-response">
            <h3>Réponse structurée</h3>
            <p className="muted-text">Question : {latest.question}</p>
            {SECTION_DEFINITIONS.map((section) => (
              <section className="assistant-section" key={section.key}>
                <div className="assistant-section__header"><h4>{section.label}</h4><StatusBadge variant={section.tone}>{latest[section.key].length}</StatusBadge></div>
                <p className="muted-text">{section.description}</p>
                {latest[section.key].length === 0 ? <p className="assistant-empty-line">Aucun élément.</p> : latest[section.key].map((insight, index) => <InsightCard key={`${section.key}-${insight.domain}-${index}`} insight={insight} section={section.key} />)}
              </section>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
