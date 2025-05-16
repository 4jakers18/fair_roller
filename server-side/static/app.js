(() => {
  const logEl    = document.getElementById('logs');
  const stateEl  = document.getElementById('state');
  const preview  = document.getElementById('preview');

  function log(msg) {
    logEl.textContent += msg + '\n';
    logEl.scrollTop = logEl.scrollHeight;
  }

  // ─── Load current config ────────────────────────────────────────────────
  fetch('/config')
    .then(res => res.json())
    .then(cfg => {
      document.getElementById('sides').value        = cfg.sides;
      document.getElementById('rolls').value        = cfg.rolls;
      document.getElementById('settle_ms').value    = cfg.settle_ms;
      document.getElementById('frame_size').value   = cfg.frame_size;
      document.getElementById('jpeg_quality').value = cfg.jpeg_quality;
      log('Config loaded');
    })
    .catch(err => log('Error loading config: ' + err));

  // ─── Save config handler ──────────────────────────────────────────────
  document.getElementById('saveConfig').onclick = () => {
    const updates = {
      sides:        +document.getElementById('sides').value,
      rolls:        +document.getElementById('rolls').value,
      settle_ms:    +document.getElementById('settle_ms').value,
      frame_size:    document.getElementById('frame_size').value,
      jpeg_quality: +document.getElementById('jpeg_quality').value
    };
    fetch('/config', {
      method:  'POST',
      headers: {'Content-Type': 'application/json'},
      body:    JSON.stringify(updates)
    })
    .then(res => res.json())
    .then(j   => log('Config saved: ' + JSON.stringify(j)))
    .catch(err => log('Error saving config: ' + err));
  };

  // ─── Control buttons ──────────────────────────────────────────────────
  ['start','pause','resume','stop'].forEach(cmd => {
    document.getElementById(cmd).onclick = () => {
      fetch(`/${cmd}`, { method: 'POST' })
        .then(res => res.json())
        .then(j   => log(`/${cmd} → ${JSON.stringify(j)}`))
        .catch(err => log(`Error /${cmd}: ${err}`));
    };
  });

  // ─── WebSocket to receive status & step_ok ───────────────────────────
  const ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onopen = () => {
    log('WS connected');
    stateEl.textContent = 'Connected';
  };

  ws.onmessage = evt => {
    log('WS ← ' + evt.data);
    let msg;
    try {
      msg = JSON.parse(evt.data);
    } catch {
      return;
    }

    // If server broadcasts state commands
    if (msg.cmd) {
      stateEl.textContent = `State: ${msg.cmd}`;
    }

    // When a step completes, load the preview
    if (msg.evt === 'step_ok' && typeof msg.seq === 'number') {
      stateEl.textContent = `Rolling… seq ${msg.seq}`;
      // Preview file is saved by server as "<seq>.jpg"
      preview.src = `/uploads/${msg.seq}.jpg?` + Date.now();
    }
  };

  ws.onclose = () => {
    log('WS disconnected');
    stateEl.textContent = 'Disconnected';
  };

  ws.onerror = e => log('WS error: ' + (e.message || e));
})();
