(() => {
  const dialog = document.getElementById("tracker-edit-dialog");
  if (!dialog || !window.fetch || typeof dialog.showModal !== "function") return;
  const content = dialog.querySelector("[data-edit-content]");
  const status = dialog.querySelector("[data-edit-status]");
  let controller = null;
  let opener = null;

  //Ubah ID dan referensi label agar formulir halaman dan modal tidak bertabrakan.
  function prepareModalForm(form) {
    const ids = new Map();
    for (const element of [form, ...form.querySelectorAll("[id]")]) {
      if (!element.id) continue;
      const original = element.id;
      element.id = `edit-${original}`;
      ids.set(original, element.id);
    }
    for (const element of [form, ...form.querySelectorAll("[for], [aria-labelledby], [aria-describedby]")]) {
      for (const attribute of ["for", "aria-labelledby", "aria-describedby"]) {
        const references = element.getAttribute(attribute);
        if (references) {
          element.setAttribute(attribute, references.split(/\s+/).map((id) => ids.get(id) || id).join(" "));
        }
      }
    }
    return form;
  }

  function isSaving() {
    return content.querySelector("[data-tracker-form]")?.dataset.saving === "true";
  }

  function closeModal() {
    if (isSaving()) return;
    controller?.abort();
    dialog.close();
  }

  async function openModal(link) {
    opener = link;
    controller?.abort();
    const request = new AbortController();
    controller = request;
    const timeout = window.setTimeout(() => request.abort(), 15000);
    content.replaceChildren();
    status.textContent = "Memuat aktivitas…";
    status.hidden = false;
    dialog.showModal();
    document.body.classList.add("tracker-modal-open");

    try {
      const response = await fetch(link.href, {
        credentials: "same-origin", headers: { Accept: "text/html" }, signal: request.signal,
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Edit form unavailable");
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const form = page.querySelector("[data-tracker-form]");
      if (!form) throw new Error("Edit form missing");
      if (!dialog.open || request !== controller) return;
      content.append(prepareModalForm(form));
      status.hidden = true;
      document.dispatchEvent(new Event("tracker:form-ready"));
      content.querySelector('[name="quantity"]').focus({ preventScroll: true });
    } catch (error) {
      if (!dialog.open || request !== controller) return;
      status.textContent = "Gagal memuat aktivitas. Tutup dialog dan coba lagi.";
    } finally {
      window.clearTimeout(timeout);
    }
  }

  //Delegasi tetap bekerja setelah tabel riwayat diganti melalui AJAX.
  document.addEventListener("click", (event) => {
    const cancel = event.target.closest("[data-tracker-cancel]");
    if (cancel && dialog.contains(cancel)) {
      event.preventDefault();
      closeModal();
      return;
    }
    const link = event.target.closest("a.history-edit");
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    //Tunggu penyimpanan pada halaman selesai sebelum membuka formulir edit lain.
    if (document.querySelector('[data-tracker-form][data-saving="true"]')) {
      event.preventDefault();
      return;
    }
    event.preventDefault();
    openModal(link);
  });
  dialog.querySelector("[data-edit-close]").addEventListener("click", closeModal);
  dialog.addEventListener("cancel", (event) => {
    if (isSaving()) event.preventDefault();
  });
  dialog.addEventListener("close", () => {
    controller?.abort();
    content.replaceChildren();
    document.body.classList.remove("tracker-modal-open");
    if (opener?.isConnected) opener.focus({ preventScroll: true });
  });
  document.addEventListener("tracker:dashboard-updated", () => {
    if (dialog.open) dialog.close();
  });
})();
