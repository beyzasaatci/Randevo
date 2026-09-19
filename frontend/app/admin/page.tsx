"use client";

import { FormEvent, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Row = { id: string; customer_name: string | null; customer_phone: string; service_name: string; start_at: string; status: string };
type Service = { id: string; name: string; duration_minutes: number; price: string; active: boolean };
type WorkingHour = { day_of_week: number; start_time: string; end_time: string; active: boolean };
type BlockedTime = { id: string; date: string; start_time: string; end_time: string; reason: string | null };
const weekdays = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"];

export default function AdminPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [hours, setHours] = useState<WorkingHour[]>([]);
  const [blockedTimes, setBlockedTimes] = useState<BlockedTime[]>([]);
  const [error, setError] = useState("");
  const [manual, setManual] = useState({ phone_number: "", customer_name: "", service_id: "", start_at: "" });
  const [blocked, setBlocked] = useState({ date: "", start_time: "", end_time: "", reason: "" });
  const [serviceForm, setServiceForm] = useState({ name: "", duration_minutes: "30", price: "" });
  const [editingService, setEditingService] = useState<string | null>(null);

  async function loadData(currentToken = token) {
    const headers = { Authorization: `Bearer ${currentToken}` };
    const [dashboard, serviceResponse, hoursResponse, blockedResponse] = await Promise.all([
      fetch(`${apiUrl}/api/v1/admin/dashboard`, { headers }),
      fetch(`${apiUrl}/api/v1/services`),
      fetch(`${apiUrl}/api/v1/admin/working-hours`, { headers }),
      fetch(`${apiUrl}/api/v1/admin/blocked-times`, { headers }),
    ]);
    setRows(await dashboard.json());
    setServices(await serviceResponse.json());
    setHours(await hoursResponse.json());
    setBlockedTimes(await blockedResponse.json());
  }

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${apiUrl}/api/v1/admin/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? "Giriş yapılamadı."); return; }
    setToken(data.access_token);
    await loadData(data.access_token);
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
    if (response.ok) { setBlocked({ date: "", start_time: "", end_time: "", reason: "" }); await loadData(); } else setError("Kapalı zaman kaydedilemedi.");
  }

  async function deleteBlockedTime(id: string) {
    const response = await fetch(`${apiUrl}/api/v1/admin/blocked-times/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    if (response.ok) await loadData(); else setError("Kapalı zaman silinemedi.");
  }

  async function createManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch(`${apiUrl}/api/v1/admin/appointments`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ ...manual, start_at: new Date(manual.start_at).toISOString() }) });
    if (response.ok) { setManual({ phone_number: "", customer_name: "", service_id: "", start_at: "" }); await loadData(); } else { const data = await response.json(); setError(data.detail ?? "Randevu oluşturulamadı."); }
  }

  async function saveService(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const path = editingService ? `${apiUrl}/api/v1/admin/services/${editingService}` : `${apiUrl}/api/v1/admin/services`;
    const response = await fetch(path, { method: editingService ? "PATCH" : "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ ...serviceForm, duration_minutes: Number(serviceForm.duration_minutes), price: Number(serviceForm.price), active: true }) });
    if (response.ok) { setServiceForm({ name: "", duration_minutes: "30", price: "" }); setEditingService(null); await loadData(); } else setError("Hizmet kaydedilemedi.");
  }

  async function deactivateService(id: string) {
    const response = await fetch(`${apiUrl}/api/v1/admin/services/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    if (response.ok) await loadData(); else setError("Hizmet pasifleştirilemedi.");
  }

  async function cancelAppointment(id: string) {
    const response = await fetch(`${apiUrl}/api/v1/admin/appointments/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    if (response.ok) await loadData(); else setError("Randevu iptal edilemedi.");
  }

  if (!token) return <main className="admin-shell"><section className="auth-panel"><p className="section-kicker">Yönetim paneli</p><h1>Hoş geldiniz.</h1><form onSubmit={login}><label htmlFor="admin-user">Kullanıcı adı</label><input id="admin-user" value={username} onChange={(event) => setUsername(event.target.value)} /><label htmlFor="admin-password">Şifre</label><input id="admin-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /><button type="submit">Giriş yap</button></form>{error && <p className="form-error" role="alert">{error}</p>}</section></main>;

  return <main className="admin-shell"><section className="admin-content"><p className="section-kicker">Yönetim paneli</p><h1>Bugünün akışı.</h1><div className="admin-columns">
    <div><h2>Randevular</h2>{rows.length === 0 ? <p className="form-hint">Bugün için randevu yok.</p> : <div className="appointment-list">{rows.map((row) => <div className="appointment-item" key={row.id}><div><strong>{new Date(row.start_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })} · {row.customer_name ?? row.customer_phone}</strong><span>{row.service_name}</span></div>{row.status !== "cancelled" && <button className="inline-action" type="button" onClick={() => cancelAppointment(row.id)}>İptal</button>}</div>)}</div>}</div>
    <div className="admin-card"><h2>Manuel randevu</h2><form onSubmit={createManual}><input placeholder="Müşteri adı soyadı" value={manual.customer_name} onChange={(event) => setManual({ ...manual, customer_name: event.target.value })} required /><input placeholder="Telefon" type="tel" value={manual.phone_number} onChange={(event) => setManual({ ...manual, phone_number: event.target.value })} required /><select value={manual.service_id} onChange={(event) => setManual({ ...manual, service_id: event.target.value })} required><option value="">Hizmet seçin</option>{services.map((service) => <option key={service.id} value={service.id}>{service.name}</option>)}</select><input type="datetime-local" value={manual.start_at} onChange={(event) => setManual({ ...manual, start_at: event.target.value })} required /><button type="submit">Randevu oluştur</button></form></div>
    <div className="admin-card"><h2>{editingService ? "Hizmeti düzenle" : "Hizmet ekle"}</h2><form onSubmit={saveService}><input placeholder="Hizmet adı" value={serviceForm.name} onChange={(event) => setServiceForm({ ...serviceForm, name: event.target.value })} required /><div className="two-fields"><input type="number" min="1" placeholder="Dakika" value={serviceForm.duration_minutes} onChange={(event) => setServiceForm({ ...serviceForm, duration_minutes: event.target.value })} required /><input type="number" min="0" step="0.01" placeholder="Fiyat (TL)" value={serviceForm.price} onChange={(event) => setServiceForm({ ...serviceForm, price: event.target.value })} required /></div><button type="submit">{editingService ? "Kaydet" : "Hizmet ekle"}</button></form><div className="admin-list">{services.map((service) => <div className="admin-list-row" key={service.id}><span>{service.name}<small>{service.duration_minutes} dk · {service.price} TL</small></span><span><button className="inline-action" type="button" onClick={() => { setEditingService(service.id); setServiceForm({ name: service.name, duration_minutes: String(service.duration_minutes), price: String(service.price) }); }}>Düzenle</button><button className="inline-action" type="button" onClick={() => deactivateService(service.id)}>Pasifleştir</button></span></div>)}</div></div>
    <div className="admin-card"><h2>Çalışma saatleri · 09:00–21:00</h2>{weekdays.map((day, index) => { const item = hours.find((hour) => hour.day_of_week === index); return <label className="toggle-row" key={day}><span>{day}<small>{item?.start_time?.slice(0, 5) ?? "09:00"} - {item?.end_time?.slice(0, 5) ?? "21:00"}</small></span><input type="checkbox" checked={item?.active ?? false} onChange={(event) => saveHours(index, event.target.checked)} /></label>; })}</div>
    <div className="admin-card"><h2>Kapalı zaman ekle</h2><form onSubmit={createBlocked}><input type="date" value={blocked.date} onChange={(event) => setBlocked({ ...blocked, date: event.target.value })} required /><div className="two-fields"><input type="time" value={blocked.start_time} onChange={(event) => setBlocked({ ...blocked, start_time: event.target.value })} required /><input type="time" value={blocked.end_time} onChange={(event) => setBlocked({ ...blocked, end_time: event.target.value })} required /></div><input placeholder="Not (isteğe bağlı)" value={blocked.reason} onChange={(event) => setBlocked({ ...blocked, reason: event.target.value })} /><button type="submit">Kapalı zaman ekle</button></form><div className="admin-list">{blockedTimes.map((item) => <div className="admin-list-row" key={item.id}><span>{item.date}<small>{item.start_time.slice(0, 5)} - {item.end_time.slice(0, 5)} {item.reason ?? ""}</small></span><button className="inline-action" type="button" onClick={() => deleteBlockedTime(item.id)}>Sil</button></div>)}</div></div>
  </div>{error && <p className="form-error" role="alert">{error}</p>}</section></main>;
}
