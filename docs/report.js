/* ShadeMap community photo reports.
 * Talks to Supabase with plain fetch, no libraries. Enabled only when docs/config.js has a
 * project URL and anon key. Photos are re-encoded in the browser, which drops the GPS
 * location and other metadata a phone stores inside the file. */
(function () {
  "use strict";

  var cfg = window.SHADEMAP_CONFIG || {};
  var BASE = (cfg.supabaseUrl || "").replace(/\/+$/, "");
  var KEY = cfg.supabaseAnonKey || "";
  var BUCKET = cfg.bucket || "stop-photos";
  var ENABLED = !!(BASE && KEY);
  var MAX_SIDE = 1280;
  var COOLDOWN_MS = 30000;
  var PATH_OK = /^[0-9a-f-]{36}\.jpg$/;
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  var approved = null; // stop_id -> approved rows, loaded once
  var modal = null;
  var current = { stopId: "", stopName: "" };
  var lastFocus = null;

  // helpers -----------------------------------------------------------------------
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function authHeaders(extra) {
    var h = { apikey: KEY, Authorization: "Bearer " + KEY };
    for (var k in extra) h[k] = extra[k];
    return h;
  }
  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    var b = crypto.getRandomValues(new Uint8Array(16));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    var h = Array.prototype.map.call(b, function (x) { return pad(x.toString(16)).slice(-2); }).join("");
    return [h.slice(0, 8), h.slice(8, 12), h.slice(12, 16), h.slice(16, 20), h.slice(20)].join("-");
  }
  function bucketFor(t) {
    var h = parseInt(t.slice(0, 2), 10);
    if (h >= 5 && h < 11) return "morning";
    if (h >= 11 && h < 14) return "midday";
    if (h >= 14 && h < 18) return "afternoon";
    if (h >= 18 && h < 22) return "evening";
    return "night";
  }
  function fmtTime(t) {
    var h = parseInt(t.slice(0, 2), 10);
    return (h % 12 || 12) + ":" + t.slice(3, 5) + " " + (h >= 12 ? "PM" : "AM");
  }
  function fmtDate(d) {
    var p = d.split("-");
    return MONTHS[+p[1] - 1] + " " + +p[2] + ", " + p[0];
  }
  function today() {
    var d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }
  function nowHHMM() {
    var d = new Date();
    return pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  // photo processing: scale down and re-encode as JPEG, which removes EXIF and GPS ----
  async function shrink(file) {
    var bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
    var scale = Math.min(1, MAX_SIDE / Math.max(bmp.width, bmp.height));
    var w = Math.max(1, Math.round(bmp.width * scale));
    var h = Math.max(1, Math.round(bmp.height * scale));
    var canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    canvas.getContext("2d").drawImage(bmp, 0, 0, w, h);
    if (bmp.close) bmp.close();
    return new Promise(function (resolve, reject) {
      canvas.toBlob(function (b) { b ? resolve(b) : reject(new Error("encode failed")); }, "image/jpeg", 0.85);
    });
  }

  // the form ----------------------------------------------------------------------
  function buildModal() {
    var el = document.createElement("div");
    el.id = "report-modal";
    el.hidden = true;
    el.innerHTML =
      '<div class="rm-card" role="dialog" aria-modal="true" aria-labelledby="rm-title">' +
      '<button type="button" class="rm-x" aria-label="Close">&times;</button>' +
      '<h2 id="rm-title">Add a photo of this stop</h2>' +
      '<p class="rm-stop" id="rm-stop"></p>' +
      '<form id="rm-form" novalidate>' +
      '<label class="rm-l" for="rm-photo">Photo</label>' +
      '<input id="rm-photo" name="photo" type="file" accept="image/*">' +
      '<p class="rm-fine">Please do not include faces or license plates. Photos showing them will not be approved.</p>' +
      '<label class="rm-l" for="rm-date">When did you take it?</label>' +
      '<div class="rm-row"><input id="rm-date" name="date" type="date" required>' +
      '<input id="rm-time" name="time" type="time" required></div>' +
      '<label class="rm-l" for="rm-note">What does the stop look like? (optional)</label>' +
      '<textarea id="rm-note" name="note" maxlength="280" rows="3" placeholder="Shade, bench, shelter, sun exposure"></textarea>' +
      '<input class="rm-hp" name="website" type="text" tabindex="-1" autocomplete="off" aria-hidden="true">' +
      '<label class="rm-check"><input id="rm-consent" name="consent" type="checkbox"> ' +
      "<span>I took this photo or have permission to share it. It shows no faces or license plates. " +
      "I agree it may be shown on this map after review.</span></label>" +
      '<p class="rm-fine">Photos are reviewed before they appear. Location data inside the photo is removed before upload.</p>' +
      '<p id="rm-status" class="rm-status" role="status" aria-live="polite"></p>' +
      '<div class="rm-actions"><button type="button" class="rm-cancel">Cancel</button>' +
      '<button type="submit" class="rm-send">Send photo</button></div>' +
      "</form></div>";
    document.body.appendChild(el);
    el.addEventListener("click", function (e) { if (e.target === el) closeModal(); });
    el.querySelector(".rm-x").addEventListener("click", closeModal);
    el.querySelector(".rm-cancel").addEventListener("click", closeModal);
    el.querySelector("#rm-form").addEventListener("submit", submit);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !el.hidden) closeModal(); });
    return el;
  }

  function setStatus(msg, isError) {
    var s = modal.querySelector("#rm-status");
    s.textContent = msg || "";
    s.className = "rm-status" + (isError ? " rm-err" : msg ? " rm-ok" : "");
  }

  function openModal(stopId, stopName) {
    if (!modal) modal = buildModal();
    current = { stopId: String(stopId), stopName: stopName || "" };
    lastFocus = document.activeElement;
    var f = modal.querySelector("#rm-form");
    f.reset();
    f.date.value = today();
    f.date.max = today();
    f.time.value = nowHHMM();
    modal.querySelector("#rm-stop").textContent = stopName ? "Stop: " + stopName : "";
    modal.querySelector(".rm-send").disabled = false;
    setStatus("");
    modal.hidden = false;
    f.photo.focus();
  }

  function closeModal() {
    if (!modal) return;
    modal.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  async function submit(ev) {
    ev.preventDefault();
    var f = modal.querySelector("#rm-form");
    var send = modal.querySelector(".rm-send");
    if (f.website.value) { setStatus("Thank you. Your photo will be reviewed."); return; } // bot trap

    var file = f.photo.files && f.photo.files[0];
    if (!file) return setStatus("Choose a photo first.", true);
    if (file.type && file.type.indexOf("image/") !== 0) return setStatus("That file is not an image.", true);
    if (!f.date.value || !f.time.value) return setStatus("Enter the date and time you took the photo.", true);
    if (f.date.value + "T" + f.time.value > today() + "T" + nowHHMM()) {
      return setStatus("The photo cannot be from the future. Check the date and time.", true);
    }
    if (!f.consent.checked) return setStatus("Please confirm the statement above the send button.", true);

    var last = 0;
    try { last = +localStorage.getItem("shademap_last_report") || 0; } catch (e) { /* storage blocked */ }
    if (Date.now() - last < COOLDOWN_MS) return setStatus("Please wait a few seconds before sending another photo.", true);

    send.disabled = true;
    try {
      setStatus("Preparing photo...");
      var blob;
      try { blob = await shrink(file); }
      catch (e) { setStatus("Could not read that photo. Try a JPEG or PNG.", true); send.disabled = false; return; }

      setStatus("Uploading...");
      var path = uuid() + ".jpg";
      var up = await fetch(BASE + "/storage/v1/object/" + BUCKET + "/" + path, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "image/jpeg", "x-upsert": "false" }),
        body: blob,
      });
      if (!up.ok) throw new Error("upload " + up.status);

      var time = f.time.value.length === 5 ? f.time.value + ":00" : f.time.value;
      var row = {
        stop_id: current.stopId,
        photo_path: path,
        taken_date: f.date.value,
        taken_time: time,
        time_bucket: bucketFor(time),
        note: f.note.value.trim() || null,
      };
      var ins = await fetch(BASE + "/rest/v1/stop_reports", {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json", Prefer: "return=minimal" }),
        body: JSON.stringify(row),
      });
      if (!ins.ok) throw new Error("insert " + ins.status);

      try { localStorage.setItem("shademap_last_report", String(Date.now())); } catch (e) { /* ignore */ }
      f.reset();
      f.date.value = today();
      f.time.value = nowHHMM();
      setStatus("Thank you. Your photo was sent and will appear after it is reviewed.");
      send.textContent = "Send another";
      send.disabled = false;
    } catch (e) {
      if (window.console) console.error(e);
      setStatus("Could not send the photo. Check your connection and try again.", true);
      send.disabled = false;
    }
  }

  // approved photos shown in popups ------------------------------------------------
  async function loadApproved() {
    if (approved) return approved;
    try {
      var r = await fetch(
        BASE + "/rest/v1/stop_reports?approved=eq.true" +
          "&select=stop_id,photo_path,taken_date,taken_time,time_bucket,note&order=created_at.desc&limit=1000",
        { headers: authHeaders() }
      );
      if (!r.ok) throw new Error("load " + r.status);
      var rows = await r.json();
      var by = {};
      rows.forEach(function (x) { (by[x.stop_id] = by[x.stop_id] || []).push(x); });
      approved = by;
    } catch (e) {
      return {}; // leave approved null so the next popup tries again
    }
    return approved;
  }

  async function fillGallery(box, popup) {
    var by = await loadApproved();
    var rows = (by[box.getAttribute("data-stop")] || []).filter(function (x) { return PATH_OK.test(x.photo_path); });
    if (!rows.length) return;
    box.innerHTML =
      '<div class="ugc-head">Photos from riders</div>' +
      rows.slice(0, 3).map(function (x) {
        return (
          '<figure class="ugc-item"><img loading="lazy" alt="Photo of this stop submitted by a rider" src="' +
          esc(BASE + "/storage/v1/object/public/" + BUCKET + "/" + x.photo_path) + '">' +
          "<figcaption>Taken " + esc(fmtTime(x.taken_time)) + " on " + esc(fmtDate(x.taken_date)) +
          " (" + esc(x.time_bucket) + ")" + (x.note ? ": " + esc(x.note) : "") + "</figcaption></figure>"
        );
      }).join("");
    // The popup grows again when each photo finishes loading. update() re-measures it and
    // re-runs Leaflet's auto-pan, which keeps it clear of the title bar (padding set in make_map.py).
    popup.update();
    Array.prototype.forEach.call(box.querySelectorAll("img"), function (img) {
      img.addEventListener("load", function () { popup.update(); });
    });
  }

  // entry point, called once from the map page ------------------------------------
  window.shademapInit = function (map) {
    if (!ENABLED) return; // buttons stay hidden, the map is unchanged
    document.documentElement.classList.add("reports-on");
    map.on("popupopen", function (e) {
      var el = e.popup.getElement();
      if (!el) return;
      var btn = el.querySelector(".report-btn");
      if (btn) btn.addEventListener("click", function () { openModal(btn.getAttribute("data-stop"), btn.getAttribute("data-name")); });
      var box = el.querySelector(".ugc");
      if (box) fillGallery(box, e.popup);
    });
  };
})();
