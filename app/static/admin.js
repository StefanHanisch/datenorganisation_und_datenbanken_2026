const root = document.querySelector('.admin-layout');
if (root) {
  const $ = (selector) => document.querySelector(selector);
  const setTab = (id) => {
    for (const b of document.querySelectorAll('.side-button')) b.classList.toggle('active', b.dataset.tab === id);
    for (const el of document.querySelectorAll('.panel-section')) el.classList.toggle('active', el.id === 'tab-' + id);
    if (id === 'overview') refreshStats();
  };
  document.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
  document.querySelectorAll('[data-tab-link]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); setTab(a.dataset.tabLink); }));
  const fetchJson = async (url, init={}) => { const r = await fetch(url, init); const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'HTTP ' + r.status); return data; };
  const fmt = (value) => (value ?? '—').toLocaleString('de-DE');
  async function refreshStats() {
    try {
      const data = await fetchJson('/api/admin/stats');
      const keys = ['hotels', 'rooms', 'guests', 'reservations'];
      $('#stats').querySelectorAll('.metric strong').forEach((node, i) => node.textContent = fmt(data.counts[keys[i]]));
    } catch (_) { /* stat service may be unavailable during DB setup */ }
  }
  refreshStats();

  const tables = ['cities', 'hotels', 'room_categories', 'rooms', 'guests', 'reservations'];
  for (const t of tables) {
    const b = document.createElement('button'); b.textContent = t;
    b.addEventListener('click', async () => {
      $('#table-output').textContent = 'Lade ' + t + '…';
      try { const d = await fetchJson('/api/admin/tables/' + t); $('#table-output').textContent = JSON.stringify(d.rows, null, 2); }
      catch (e) { $('#table-output').textContent = e.message; }
    });
    $('#table-buttons').append(b);
  }
  const output = $('#sql-output');
  const runSql = async (explain) => {
    const sql = $('#sql-input').value;
    $('#sql-status').textContent = 'Abfrage läuft…';
    output.replaceChildren();
    const t0 = performance.now();
    try {
      const d = await fetchJson('/api/admin/sql', {
        method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({sql, explain})
      });
      $('#sql-status').textContent = (performance.now()-t0).toFixed(0) + ' ms inklusive Netzwerk';
      if (d.type === 'error') throw new Error(d.message);
      if (d.type === 'explain') {
        const pre = document.createElement('pre'); pre.textContent = JSON.stringify(d.plan, null, 2); output.append(pre);
      } else {
        const table = document.createElement('table');
        const tr = document.createElement('tr');
        for (const h of d.columns) { const th = document.createElement('th'); th.textContent=h; tr.append(th); }
        const head = document.createElement('thead');head.append(tr);table.append(head);
        const body = document.createElement('tbody');
        for (const row of d.rows) {
          const tr = document.createElement('tr');
          for (const key of d.columns) { const td = document.createElement('td'); const v = row[key]; td.textContent = v === null ? 'NULL' : typeof v === 'object' ? JSON.stringify(v) : String(v);tr.append(td); }
          body.append(tr);
        }
        table.append(body);output.append(table);
        if (d.truncated) { const p = document.createElement('p');p.textContent = 'Weitere Zeilen vorhanden. Begrenze die Abfrage mit LIMIT.';output.append(p); }
      }
    } catch(e) { const pre=document.createElement('pre');pre.textContent='Fehler: '+e.message;output.append(pre);$('#sql-status').textContent='Abfrage fehlgeschlagen'; }
  };
  $('#sql-run').addEventListener('click',()=>runSql(false));
  $('#sql-plan').addEventListener('click',()=>runSql(true));

  const action = $('#admin-action');
  if (action) {
    const fields = {
      cities: [['name','Stadtname','Berlin'],['country','Land','Deutschland']],
      hotels: [['city_id','Stadt-ID (aus Datenexplorer)','1'],['name','Hotelname','GlobalStay Hamburg Airport'],['address','Adresse','Flughafenstraße 1'],['stars','Sterne (1-5)','4']],
      'room-categories': [['hotel_id','Hotel-ID','1'],['name','Kategorie','Standard'],['base_price','Preis pro Nacht','109'],['max_guests','Max. Personen','2']],
      rooms: [['category_id','Kategorie-ID','1'],['room_number','Zimmernummer','STD-001']],
    };
    const numeric = new Set(['city_id','hotel_id','stars','base_price','max_guests','category_id']);
    function renderAction() {
      const box = $('#admin-fields');box.replaceChildren();
      for (const [name,label,placeholder] of fields[action.value]) {
        const wrapper = document.createElement('label');wrapper.textContent=label;
        const input = document.createElement('input');input.name=name;input.placeholder=placeholder;input.required=true;
        if(numeric.has(name)) {input.type='number';input.step=name==='base_price'?'0.01':'1';input.min='1';}
        wrapper.append(input);box.append(wrapper);
      }
    }
    action.addEventListener('change',renderAction);renderAction();
    $('#admin-action-form').addEventListener('submit',async e=>{
      e.preventDefault();const values={};
      for (const el of e.target.querySelectorAll('input')) values[el.name]=numeric.has(el.name)?Number(el.value):el.value;
      try {const out=await fetchJson('/api/admin/'+action.value, {method:'POST', headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});$('#admin-response').textContent=JSON.stringify(out,null,2);refreshStats();}
      catch(err){$('#admin-response').textContent='Fehler: '+err.message;}
    });
  }
}
