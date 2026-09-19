"use client";

import { FormEvent, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Row = { id: string; customer_name: string | null; customer_phone: string; service_name: string; start_at: string; status: string };
type Service = { id: string; name: string; duration_minutes: number; price: string; active: boolean };
type WorkingHour = { day_of_week: number; start_time: string; end_time: string; active: boolean };
const weekdays = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

export default function AdminPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [hours, setHours] = useState<WorkingHour[]>([]);
  const [manual, setManual] = useState({ phone_number: "", customer_name: "", service_id: "", start_at: "" });
  const [blocked, setBlocked] = useState({ date: "", start_time: "", end_time: "", reason: "" });
  const [newService, setNewService] = useState({ name: "", duration_minutes: "30", price: "" });

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiUrl}/api/v1/admin/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? "Giriş yapılamadı."); return; }
    setToken(data.access_token);
    await loadData(data.access_token);
  }

  async function loadData(currentToken = token) {
    const headers = { Authorization: `Bearer ${currentToken}` };
    const [dashboard, serviceResponse, hoursResponse] = await Promise.all([fetch(`${apiUrl}/api/v1/admin/dashboard`, { headers }), fetch(`${apiUrl}/api/v1/services`), fetch(`${apiUrl}/api/v1/admin/working-hours`, { headers })]);
    setRows(await dashboard.json());
    setServices(await serviceResponse.json());
    setHours(await hoursResponse.json());
  }

  async function saveHours(day: number, active: boolean) {
    const existing = hours.find((item) => item.day_of_week === day);
    const payload = { day_of_week: day, start_time: existing?.start_time?.slice(0, 5) ?? "09:00", end_time: existing?.end_time?.slice(0, 5) ?? "21:00", active };
    const response = await fetch(`${apiUrl}/api/v1/admin/working-hours/${day}`, { method: "PUT", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });
    if (response.ok) await loadData(); else setError("Çalışma saati kaydedilemedi.");
  }

  async function createBlocked(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${apiUrl}/api/v1/admin/blocked-times`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(blocked) });
    if (response.ok) setBlocked({ date: "", start_time: "", end_time: "", reason: "" }); else setError("Kapalı zaman kaydedilemedi.");
  }

  async function createManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${apiUrl}/api/v1/admin/appointments`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ ...manual, start_at: new Date(manual.start_at).toISOString() }) });
    if (response.ok) { setManual({ phone_number: "", customer_name: "", service_id: "", start_at: "" }); await loadData(); } else { const data = await response.json(); setError(data.detail ?? "Randevu oluşturulamadı."); }
  }

  async function createService(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${apiUrl}/api/v1/admin/services`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ ...newService, duration_minutes: Number(newService.duration_minutes), price: Number(newService.price), active: true }) });
    if (response.ok) { setNewService({ name: "", duration_minutes: "30", price: "" }); await loadData(); } else setError("Hizmet eklenemedi.");
  }

  if (!token) return <main className="admin-shell"><section className="auth-panel"><p className="section-kicker">Yönetim paneli</p><h1>Hoş geldiniz.</h1><form onSubmit={login}><label htmlFor="admin-user">Kullanıcı adı</label><input id="admin-user" value={username} onChange={(event) => setUsername(event.target.value)} /><label htmlFor="admin-password">Şifre</label><input id="admin-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /><button type="submit">Giriş yap</button></form>{error && <p className="form-error" role="alert">{error}</p>}</section></main>;

  return <main className="admin-shell"><section className="admin-content"><p className="section-kicker">Yönetim paneli</p><h1>Bugünün akışı.</h1><div className="admin-columns"><div><h2>Randevular</h2>{rows.length === 0 ? <p className="form-hint">Bugün için randevu yok.</p> : <div className="appointment-list">{rows.map((row) => <div className="appointment-item" key={row.id}><strong>{new Date(row.start_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })} · {row.customer_name ?? row.customer_phone}</strong><span>{row.service_name}</span></div>)}</div>}</div><div className="admin-card"><h2>Manuel randevu</h2><form onSubmit={createManual}><input placeholder="Müşteri adı soyadı" value={manual.customer_name} onChange={(event) => setManual({ ...manual, customer_name: event.target.value })} required /><input placeholder="Telefon" type="tel" value={manual.phone_number} onChange={(event) => setManual({ ...manual, phone_number: event.target.value })} required /><select value={manual.service_id} onChange={(event) => setManual({ ...manual, service_id: event.target.value })} required><option value="">Hizmet seçin</option>{services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select><input type="datetime-local" value={manual.start_at} onChange={(event) => setManual({ ...manual, start_at: event.target.value })} required /><button type="submit">Randevu oluştur</button></form></div><div className="admin-card"><h2>Hizmet ekle</h2><form onSubmit={createService}><input placeholder="Hizmet adı" value={newService.name} onChange={(event) => setNewService({ ...newService, name: event.target.value })} required /><div className="two-fields"><input type="number" min="1" placeholder="Dakika" value={newService.duration_minutes} onChange={(event) => setNewService({ ...newService, duration_minutes: event.target.value })} required /><input type="number" min="0" step="0.01" placeholder="Fiyat (TL)" value={newService.price} onChange={(event) => setNewService({ ...newService, price: event.target.value })} required /></div><button type="submit">Hizmet ekle</button></form></div><div className="admin-card"><h2>Çalışma saatleri · 09:00–21:00</h2>{weekdays.map((day, index) => { const item = hours.find((hour) => hour.day_of_week === index); return <label className="toggle-row" key={day}><span>{day}<small>{item?.start_time?.slice(0, 5) ?? "09:00"} - {item?.end_time?.slice(0, 5) ?? "21:00"}</small></span><input type="checkbox" checked={item?.active ?? false} onChange={(event) => saveHours(index, event.target.checked)} /></label>; })}</div><div className="admin-card"><h2>Kapalı zaman ekle</h2><form onSubmit={createBlocked}><input type="date" value={blocked.date} onChange={(event) => setBlocked({ ...blocked, date: event.target.value })} required /><div className="two-fields"><input type="time" value={blocked.start_time} onChange={(event) => setBlocked({ ...blocked, start_time: event.target.value })} required /><input type="time" value={blocked.end_time} onChange={(event) => setBlocked({ ...blocked, end_time: event.target.value })} required /></div><input placeholder="Not (isteğe bağlı)" value={blocked.reason} onChange={(event) => setBlocked({ ...blocked, reason: event.target.value })} /><button type="submit">Kapalı zaman ekle</button></form></div></div>{error && <p className="form-error" role="alert">{error}</p>}</section></main>;
}