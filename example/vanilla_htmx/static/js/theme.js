/**
 * @fileoverview enforce the theme controller works and with persistence.
 */

document.addEventListener('DOMContentLoaded', () => {
  const themeController = document.querySelector('.theme-controller');
  if (!themeController) return;

  themeController.checked = document.documentElement.getAttribute('data-theme') === 'dark';

  themeController.addEventListener('change', (e) => {
    const next = e.target.checked ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  });
});