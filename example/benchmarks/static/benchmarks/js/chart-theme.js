/**
 * Tracks daisyUI's light/dark toggle and exposes it as a plain boolean,
 * for ECharts to select its own built-in 'dark' theme vs. its default theme.
 */
(function (global) {
  const listeners = new Set();

  function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  function themeName() {
    return isDark() ? 'dark' : null; // null = ECharts' default light theme
  }

  function onChange(callback) {
    listeners.add(callback);
  }

  function offChange(callback) {
    listeners.delete(callback);
  }

  function notify() {
    const name = themeName();
    listeners.forEach((cb) => cb(name));
  }

  new MutationObserver((mutations) => {
    if (mutations.some((m) => m.attributeName === 'data-theme')) notify();
  }).observe(document.documentElement, { attributes: true });

  global.chartTheme = { themeName, isDark, onChange, offChange };
})(window);