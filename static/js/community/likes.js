import {parse, sendForm} from './http.js';
import {toast} from './ui.js';

// Samakan tampilan tombol suka dengan status dan jumlah yang diberikan
function render(btn, counter, liked, count) {
  btn.classList.toggle('liked', liked);
  btn.setAttribute('aria-pressed', String(liked));
  counter.textContent = count;
}

// Optimistic UI: tampilan berubah dulu, lalu disamakan dengan server atau dikembalikan jika gagal
export function initLikes(root) {
  root.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!form.matches('.js-like-form')) return;
    event.preventDefault();

    const btn = form.querySelector('button');
    if (btn.dataset.pending) return;
    const counter = form.querySelector('.like-count');
    const wasLiked = btn.classList.contains('liked');
    const before = Number(counter.textContent);

    render(btn, counter, !wasLiked, before + (wasLiked ? -1 : 1));
    btn.dataset.pending = '1';
    try {
      const result = await parse(await sendForm(form));
      if (!result) return;
      if (!result.ok) throw new Error('like failed');
      render(btn, counter, result.data.liked, result.data.count);
    } catch {
      render(btn, counter, wasLiked, before);
      toast('Gagal memperbarui suka. Coba lagi.', 'danger');
    } finally {
      delete btn.dataset.pending;
    }
  });
}
