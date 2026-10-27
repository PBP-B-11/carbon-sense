import {parse, sendForm} from './http.js';
import {clearNote, htmlToEl, showNote, toast} from './ui.js';

const EMPTY_TEXT = 'Belum ada postingan. Jadilah yang pertama bercerita.';

function ensureEmptyNote(list) {
  if (!list.querySelector('article.post') && !list.querySelector('.feed-empty')) {
    const note = document.createElement('p');
    note.className = 'card feed-note feed-empty';
    note.textContent = EMPTY_TEXT;
    list.appendChild(note);
  }
}

// Kartu baru hanya disisipkan di atas jika urutannya terbaru, tanpa pencarian,
// dan sesuai filter kategori yang sedang aktif
function prependCard(list, html) {
  const card = htmlToEl(html);
  const {category, query, sort} = list.dataset;
  if (query || sort === 'popular') return;
  list.querySelector('.feed-empty')?.remove();
  if (!category || category === card.dataset.category) list.prepend(card);
}

function initCompose(feed, list) {
  const form = feed.querySelector('.js-compose-form');
  if (!form) return;

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      const result = await parse(await sendForm(form));
      if (!result) return;
      if (!result.ok) {
        showNote(feed, result.data.error || 'Postingan tidak valid.');
        return;
      }
      clearNote(feed);
      prependCard(list, result.data.html);
      form.elements.content.value = '';
      toast('Postingan berhasil dibagikan.', 'success');
    } catch {
      toast('Gagal mengirim postingan. Coba lagi.', 'danger');
    } finally {
      btn.disabled = false;
    }
  });
}

function initEdit(feed, list) {
  const dialog = document.getElementById('edit-dialog');
  const form = document.getElementById('edit-form');
  let editingCard = null;

  feed.addEventListener('click', (event) => {
    const btn = event.target.closest('.js-edit');
    if (!btn) return;
    editingCard = btn.closest('article.post');
    const hasNews = btn.dataset.hasNews === '1';
    form.action = btn.dataset.action;
    form.elements.content.value = btn.dataset.content;
    form.elements.content.required = !hasNews;
    form.querySelectorAll('input[name=category]').forEach((radio) => {
      radio.checked = radio.value === btn.dataset.category;
      radio.disabled = hasNews;
    });
    dialog.showModal();
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      const result = await parse(await sendForm(form));
      if (!result) return;
      if (!result.ok) {
        showNote(feed, result.data.error || 'Perubahan tidak valid.');
        dialog.close();
        return;
      }
      clearNote(feed);
      const updated = htmlToEl(result.data.html);
      const filter = list.dataset.category;
      if (filter && filter !== updated.dataset.category) editingCard.remove();
      else editingCard.replaceWith(updated);
      ensureEmptyNote(list);
      dialog.close();
      toast('Postingan berhasil diperbarui.', 'info');
    } catch {
      toast('Gagal menyimpan perubahan. Coba lagi.', 'danger');
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById('edit-cancel').addEventListener('click', () => dialog.close());
}

// Optimistic UI: kartu langsung hilang, dikembalikan ke posisinya jika server gagal
function initDelete(feed, list) {
  const dialog = document.getElementById('delete-dialog');
  const confirmForm = document.getElementById('delete-confirm-form');
  let pending = null;

  feed.addEventListener('submit', (event) => {
    const form = event.target;
    if (!form.matches('.js-delete-form')) return;
    event.preventDefault();
    pending = form;
    dialog.showModal();
  });

  confirmForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = pending;
    pending = null;
    dialog.close();
    if (!form) return;

    const card = form.closest('article.post');
    const parent = card.parentNode;
    const next = card.nextElementSibling;
    card.remove();
    ensureEmptyNote(list);

    try {
      const result = await parse(await sendForm(form));
      if (!result) return;
      if (!result.ok) throw new Error('delete failed');
      toast('Postingan dihapus.', 'danger');
    } catch {
      list.querySelector('.feed-empty')?.remove();
      parent.insertBefore(card, next);
      toast('Postingan gagal dihapus.', 'danger');
    }
  });

  document.getElementById('delete-cancel').addEventListener('click', () => {
    pending = null;
    dialog.close();
  });
}

function initShare(feed, list) {
  const dialog = document.getElementById('share-dialog');
  const form = dialog.querySelector('form');

  document.querySelectorAll('.js-share').forEach((btn) => {
    btn.addEventListener('click', () => {
      form.elements.url.value = btn.dataset.url;
      form.elements.content.value = '';
      document.getElementById('share-news-title').textContent = btn.dataset.title;
      dialog.showModal();
    });
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      const result = await parse(await sendForm(form));
      if (!result) return;
      if (!result.ok) {
        showNote(feed, result.data.error || 'Berita tidak valid.');
        dialog.close();
        return;
      }
      clearNote(feed);
      prependCard(list, result.data.html);
      dialog.close();
      toast('Berita berhasil dibagikan ke feed.', 'success');
    } catch {
      toast('Gagal membagikan berita. Coba lagi.', 'danger');
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById('share-cancel').addEventListener('click', () => dialog.close());
}

export function initPosts(feed) {
  const list = document.getElementById('post-list');
  initCompose(feed, list);
  initEdit(feed, list);
  initDelete(feed, list);
  initShare(feed, list);
}
