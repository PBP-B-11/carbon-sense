(() => {
  //Bagikan pembaruan dashboard untuk penyimpanan dan penghapusan aktivitas.
  window.CarbonTracker = window.CarbonTracker || {};

  async function refreshDashboard(url, message) {
    const controller = new AbortController();
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
    }

    const replacement = page.getElementById("tracker-dashboard");
    if (!replacement?.querySelector("#catat-cepat")) {
      throw new Error("Dashboard content missing");
    }
    document.getElementById("tracker-dashboard").replaceWith(replacement);
    document.title = page.title;
    window.history.replaceState(null, "", url);
    //Tutup dialog dan pasang kembali penanganan formulir setelah konten diganti.
    document.dispatchEvent(new Event("tracker:dashboard-updated"));
    document.dispatchEvent(new Event("tracker:form-ready"));
    const confirmation = document.getElementById("activity-status");
    confirmation.textContent = message;
    confirmation.hidden = false;
    confirmation.focus({ preventScroll: true });
  }

  window.CarbonTracker.refreshDashboard = refreshDashboard;
})();
