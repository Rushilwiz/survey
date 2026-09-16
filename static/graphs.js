/* Results slideshow: one question per screen, with the room sliced three ways.
   All counts are rendered server-side into #stats-data, so paging and
   switching breakdowns never hits the network. */
(function () {
  const stats = JSON.parse(document.getElementById("stats-data").textContent);
  const el = (id) => document.getElementById(id);
  const chart = el("chart"), legend = el("legend"), dots = el("dots");

  // Deep-linkable: /graphs?token=..&view=year&q=4 opens straight on a slide.
  const params = new URLSearchParams(location.search);
  const named = stats.views.findIndex((v) => v.key === params.get("view"));
  let viewIdx = named < 0 ? 0 : named;
  let step = Math.min(
    stats.questions.length - 1,
    Math.max(0, (parseInt(params.get("q"), 10) || 1) - 1),
  );

  const pct = (n, d) => (d ? (100 * n) / d : 0);
  // One decimal, but never a trailing ".0" -- these are read at a distance.
  const fmt = (x) => String(Math.round(x * 10) / 10);

  if (!stats.total) {
    chart.innerHTML = '<p class="empty muted">No submissions yet.</p>';
    el("q-title").textContent = "Nothing to show";
    document.querySelector(".graph-nav").classList.add("hidden");
    return;
  }

  // --- chrome built once ----------------------------------------------------
  stats.views.forEach((v, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "view-btn";
    b.textContent = v.label;
    b.setAttribute("role", "tab");
    b.addEventListener("click", () => { viewIdx = i; render(); });
    el("view-toggle").appendChild(b);
  });

  stats.questions.forEach((_, i) => {
    const d = document.createElement("button");
    d.type = "button";
    d.className = "dot";
    d.setAttribute("aria-label", `Question ${i + 1}`);
    d.addEventListener("click", () => { step = i; render(); });
    dots.appendChild(d);
  });

  // --- rendering ------------------------------------------------------------
  function bar(group, gi, count, optLabel) {
    const share = pct(count, group.n);
    const wrap = document.createElement("div");
    wrap.className = "bar";
    wrap.title = `${group.label} — ${optLabel}: ${count} of ${group.n} (${fmt(share)}%)`;

    const track = document.createElement("span");
    track.className = "track";
    const fill = document.createElement("span");
    fill.className = "fill";
    fill.style.width = share + "%";
    fill.style.background = `var(--s${(gi % 8) + 1})`;
    track.appendChild(fill);

    const val = document.createElement("span");
    val.className = "val";
    val.innerHTML = `${fmt(share)}%<span class="cnt">${count}</span>`;

    wrap.append(track, val);
    return wrap;
  }

  function render() {
    const view = stats.views[viewIdx];
    const q = stats.questions[step];
    const counts = q.counts[view.key];
    const grouped = view.groups.length > 1;

    Array.from(el("view-toggle").children).forEach((b, i) =>
      b.classList.toggle("on", i === viewIdx));
    Array.from(dots.children).forEach((d, i) =>
      d.classList.toggle("on", i === step));

    el("view-n").textContent =
      `${stats.total} response${stats.total === 1 ? "" : "s"}`;
    el("q-index").textContent = `Question ${step + 1} of ${stats.questions.length}`;
    el("q-title").textContent = q.text;
    el("q-note").classList.toggle("hidden", !q.multi);
    el("prev").disabled = step === 0;
    el("next").disabled = step === stats.questions.length - 1;

    // Legend only earns its space when there is more than one series.
    legend.innerHTML = "";
    legend.classList.toggle("hidden", !grouped);
    if (grouped) {
      view.groups.forEach((g, gi) => {
        const item = document.createElement("span");
        item.className = "legend-item";
        item.innerHTML =
          `<span class="swatch" style="background:var(--s${(gi % 8) + 1})"></span>` +
          `${g.label} <span class="muted">n=${g.n}</span>`;
        legend.appendChild(item);
      });
    }

    chart.innerHTML = "";
    chart.classList.toggle("grouped", grouped);
    q.options.forEach((opt) => {
      const row = document.createElement("div");
      row.className = "row";

      const label = document.createElement("div");
      label.className = "row-label";
      label.textContent = opt.label;

      const bars = document.createElement("div");
      bars.className = "row-bars";
      view.groups.forEach((g, gi) =>
        bars.appendChild(bar(g, gi, (counts[g.key] || {})[opt.slug] || 0, opt.label)));

      row.append(label, bars);
      chart.appendChild(row);
    });
  }

  const move = (d) => {
    step = Math.min(stats.questions.length - 1, Math.max(0, step + d));
    render();
  };
  el("prev").addEventListener("click", () => move(-1));
  el("next").addEventListener("click", () => move(1));
  document.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowLeft") move(-1);
    else if (e.key >= "1" && e.key <= String(stats.views.length)) {
      viewIdx = Number(e.key) - 1;
      render();
    }
  });

  render();
})();
