// Typeform-style step-through for the survey. Renders one question at a time,
// advances on selection for single-choice, enforces the mutually-exclusive
// "Prefer not to answer" on the multi-select. If this script fails to load,
// all steps are simply shown (see noscript) and the form still POSTs normally.
(function () {
  var form = document.getElementById("survey-form");
  if (!form) return;
  var steps = Array.prototype.slice.call(form.querySelectorAll(".step"));
  var backBtn = document.getElementById("back");
  var nextBtn = document.getElementById("next");
  var submitBtn = document.getElementById("submit");
  var fill = document.getElementById("progress-fill");
  var ptext = document.getElementById("progress-text");
  var i = 0;

  function render() {
    steps.forEach(function (s, idx) { s.hidden = idx !== i; });
    var isLast = i === steps.length - 1;
    backBtn.hidden = i === 0;
    nextBtn.hidden = isLast;
    submitBtn.hidden = !isLast;
    var pct = Math.round(((i + 1) / steps.length) * 100);
    fill.style.width = pct + "%";
    ptext.textContent = (i + 1) + " / " + steps.length;
    var focusable = steps[i].querySelector("input, textarea");
    if (focusable) { try { focusable.focus({ preventScroll: true }); } catch (e) {} }
  }

  function go(n) {
    i = Math.max(0, Math.min(steps.length - 1, n));
    render();
  }

  nextBtn.addEventListener("click", function () { go(i + 1); });
  backBtn.addEventListener("click", function () { go(i - 1); });

  steps.forEach(function (step) {
    var multi = step.dataset.multi === "1";
    step.addEventListener("change", function (e) {
      var input = e.target;
      if (input.type === "radio") {
        // Advance shortly after a single-choice pick.
        setTimeout(function () { go(i + 1); }, 180);
      } else if (input.type === "checkbox" && multi) {
        var boxes = step.querySelectorAll('input[type="checkbox"]');
        var pna = step.querySelector('.option.pna input');
        if (input === pna && input.checked) {
          boxes.forEach(function (b) { if (b !== pna) b.checked = false; });
        } else if (input !== pna && input.checked && pna) {
          pna.checked = false;
        }
      }
    });
  });

  // Keyboard: Enter advances (except inside the comments textarea).
  form.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
      if (!submitBtn.hidden) return; // let Enter submit on the last step
      e.preventDefault();
      go(i + 1);
    }
  });

  render();
})();
