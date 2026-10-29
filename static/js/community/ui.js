// Notifikasi singkat yang hilang sendiri setelah 3 detik; `type`: success, info, atau danger
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

// Ubah string HTML dari server menjadi elemen DOM (elemen pertamanya saja)
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

// Tambahkan elemen dari HTML server ke akhir `list`, kecuali yang `data-id`-nya sudah tampil.
// Paginasi berbasis offset menggeser halaman saat item ditambah/dihapus di klien.
export function appendNew(list, html) {
  const tpl = document.createElement('template');
  tpl.innerHTML = html;
  const seen = new Set([...list.children].map((el) => el.dataset.id).filter(Boolean));
  [...tpl.content.children].forEach((el) => {
    if (!el.dataset.id || !seen.has(el.dataset.id)) list.appendChild(el);
  });
}
