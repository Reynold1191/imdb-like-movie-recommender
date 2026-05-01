// User dropdown toggle
(function () {
  const btn = document.getElementById('userMenuBtn');
  const dropdown = document.getElementById('userDropdown');

  if (btn && dropdown) {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('open');
    });

    document.addEventListener('click', () => {
      dropdown.classList.remove('open');
    });

    dropdown.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }
})();

// Copy SQL to clipboard
function copySQL(btn) {
  const pre = btn.closest('.sql-disclosure-body').querySelector('.sql-code-text');
  if (!pre) return;
  navigator.clipboard.writeText(pre.textContent).then(() => {
    const orig = btn.innerHTML;
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.innerHTML = orig; }, 1500);
  });
}

// ── Universal table pagination ────────────────────────────────────────────────
// Any <table data-paginate="N"> gets automatic N-rows-per-page splitting.
(function initPagination() {

  function setup(table) {
    const pageSize = parseInt(table.dataset.paginate) || 10;
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length <= pageSize) return;

    let current = 1;
    const total = Math.ceil(rows.length / pageSize);

    const wrap = document.createElement('div');
    wrap.className = 'pg-wrap';
    table.parentNode.insertBefore(wrap, table.nextSibling);

    function show(page) {
      current = Math.max(1, Math.min(page, total));
      const start = (current - 1) * pageSize;
      rows.forEach((r, i) => {
        r.style.display = (i >= start && i < start + pageSize) ? '' : 'none';
      });
      render();
    }

    function render() {
      wrap.innerHTML = '';

      // info: "rows 1–10 of 47"
      const start = (current - 1) * pageSize + 1;
      const end   = Math.min(current * pageSize, rows.length);
      const info  = document.createElement('span');
      info.className = 'pg-info';
      info.textContent = `${start}–${end} of ${rows.length}`;
      wrap.appendChild(info);

      // controls: ‹  3  ›
      const ctrl = document.createElement('div');
      ctrl.className = 'pg-btns';

      const prev = document.createElement('button');
      prev.className = 'pg-arrow';
      prev.innerHTML = '&#8249;';
      prev.disabled = current === 1;
      prev.addEventListener('click', () => show(current - 1));
      ctrl.appendChild(prev);

      const lbl = document.createElement('span');
      lbl.className = 'pg-current';
      lbl.textContent = `${current} / ${total}`;
      ctrl.appendChild(lbl);

      const next = document.createElement('button');
      next.className = 'pg-arrow';
      next.innerHTML = '&#8250;';
      next.disabled = current === total;
      next.addEventListener('click', () => show(current + 1));
      ctrl.appendChild(next);

      wrap.appendChild(ctrl);
    }

    show(1);
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('table[data-paginate]').forEach(setup);
  });
})();

// Auto-dismiss flash messages after 5s
(function () {
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    });
  }, 5000);
})();
