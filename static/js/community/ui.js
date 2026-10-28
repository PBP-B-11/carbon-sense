export function toast(text, type = 'success') {
  const region = document.getElementById('toast-region');
  if (!region) return;
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.textContent = text;
  region.appendChild(el);
  setTimeout(() => {
    el.classList.add('toast--out');
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

export function htmlToEl(html) {
  const tpl = document.createElement('template');
  tpl.innerHTML = html.trim();
  return tpl.content.firstElementChild;
}

// Pesan error yang menetap di atas container sampai aksi berikutnya berhasil
export function showNote(container, text) {
  let note = container.querySelector(':scope > .feed-error');
  if (!note) {
    note = document.createElement('p');
    note.className = 'card feed-note feed-error';
    note.setAttribute('role', 'alert');
    container.prepend(note);
  }
  note.textContent = text;
}

export function clearNote(container) {
  container.querySelector(':scope > .feed-error')?.remove();
}
