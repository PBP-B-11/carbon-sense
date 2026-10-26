(() => {
  if (!window.fetch || !document.querySelector("[data-period-filters]")) return;
  const refreshDashboard = window.CarbonTracker.refreshDashboard;
  let controller = null;
  let appliedUrl = window.location.href;

  function showStatus(message) {
    const status = document.getElementById("period-status");
    status.textContent = message;
    status.hidden = false;
  }

  async function selectPeriod(url, historyMode = "push") {
    //Abaikan hasil lama jika pengguna memilih beberapa periode dengan cepat.
    controller?.abort();
    const request = new AbortController();
    controller = request;
    document.querySelector("[data-period-filters]").setAttribute("aria-busy", "true");
    showStatus("Memuat ringkasan periode…");

    try {
      await refreshDashboard(url, null, {
        preserveForm: true, historyMode, signal: request.signal,
      });
      appliedUrl = window.location.href;
      const label = document.querySelector('[data-period-filter][aria-current="true"]').textContent;
      showStatus(`Menampilkan ${label.toLowerCase()}.`);
    } catch (error) {
      if (request.signal.aborted) return;
      //Jika navigasi Back gagal, cocokkan kembali URL dengan data yang masih tampil.
      if (historyMode === "none") window.history.replaceState(null, "", appliedUrl);
      showStatus("Gagal memuat periode. Ringkasan sebelumnya tetap ditampilkan; coba lagi.");
    } finally {
      if (controller === request) {
        document.querySelector("[data-period-filters]").removeAttribute("aria-busy");
        controller = null;
      }
    }
  }

  //Tautan tetap dapat dibuka biasa dengan Ctrl/Cmd atau tanpa JavaScript.
  document.addEventListener("click", (event) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest("a[data-period-filter]");
    if (link) {
      event.preventDefault();
      if (document.querySelector('[data-saving="true"]')) {
        showStatus("Tunggu aktivitas selesai diproses sebelum mengganti periode.");
        return;
      }
      if (!controller && link.getAttribute("aria-current") === "true") return;
      selectPeriod(link.href);
    } else if (controller && event.target.closest("a.history-edit, a.history-delete")) {
      //Jangan membuka dialog berdasarkan periode lama ketika filter masih dimuat.
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  //Tunggu filter selesai agar penyimpanan tidak berlomba dengan respons ringkasan lama.
  document.addEventListener("submit", (event) => {
    if (!controller || !event.target.matches("[data-tracker-form], [data-delete-form]")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    showStatus("Tunggu ringkasan periode selesai dimuat, lalu coba lagi.");
  }, true);

  window.addEventListener("popstate", () => {
    if (document.querySelector('[data-saving="true"]')) {
      window.history.replaceState(null, "", appliedUrl);
      showStatus("Tunggu aktivitas selesai diproses sebelum mengganti periode.");
      return;
    }
    selectPeriod(window.location.href, "none");
  });

  //Penyimpanan atau penghapusan juga dapat memperbarui URL dashboard.
  document.addEventListener("tracker:dashboard-updated", () => {
    appliedUrl = window.location.href;
  });
})();
