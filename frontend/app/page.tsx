"use client";

import { FormEvent, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type Service = { id: string; name: string; duration_minutes: number; price: string };
type Slot = { start_at: string; end_at: string };
type Appointment = { id: string; service_id: string; start_at: string; end_at: string; status: string };

export default function Home() {
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [services, setServices] = useState<Service[]>([]);
  const [selectedService, setSelectedService] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const [slots, setSlots] = useState<Slot[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [requiresName, setRequiresName] = useState(false);
  const [profileName, setProfileName] = useState("");

  async function submitPhone(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phone }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Kod gönderilemedi.");
      setMessage(data.message);
      setStep("otp");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Bir hata oluştu.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phone, code }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Kod doğrulanamadı.");
      window.localStorage.setItem("customer_token", data.access_token);
      setToken(data.access_token);
      setRequiresName(data.requires_name);
      const serviceResponse = await fetch(`${apiUrl}/api/v1/services`);
      setServices(await serviceResponse.json());
      setMessage(data.requires_name ? "Doğrulandı. Profil adımına geçebilirsiniz." : "Doğrulandı. Randevu akışına geçebilirsiniz.");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Bir hata oluştu.");
    } finally {
      setBusy(false);
    }
  }

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const response = await fetch(`${apiUrl}/api/v1/auth/profile`, { method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ name: profileName }) });
    if (!response.ok) { const data = await response.json(); setError(data.detail ?? "Profil kaydedilemedi."); }
    else setRequiresName(false);
    setBusy(false);
  }

  async function loadAvailability() {
    if (!selectedService || !selectedDate) return;
    const response = await fetch(`${apiUrl}/api/v1/availability?date=${selectedDate}&service_id=${selectedService}`);
    const data = await response.json();
    if (!response.ok) { setError(data.detail ?? "Müsait saatler alınamadı."); return; }
    setSlots(data.slots);
  }

  async function bookSlot(slot: Slot) {
    setBusy(true);
    setError("");
    const response = await fetch(`${apiUrl}/api/v1/appointments`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ service_id: selectedService, start_at: slot.start_at }) });
    const data = await response.json();
    if (!response.ok) setError(data.detail ?? "Randevu oluşturulamadı.");
    else setMessage("Randevunuz başarıyla oluşturuldu.");
    setBusy(false);
  }

  async function loadAppointments() {
    setError("");
    const response = await fetch(`${apiUrl}/api/v1/appointments`, { headers: { Authorization: `Bearer ${token}` } });
    const data = await response.json();
    if (!response.ok) setError(data.detail ?? "Randevular alınamadı.");
    else setAppointments(data);
  }

  return (
    <main className="page-shell">
      <section className="hero" aria-labelledby="page-title">
        <div className="brand-mark" aria-label="Randevo">R</div>
        <p className="eyebrow">Kişisel bakım, sizin zamanınızda</p>
        <h1 id="page-title">İyi görünmek için<br /><em>beklemeyin.</em></h1>
        <p className="intro">Uygun saati seçin, randevunuzu birkaç adımda oluşturun.</p>
        <div className="actions"><a className="primary-action" href="#randevu">Randevu Al <span aria-hidden="true">→</span></a><a className="secondary-action" href="#randevularim">Randevularım</a></div>
        <div className="availability-note"><span className="status-dot" /> Online randevu sistemi açık</div>
      </section>
      {!token ? <section className="auth-panel" id="randevu" aria-labelledby="auth-title">
        <p className="section-kicker">Hızlı giriş</p>
        <h2 id="auth-title">Telefonunuzla başlayın.</h2>
        {step === "phone" ? (
          <form onSubmit={submitPhone}>
            <label htmlFor="phone">Telefon numarası</label>
            <input id="phone" type="tel" inputMode="tel" autoComplete="tel" placeholder="+90 5xx xxx xx xx" value={phone} onChange={(event) => setPhone(event.target.value)} required />
            <button type="submit" disabled={busy}>{busy ? "Gönderiliyor..." : "SMS kodu gönder"}</button>
          </form>
        ) : (
          <form onSubmit={verifyCode}>
            <p className="form-hint">{message || `${phone} numarasına gönderilen 6 haneli kodu girin.`}</p>
            <label htmlFor="code">SMS doğrulama kodu</label>
            <input id="code" type="text" inputMode="numeric" autoComplete="one-time-code" maxLength={6} pattern="[0-9]{6}" value={code} onChange={(event) => setCode(event.target.value)} required />
            <button type="submit" disabled={busy}>{busy ? "Kontrol ediliyor..." : "Doğrula"}</button>
            <button className="text-button" type="button" onClick={() => { setStep("phone"); setMessage(""); }}>Numarayı değiştir</button>
          </form>
        )}
        {error && <p className="form-error" role="alert">{error}</p>}
      </section> : requiresName ? <section className="auth-panel" id="randevu" aria-labelledby="profile-title">
        <p className="section-kicker">Son bir adım</p>
        <h2 id="profile-title">Size nasıl hitap edelim?</h2>
        <form onSubmit={submitProfile}><label htmlFor="profile-name">Ad soyad</label><input id="profile-name" value={profileName} onChange={(event) => setProfileName(event.target.value)} autoComplete="name" required /><button type="submit" disabled={busy}>{busy ? "Kaydediliyor..." : "Devam et"}</button></form>
        {error && <p className="form-error" role="alert">{error}</p>}
      </section> : <section className="auth-panel" id="randevu" aria-labelledby="booking-title">
        <p className="section-kicker">Randevu al</p>
        <h2 id="booking-title">Size uygun zamanı seçin.</h2>
        <label htmlFor="service">Hizmet</label>
        <select id="service" value={selectedService} onChange={(event) => setSelectedService(event.target.value)}>
          <option value="">Hizmet seçin</option>
          {services.map((service) => <option key={service.id} value={service.id}>{service.name} · {service.price} TL · {service.duration_minutes} dk</option>)}
        </select>
        <label htmlFor="date">Tarih</label>
        <input id="date" type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} min={new Date().toISOString().slice(0, 10)} />
        <button type="button" onClick={loadAvailability} disabled={!selectedService || !selectedDate || busy}>Uygun saatleri göster</button>
        {slots.length > 0 && <div className="slot-grid">{slots.map((slot) => <button className="slot-button" key={slot.start_at} type="button" onClick={() => bookSlot(slot)} disabled={busy}>{new Date(slot.start_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}</button>)}</div>}
        {slots.length === 0 && selectedDate && <p className="form-hint">Bir tarih ve hizmet seçerek uygun saatleri görebilirsiniz.</p>}
        <button className="text-button" type="button" onClick={loadAppointments}>Randevularımı göster</button>
        {appointments.length > 0 && <div className="appointment-list">{appointments.map((appointment) => <div className="appointment-item" key={appointment.id}><strong>{new Date(appointment.start_at).toLocaleString("tr-TR")}</strong><span>{appointment.status === "cancelled" ? "İptal edildi" : "Onaylandı"}</span></div>)}</div>}
        {message && <p className="form-hint" role="status">{message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </section>}
      <section className="service-preview" aria-label="Hizmetler"><p className="section-kicker">Bugünün ritmi</p><h2>Koltuğunuz hazır.</h2><p>Saç kesimi, sakal veya ikisi birden. Size uyan zamanı bulun.</p></section>
    </main>
  );
}