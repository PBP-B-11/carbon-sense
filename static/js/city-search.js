document.querySelectorAll('[data-city-picker]').forEach((picker) => {
  const queryInput = picker.querySelector('[data-city-query]');
  const citySelect = picker.querySelector('[data-city-results]');
  const status = picker.querySelector('[data-city-status]');
  const saveForm = picker.querySelector('[data-city-save-form]');
  const saveStatus = picker.querySelector('[data-city-save-status]');
  let timer;
  let controller;

  queryInput.addEventListener('input', () => {
    if (saveStatus) {
      saveStatus.textContent = '';
      saveStatus.hidden = true;
    }
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
    if (saveStatus) {
      saveStatus.textContent = '';
      saveStatus.hidden = true;
    }
  });

  if (saveForm) {
    const saveButton = saveForm.querySelector('button[type="submit"]');
    saveForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(saveForm);
      let failure = 'Gagal menyimpan kota. Coba lagi.';
      saveButton.disabled = true;
      queryInput.disabled = true;
      citySelect.disabled = true;
      saveStatus.hidden = false;
      saveStatus.textContent = 'Menyimpan kota...';

      try {
        const response = await fetch(saveForm.action, {
          method: 'POST',
          body: formData,
          headers: {Accept: 'application/json'},
        });
        if (response.redirected) {
          failure = 'Sesi berakhir. Muat ulang halaman untuk masuk kembali.';
          throw new Error();
        }
        const result = await response.json();
        if (!response.ok) {
          failure = result.error || failure;
          throw new Error();
        }

        document.querySelectorAll('[data-profile-city]').forEach((element) => {
          element.textContent = result.city;
        });
        document.querySelector('[data-profile-air]').outerHTML = result.air_html;
        saveStatus.textContent = 'Kota berhasil disimpan.';
      } catch {
        saveStatus.textContent = failure;
      } finally {
        saveButton.disabled = false;
        queryInput.disabled = false;
        citySelect.disabled = false;
      }
    });
  }

  if (citySelect.value) status.textContent = 'Kota dipilih.';
  else if (queryInput.value.trim().length >= 2) queryInput.dispatchEvent(new Event('input'));
});
