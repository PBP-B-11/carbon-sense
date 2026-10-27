(() => {
  const dialog = document.getElementById("tracker-edit-dialog");
  if (!dialog || !window.fetch || typeof dialog.showModal !== "function") return;
  const content = dialog.querySelector("[data-edit-content]");
  const status = dialog.querySelector("[data-edit-status]");
  const title = dialog.querySelector("#tracker-edit-title");
  let controller = null;
  let opener = null;

  //Ubah ID dan referensi label agar formulir halaman dan modal tidak bertabrakan.
  function prepareModalContent(form, prefix) {
    const ids = new Map();
    for (const element of [form, ...form.querySelectorAll("[id]")]) {
      if (!element.id) continue;
      const original = element.id;
      element.id = `${prefix}-${original}`;
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
    return Boolean(content.querySelector('[data-saving="true"]'));
  }

  function closeModal() {
    if (isSaving()) return;
    controller?.abort();
    dialog.close();
  }

  async function openModal(link) {
    const deleting = link.classList.contains("history-delete");
    opener = link;
    controller?.abort();
    const request = new AbortController();
    controller = request;
    const timeout = window.setTimeout(() => request.abort(), 15000);
    content.replaceChildren();
    title.textContent = deleting ? "Hapus aktivitas" : "Edit aktivitas";
    dialog.querySelector("[data-edit-close]").setAttribute("aria-label", deleting ? "Tutup dialog hapus" : "Tutup dialog edit");
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
      const form = page.querySelector(deleting ? "[data-delete-confirmation]" : "[data-tracker-form]");
      if (!form) throw new Error("Edit form missing");
      if (!dialog.open || request !== controller) return;
      if (deleting) {
        //Gunakan periode dashboard yang sedang tampil untuk pembaruan setelah hapus.
        form.querySelector("[data-delete-form]").dataset.dashboardUrl =
          document.getElementById("catat-cepat").dataset.dashboardUrl;
      }
      content.append(prepareModalContent(form, deleting ? "delete" : "edit"));
      status.hidden = true;
      document.dispatchEvent(new Event("tracker:form-ready"));
      //Pada konfirmasi hapus, fokus awal berada pada Batal.
      content.querySelector(deleting ? "[data-tracker-cancel]" : '[name="quantity"]').focus({ preventScroll: true });
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
    const link = event.target.closest("a.history-edit, a.history-delete");
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    //Tunggu penyimpanan pada halaman selesai sebelum membuka formulir edit lain.
    if (document.querySelector('[data-saving="true"]')) {
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
