import Link from "next/link";

type AuthShellProps = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer: React.ReactNode;
};

export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <main className="auth-root">
      <div className="auth-card">
        <p className="auth-brand">
          Gym<span className="auth-brand-accent">Life</span>
        </p>
        <h1 className="auth-title">{title}</h1>
        {subtitle ? <p className="auth-subtitle">{subtitle}</p> : null}
        {children}
        <div className="auth-footer">{footer}</div>
        <Link href="/" className="auth-back">
          ← Back to home
        </Link>
      </div>
    </main>
  );
}
