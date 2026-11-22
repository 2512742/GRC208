// Runs before first paint (loaded synchronously in <head>) so dark mode never flashes white.
// An external file rather than an inline script, because the CSP allows scripts from 'self' only.
(function () {
  try {
    var saved = localStorage.getItem("risktrack-theme");
    var dark = saved ? saved === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
  } catch (e) {
    /* storage blocked: fall back to the light theme */
  }
})();
