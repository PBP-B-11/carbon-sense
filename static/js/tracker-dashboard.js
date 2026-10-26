(() => {
  //Bagikan pembaruan dashboard untuk penyimpanan dan penghapusan aktivitas.
  window.CarbonTracker = window.CarbonTracker || {};

  async function refreshDashboard(url, message, options = {}) {
    const { preserveForm = false, historyMode = "replace", signal } = options;
    const controller = new AbortController();
    //Permintaan filter yang lebih baru boleh membatalkan hasil filter sebelumnya.
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) controller.abort();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    let page;
    try {
      const response = await fetch(url, {
        credentials: "same-origin",
        headers: { Accept: "text/html" },
        cache: "no-store",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("Dashboard refresh failed");
      page = new DOMParser().parseFromString(await response.text(), "text/html");
    } finally {
      window.clearTimeout(timeout);
      signal?.removeEventListener("abort", abort);
    }

    if (signal?.aborted) throw new DOMException("Request cancelled", "AbortError");

    const replacement = page.getElementById("tracker-dashboard");
    if (!replacement?.querySelector("#catat-cepat")) {
      throw new Error("Dashboard content missing");
    }
    const current = document.getElementById("tracker-dashboard");
    const activeElement = document.activeElement;
    const currentForm = current.querySelector("[data-tracker-form]");
    const keepFocus = preserveForm && currentForm.contains(activeElement);

    //Filter hanya mengganti ringkasan: pertahankan input, pratinjau, dan listener formulir.
    if (preserveForm) {
      const freshForm = replacement.querySelector("[data-tracker-form]");
      currentForm.setAttribute("action", freshForm.getAttribute("action"));
      currentForm.dataset.dashboardUrl = freshForm.dataset.dashboardUrl;
      const cancel = currentForm.querySelector("[data-tracker-cancel]");
      const freshCancel = freshForm.querySelector("[data-tracker-cancel]");
      if (cancel && freshCancel) cancel.href = freshCancel.href;
      freshForm.replaceWith(currentForm);
    }

    current.replaceWith(replacement);
    document.title = page.title;
    if (historyMode === "push") window.history.pushState(null, "", url);
    if (historyMode === "replace") window.history.replaceState(null, "", url);
    //Tutup dialog dan pasang kembali penanganan formulir setelah konten diganti.
    document.dispatchEvent(new Event("tracker:dashboard-updated"));
    document.dispatchEvent(new Event("tracker:form-ready"));
    if (message) {
      const confirmation = document.getElementById("activity-status");
      confirmation.textContent = message;
      confirmation.hidden = false;
      confirmation.focus({ preventScroll: true });
    } else if (keepFocus) {
      activeElement.focus({ preventScroll: true });
    } else if (preserveForm) {
      replacement.querySelector('[data-period-filter][aria-current="true"]').focus({ preventScroll: true });
    }
  }

  window.CarbonTracker.refreshDashboard = refreshDashboard;
})();
