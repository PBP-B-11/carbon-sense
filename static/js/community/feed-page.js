import {initFilter} from './filter.js';
import {initLikes} from './likes.js';
import {initPosts} from './posts.js';

const feed = document.querySelector('.feed');
initLikes(feed);
initPosts(feed);
initFilter();

// Kembali ke feed lewat tombol "back" menampilkan salinan lama (bfcache):
// muat ulang agar jumlah suka dan komentar terbaru ikut tampil.
window.addEventListener('pageshow', (event) => {
  if (event.persisted) window.location.reload();
});
