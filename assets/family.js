(() => {
  "use strict";

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!reduce && "IntersectionObserver" in window) {
    const targets = new Set([
      ...document.querySelectorAll("main > section, main > article, main > .grid > *, main > .card"),
    ]);
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add("in");
        observer.unobserve(entry.target);
      }
    }, { rootMargin: "0px 0px -8% 0px", threshold: .08 });
    for (const target of targets) {
      target.classList.add("reveal");
      observer.observe(target);
    }
  }

  const fallbackCopy = (text) => {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
    area.remove();
    return ok;
  };

  for (const pre of document.querySelectorAll("pre")) {
    const command = pre.textContent.trim();
    if (!command) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-command";
    button.textContent = "COPY";
    button.setAttribute("aria-label", "Copy command");
    button.addEventListener("click", () => {
      const finish = (ok) => {
        button.textContent = ok ? "COPIED" : "SELECT";
        window.setTimeout(() => { button.textContent = "COPY"; }, 1400);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(command).then(() => finish(true), () => finish(fallbackCopy(command)));
      } else {
        finish(fallbackCopy(command));
      }
    });
    pre.appendChild(button);
    pre.classList.add("has-copy");
  }
})();
