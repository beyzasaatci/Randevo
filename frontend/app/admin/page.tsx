"use client";

import { FormEvent, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Row = { id: string; customer_name: string | null; customer_phone: string; service_name: string; start_at: string; status: string };

export default function AdminPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiUrl}/api/v1/admin/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? "Giriş yapılamadı."); return; }
    setToken(data.access_token);
    const dashboard = await fetch(`${apiUrl}/api/v1/admin/dashboard`, { headers: { Authorization: `Bearer ${data.access_token}` } });
    setRows(await dashboard.json());
  }

  if (!token) return <main className="admin-shell"><section className="auth-panel"><p className="section-kicker">Yönetim paneli</p><h1>Hoş geldiniz.</h1><form onSubmit={login}><label htmlFor="admin-user">Kullanıcı adı</label><input id="admin-user" value={username} onChange={(event) => setUsername(event.target.value)} /><label htmlFor="admin-password">Şifre</label><input id="admin-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /><button type="submit">Giriş yap</button></form>{error && <p className="form-error" role="alert">{error}</p>}</section></main>;

  return <main className="admin-shell"><section className="admin-content"><p className="section-kicker">Bugün</p><h1>Randevular</h1>{rows.length === 0 ? <p className="form-hint">Bugün için randevu yok.</p> : <div className="appointment-list">{rows.map((row) => <div className="appointment-item" key={row.id}><strong>{new Date(row.start_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })} · {row.customer_name ?? row.customer_phone}</strong><span>{row.service_name}</span></div>)}</div>}</section></main>;
}