document.querySelectorAll('[data-city-picker]').forEach((picker) => {
  const queryInput = picker.querySelector('[data-city-query]');
  const citySelect = picker.querySelector('[data-city-results]');
  const status = picker.querySelector('[data-city-status]');
  let timer;
  let controller;

  queryInput.addEventListener('input', () => {
    clearTimeout(timer);
    controller?.abort();
    citySelect.size = 1;
    citySelect.replaceChildren(new Option('Ketik minimal 2 karakter untuk mencari', ''));
    const query = queryInput.value.trim();

    if (query.length < 2) {
      status.textContent = 'Ketik minimal 2 karakter untuk mencari.';
      return;
    }

    status.textContent = 'Mencari kota...';
    timer = setTimeout(async () => {
      controller = new AbortController();
      const url = new URL(picker.dataset.cityUrl, window.location.origin);
      url.searchParams.set('q', query);

      try {
        const response = await fetch(url, {signal: controller.signal});
        if (!response.ok) throw new Error('City search failed');
        const {results} = await response.json();
        if (query !== queryInput.value.trim()) return;

        citySelect.size = Math.min(results.length || 1, 5);
        citySelect.replaceChildren(new Option('Pilih kota', ''));
        results.forEach(({label, token}) => citySelect.add(new Option(label, token)));
        status.textContent = results.length ? 'Pilih kota dari daftar.' : 'Tidak ada kota yang ditemukan.';
      } catch (error) {
        if (error.name !== 'AbortError' && query === queryInput.value.trim()) {
          citySelect.replaceChildren(new Option('Pencarian gagal', ''));
          status.textContent = 'Pencarian kota gagal. Coba lagi.';
        }
      }
    }, 300);
  });

  citySelect.addEventListener('change', () => {
    if (citySelect.value) citySelect.size = 1;
  });

  if (citySelect.value) status.textContent = 'Kota dipilih.';
  else if (queryInput.value.trim().length >= 2) queryInput.dispatchEvent(new Event('input'));
});
