// MISSION-02: Endpoint exists, but returns no suggestions until Trie is implemented.
const destination = document.getElementById('city-search');
if (destination) {
  let seq = 0;
  destination.addEventListener('input', async () => {
    const q = destination.value.trim();
    const list = document.getElementById('city-suggestions');
    const request = ++seq;
    list.replaceChildren();
    if (q.length < 2) return;
    try {
      const response = await fetch('/api/cities/suggest?q=' + encodeURIComponent(q));
      if (!response.ok) return;
      const data = await response.json();
      if (request !== seq) return;
      for (const city of data.suggestions || []) {
        const opt = document.createElement('option');
        opt.value = city;
        list.append(opt);
      }
    } catch (_) { /* network unavailable; manual search still works */ }
  });
}

// MISSION-03: Customer action is wired, but the backend intentionally says
// "not supported" until the students design the change transaction.
document.querySelectorAll('.change-booking').forEach(form => {
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const message = form.querySelector('.change-feedback');
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    message.textContent = 'Prüfe Änderungswunsch…';
    const values = new FormData(form);
    try {
      const response = await fetch('/api/reservations/' + encodeURIComponent(form.dataset.reservationId), {
        method: 'PATCH', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({checkin: values.get('checkin'), checkout: values.get('checkout')})
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        message.textContent = data.message || data.detail || 'Änderung noch nicht möglich.';
      } else {
        message.textContent = 'Aufenthalt erfolgreich geändert. Bitte Seite neu laden.';
      }
    } catch (_) { message.textContent = 'Verbindung fehlgeschlagen.'; }
    finally { button.disabled = false; }
  });
});
