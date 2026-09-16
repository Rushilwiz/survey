// Projector counter: poll /count every second and update the big number.
// Class size is optional and only affects the denominator.
(function () {
  var countEl = document.getElementById("count");
  var denomEl = document.getElementById("denom");
  var csEl = document.getElementById("class-size");
  var setup = document.getElementById("setup");
  var editBtn = document.getElementById("edit-size");
  var csForm = document.getElementById("class-size-form");
  var current = parseInt(countEl.textContent, 10) || 0;

  function showDenom(size) {
    if (size) {
      csEl.textContent = size;
      denomEl.classList.remove("hidden");
      editBtn.classList.remove("hidden");
    } else {
      denomEl.classList.add("hidden");
      editBtn.classList.add("hidden");
    }
  }

  function apply(data) {
    if (typeof data.count === "number" && data.count !== current) {
      current = data.count;
      countEl.textContent = current;
      countEl.classList.remove("bump");
      void countEl.offsetWidth; // restart animation
      countEl.classList.add("bump");
    }
    showDenom(data.class_size);
  }

  function poll() {
    fetch("/count", { headers: { "Accept": "application/json" } })
      .then(function (r) { return r.json(); })
      .then(apply)
      .catch(function () {});
  }

  csForm.addEventListener("submit", function (e) {
    e.preventDefault();
    var body = new URLSearchParams(new FormData(csForm));
    fetch("/class_size", { method: "POST", body: body })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        apply(data);
        setup.classList.add("hidden");
      })
      .catch(function () {});
  });

  editBtn.addEventListener("click", function () {
    setup.classList.remove("hidden");
    var inp = document.getElementById("cs-input");
    if (inp) inp.focus();
  });

  setInterval(poll, 1000);
  poll();
})();
