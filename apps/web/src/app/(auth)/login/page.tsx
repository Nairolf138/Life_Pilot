import Link from "next/link";
import "./styles.css";

export default function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-card">
        <p className="eyebrow">Life Pilot</p>
        <h1>Connexion</h1>
        <p>Accédez à votre espace administratif et financier personnel.</p>
        <form className="login-form">
          <label>
            Email
            <input type="email" name="email" placeholder="vous@example.com" autoComplete="email" />
          </label>
          <label>
            Mot de passe
            <input type="password" name="password" placeholder="••••••••" autoComplete="current-password" />
          </label>
          <Link className="submit-link" href="/dashboard">Se connecter</Link>
        </form>
      </section>
    </main>
  );
}
