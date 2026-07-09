import type { ButtonHTMLAttributes, ReactNode } from "react";

type StatusBadgeVariant = "success" | "warning" | "danger" | "neutral" | "info";

type StatCardProps = Readonly<{
  label: string;
  value: string;
  trend?: ReactNode;
  icon?: ReactNode;
}>;

export function StatCard({ label, value, trend, icon }: StatCardProps) {
  return (
    <article className="stat-card">
      <div className="stat-card__header">
        <span>{label}</span>
        {icon ? <span className="stat-card__icon" aria-hidden="true">{icon}</span> : null}
      </div>
      <strong>{value}</strong>
      {trend ? <p>{trend}</p> : null}
    </article>
  );
}

type DataTableProps = Readonly<{
  columns: string[];
  rows: ReactNode[][];
  caption?: string;
}>;

export function DataTable({ columns, rows, caption }: DataTableProps) {
  return (
    <div className="table-wrapper">
      <table className="data-table">
        {caption ? <caption>{caption}</caption> : null}
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StatusBadge({ children, variant = "neutral" }: Readonly<{ children: ReactNode; variant?: StatusBadgeVariant }>) {
  return <span className={`status-badge status-badge--${variant}`}>{children}</span>;
}

type ActionButtonProps = Readonly<
  { children: ReactNode; href?: string } & ButtonHTMLAttributes<HTMLButtonElement>
>;

export function ActionButton({ children, href, type = "button", ...buttonProps }: ActionButtonProps) {
  if (href) {
    return <a className="action-button" href={href}>{children}</a>;
  }

  return <button className="action-button" type={type} {...buttonProps}>{children}</button>;
}

export function Alert({ children, title, variant = "info" }: Readonly<{ children: ReactNode; title: string; variant?: "info" | "warning" | "success" }>) {
  return (
    <aside className={`alert alert--${variant}`} role="status">
      <strong>{title}</strong>
      <p>{children}</p>
    </aside>
  );
}

export function EmptyState({ action, description, title }: Readonly<{ action?: ReactNode; description: string; title: string }>) {
  return (
    <div className="empty-state">
      <div aria-hidden="true" className="empty-state__icon">✦</div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action ? <div>{action}</div> : null}
    </div>
  );
}

export function LoadingState({ label = "Chargement en cours" }: Readonly<{ label?: string }>) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}
