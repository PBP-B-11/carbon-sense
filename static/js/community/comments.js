import {parse, sendForm} from './http.js';
import {htmlToEl, toast} from './ui.js';

export function initComments() {
  const list = document.getElementById('comments');
  const counter = document.getElementById('comment-count');
  const form = document.getElementById('comment-form');
  let errorEl = null;

  function clearError() {
    errorEl?.remove();
    errorEl = null;
  }

  function showError(text) {
    clearError();
    errorEl = document.createElement('p');
    errorEl.setAttribute('role', 'alert');
    errorEl.textContent = text;
    (form || list).before(errorEl);
  }

  function ensureEmptyNote() {
    if (!list.querySelector('.comment') && !list.querySelector('.comment-empty')) {
      const p = document.createElement('p');
      p.className = 'comment-empty';
      p.textContent = 'Belum ada komentar.';
      list.appendChild(p);
    }
  }

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      const result = await parse(await sendForm(form));
      if (!result) return;
      if (!result.ok) {
        showError(result.data.error || 'Komentar tidak valid.');
        return;
      }
      clearError();
      list.querySelector('.comment-empty')?.remove();
      list.appendChild(htmlToEl(result.data.html));
      counter.textContent = result.data.count;
      form.elements.content.value = '';
      toast('Komentar terkirim.', 'success');
    } catch {
      form.submit();
    } finally {
      btn.disabled = false;
    }
  });

  const editDialog = document.getElementById('comment-edit-dialog');
  const editForm = document.getElementById('comment-edit-form');
  let editing = null;

  list.addEventListener('click', (event) => {
    const btn = event.target.closest('.js-comment-edit');
    if (!btn) return;
    editing = btn.closest('.comment');
    editForm.action = btn.dataset.action;
    editForm.elements.content.value = btn.dataset.content;
    editDialog.showModal();
  });

  editForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const btn = editForm.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      const result = await parse(await sendForm(editForm));
      if (!result) return;
      if (!result.ok) {
        showError(result.data.error || 'Komentar tidak valid.');
        editDialog.close();
        return;
      }
      clearError();
      editing.replaceWith(htmlToEl(result.data.html));
      editDialog.close();
      toast('Komentar diperbarui.', 'info');
    } catch {
      editForm.submit();
    } finally {
      btn.disabled = false;
    }
  });

  document.getElementById('comment-edit-cancel').addEventListener('click', () => editDialog.close());

  // Optimistic UI: komentar langsung hilang, dikembalikan jika server gagal
  const deleteDialog = document.getElementById('comment-delete-dialog');
  const deleteConfirm = document.getElementById('comment-delete-confirm');
  let pending = null;

  list.addEventListener('submit', (event) => {
    const f = event.target;
    if (!f.matches('.js-comment-delete-form')) return;
    event.preventDefault();
    pending = f;
    deleteDialog.showModal();
  });

  deleteConfirm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const f = pending;
    pending = null;
    deleteDialog.close();
    if (!f) return;

    const comment = f.closest('.comment');
    const parent = comment.parentNode;
    const next = comment.nextElementSibling;
    const before = Number(counter.textContent);
    comment.remove();
    counter.textContent = before - 1;
    ensureEmptyNote();

    try {
      const result = await parse(await sendForm(f));
      if (!result) return;
      if (!result.ok) throw new Error('delete failed');
      counter.textContent = result.data.count;
      toast('Komentar dihapus.', 'danger');
    } catch {
      list.querySelector('.comment-empty')?.remove();
      parent.insertBefore(comment, next);
      counter.textContent = before;
      toast('Komentar gagal dihapus.', 'danger');
    }
  });

  document.getElementById('comment-delete-cancel').addEventListener('click', () => {
    pending = null;
    deleteDialog.close();
  });
}
