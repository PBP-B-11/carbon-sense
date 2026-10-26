(() => {
  if (!window.fetch) return;
  const refreshDashboard = window.CarbonTracker.refreshDashboard;

  function initializeDeleteForm(form) {
    if (form.dataset.deleteReady) return;
    form.dataset.deleteReady = "true";
    const status = form.querySelector("[data-delete-status]");
    const button = form.querySelector('button[type="submit"]');
    let pending = false;

    //Penghapusan hanya dikirim setelah pengguna menekan tombol konfirmasi.
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (pending || form.dataset.deleteConfirmed) return;
      pending = true;
      form.dataset.saving = "true";
      const close = form.closest("[data-edit-modal]")?.querySelector("[data-edit-close]");
      if (close) close.disabled = true;
      button.disabled = true;
      const originalText = button.textContent;
      button.textContent = "Menghapus…";
      form.setAttribute("aria-busy", "true");
      status.textContent = "Sedang menghapus aktivitas…";
      status.hidden = false;
      let confirmed = false;
      let failureMessage = "Hasil penghapusan belum dapat dipastikan. Periksa riwayat atau muat ulang halaman sebelum mencoba lagi.";

      try {
        //FormData menyertakan token CSRF dari halaman konfirmasi milik pengguna.
        const response = await fetch(form.getAttribute("action"), {
          method: "POST", body: new FormData(form), credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
        });
        if (response.status === 403) failureMessage = "Permintaan ditolak. Muat ulang halaman, lalu coba lagi.";
        if (response.status === 404) failureMessage = "Aktivitas tidak ditemukan atau tidak dapat diakses.";
        if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) {
          throw new Error("Deletion failed");
        }
        const data = await response.json();
        if (data.activity_id == null) throw new Error("Deletion confirmation missing");
        confirmed = true;
        form.dataset.deleteConfirmed = "true";
        await refreshDashboard(form.dataset.dashboardUrl, data.message);
      } catch (error) {
        status.textContent = confirmed
          ? "Aktivitas sudah dihapus, tetapi tampilan belum diperbarui. Perbarui tampilan tanpa menghapus ulang."
          : failureMessage;
        if (confirmed) {
          //Jika hanya tampilan gagal diperbarui, ulangi GET dan jangan kirim POST lagi.
          const retry = document.createElement("button");
          retry.type = "button";
          retry.className = "btn";
          retry.textContent = "Perbarui tampilan";
          retry.addEventListener("click", async () => {
            retry.disabled = true;
            try {
              await refreshDashboard(form.dataset.dashboardUrl, "Aktivitas berhasil dihapus.");
            } catch {
              retry.disabled = false;
            }
          });
          status.append(document.createElement("br"), retry);
        }
      } finally {
        pending = false;
        delete form.dataset.saving;
        form.removeAttribute("aria-busy");
        button.disabled = confirmed;
        button.textContent = originalText;
        if (close) close.disabled = false;
      }
    });
  }

  function initializeForms() {
    document.querySelectorAll("[data-delete-form]").forEach(initializeDeleteForm);
  }
  document.addEventListener("tracker:form-ready", initializeForms);
  initializeForms();
})();
