document.querySelectorAll('[data-profile-update-form]').forEach((form) => {
  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector('[data-profile-save-status]');
  const fields = [...form.querySelectorAll('.profile-field input, .profile-field textarea')];
  let cooldownTimer;

  const setLocked = (locked) => {
    button.disabled = locked;
    fields.forEach((field) => {
      field.disabled = locked;
    });
  };

  const clearErrors = () => {
    form.querySelectorAll('.errorlist').forEach((list) => list.remove());
    fields.forEach((field) => field.removeAttribute('aria-invalid'));
  };

  const showErrors = (errors) => {
    clearErrors();
    Object.entries(errors || {}).forEach(([name, messages]) => {
      const field = form.elements.namedItem(name);
      if (!field || name === '__all__') return;

      field.setAttribute('aria-invalid', 'true');
      const list = document.createElement('ul');
      list.className = 'errorlist';
      messages.forEach((message) => {
        const item = document.createElement('li');
        item.textContent = message;
        list.append(item);
      });
      field.parentElement.append(list);
    });
  };

  const startCooldown = (seconds, saved = false) => {
    clearInterval(cooldownTimer);
    const endsAt = Date.now() + Math.max(0, seconds) * 1000;
    setLocked(seconds > 0);
    if (seconds <= 0) return;

    const updateStatus = () => {
      const remaining = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
      if (!remaining) {
        clearInterval(cooldownTimer);
        setLocked(false);
        status.textContent = 'Profil bisa diubah kembali.';
        return;
      }
      status.hidden = false;
      status.textContent = saved
        ? `Profil tersimpan. Kamu bisa mengubahnya lagi dalam ${remaining} detik.`
        : `Kamu bisa mengubah profil lagi dalam ${remaining} detik.`;
    };

    updateStatus();
    cooldownTimer = setInterval(updateStatus, 1000);
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearErrors();
    const data = new FormData(form);
    setLocked(true);
    status.hidden = false;
    status.textContent = 'Menyimpan perubahan...';

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: data,
        headers: {Accept: 'application/json'},
      });
      if (response.redirected) throw new Error('Sesi berakhir. Silakan masuk kembali.');

      const result = await response.json();
      if (response.status === 429) {
        startCooldown(Math.max(1, Number(result.retry_after)), false);
        return;
      }
      if (!response.ok) {
        showErrors(result.errors);
        setLocked(false);
        status.textContent = result.errors?.__all__?.join(' ') || 'Periksa kembali isian yang ditandai.';
        return;
      }

      document.querySelector('[data-profile-email]').textContent = result.email;
      document.querySelector('[data-profile-bio]').textContent = result.bio;
      startCooldown(result.cooldown, true);
    } catch (error) {
      setLocked(false);
      status.textContent = error.message || 'Gagal menyimpan perubahan. Periksa koneksi lalu coba lagi.';
    }
  });

  const initialCooldown = Number(form.dataset.cooldown);
  if (initialCooldown > 0) startCooldown(initialCooldown);
});
