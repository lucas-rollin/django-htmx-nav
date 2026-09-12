/**
 * Tracks daisyUI's light/dark toggle and exposes it as a plain boolean,
 * for ECharts to select its own built-in 'dark' theme vs. its default theme.
 * Also provides unified color palettes and a stateful palette cursor to ensure
 * all charts on a page cycle through the entire palette without duplicate colors.
 */
(function (global) {
  const listeners = new Set();

  // Official ECharts default palettes (9 colors each)
  const LIGHT_PALETTE = [
    '#5470c6',
    '#91cc75',
    '#fac858',
    '#ee6666',
    '#73c0de',
    '#3ba272',
    '#fc8452',
    '#9a60b4',
    '#ea7ccc',
  ];
  const DARK_PALETTE = [
    '#4992ff',
    '#7cffb2',
    '#fddd60',
    '#ff6e76',
    '#58d9f9',
    '#05c091',
    '#ff8a45',
    '#8d48e3',
    '#dd79ff',
  ];

  function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  function themeName() {
    return isDark() ? 'dark' : null; // null = ECharts' default light theme
  }

  function palette() {
    return isDark() ? [...DARK_PALETTE] : [...LIGHT_PALETTE];
  }

  /**
   * Factory for creating a stateful palette cursor.
   * Advances sequentially so each chart or series gets the next available color(s),
   * only wrapping around after exploring the complete palette.
   */
  function createPaletteCursor() {
    let cursor = 0;
    return {
      get cursor() {
        return cursor;
      },
      set cursor(val) {
        cursor = val;
      },
      reset() {
        cursor = 0;
      },
      /**
       * Returns a full rotated palette starting at the current cursor position,
       * then advances the cursor by `seriesCount`.
       * Useful for setting `option.color` on an ECharts instance.
       */
      nextPalette(seriesCount = 1) {
        const base = palette();
        const offset = cursor % base.length;
        cursor += seriesCount;
        return [...base.slice(offset), ...base.slice(0, offset)];
      },
      /**
       * Returns an array of exactly `count` colors, advancing the cursor.
       */
      nextColors(count = 1) {
        const base = palette();
        const colors = [];
        for (let i = 0; i < count; i++) {
          colors.push(base[(cursor + i) % base.length]);
        }
        cursor += count;
        return colors;
      },
    };
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

  global.chartTheme = {
    themeName,
    isDark,
    onChange,
    offChange,
    palette,
    createPaletteCursor,
    LIGHT_PALETTE,
    DARK_PALETTE,
  };
})(window);