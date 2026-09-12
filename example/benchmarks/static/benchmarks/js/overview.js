/**
 * @fileoverview Fixed, hand-picked ECharts panels for the benchmarks
 * overview page.
 */

document.addEventListener('alpine:init', () => {
  const chartRegistry = new Set();

  // Official ECharts default palettes
  const LIGHT_PALETTE = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'];
  const DARK_PALETTE = ['#4992ff', '#7cffb2', '#fddd60', '#ff6e76', '#58d9f9', '#f05b72', '#24cbe5', '#61a0a8', '#efa18d'];

  window.addEventListener('resize', () => {
    chartRegistry.forEach((chart) => {
      if (!chart.isDisposed()) chart.resize();
    });
  });

  document.body.addEventListener('htmx:beforeCleanupElement', (evt) => {
    const root = evt.target;
    if (!root.querySelectorAll) return;
    [root, ...root.querySelectorAll('*')].forEach((el) => {
      const instance = echarts.getInstanceByDom?.(el);
      if (instance) {
        chartRegistry.delete(instance);
        instance.dispose();
      }
    });
  });

  Alpine.data('overviewDashboard', (panelsDataId) => ({
    panels: [],
    _instances: [], // [{ el, chart, panel, index }]
    _onThemeChange: null,

    init() {
      this.panels = JSON.parse(document.getElementById(panelsDataId).textContent);
      this._onThemeChange = (themeName) => this._rebuildAll(themeName);
      this.$nextTick(() => {
        chartTheme.onChange(this._onThemeChange);
      });
    },

    destroy() {
      if (this._onThemeChange) chartTheme.offChange(this._onThemeChange);
    },

    /** Called via x-init="mount($el, panel, index)" on each panel's chart div. */
    mount(el, panel, index = 0) {
      const chart = echarts.init(el, chartTheme.themeName(), { renderer: 'canvas' });
      chartRegistry.add(chart);
      this._instances.push({ el, chart, panel, index });
      
      chart.setOption(this._optionFor(panel, index));

      requestAnimationFrame(() => {
        if (!chart.isDisposed()) chart.resize();
      });
    },

    _rebuildAll(themeName) {
      for (const entry of this._instances) {
        if (!entry.chart.isDisposed()) {
          chartRegistry.delete(entry.chart);
          entry.chart.dispose();
        }
        entry.chart = echarts.init(entry.el, themeName, { renderer: 'canvas' });
        chartRegistry.add(entry.chart);
        
        entry.chart.setOption(this._optionFor(entry.panel, entry.index));

        requestAnimationFrame(() => {
          if (!entry.chart.isDisposed()) entry.chart.resize();
        });
      }
    },

    _optionFor(panel, index) {
      const c = panel.chart;
      let baseOption;
      if (c.type === 'scatter') baseOption = this._scatterOption(c);
      else if (c.type === 'bar_line') baseOption = this._barLineOption(c);
      else baseOption = this._barOption(c);

      // Select the palette based on the current theme mode
      const basePalette = chartTheme.isDark() ? DARK_PALETTE : LIGHT_PALETTE;
      
      // Rotate the palette so each chart gets a unique starting color sequence
      const offset = index % basePalette.length;
      const rotatedPalette = [...basePalette.slice(offset), ...basePalette.slice(0, offset)];

      return { ...baseOption, color: rotatedPalette };
    },

    _barOption(c) {
      return {
        grid: { left: 48, right: 16, top: 16, bottom: 64 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: c.labels, axisLabel: { fontSize: 10, rotate: 20 } },
        yAxis: { type: 'value', name: c.y_name, nameLocation: 'middle', nameGap: 40 },
        series: [{ type: 'bar', data: c.values }],
      };
    },

    _scatterOption(c) {
      return {
        grid: { left: 56, right: 24, top: 24, bottom: 40 },
        tooltip: {
          trigger: 'item',
          formatter: (p) =>
            `${p.data.name}<br/>${c.x_name}: ${p.data.value[0]}<br/>${c.y_name}: ${p.data.value[1]}`,
        },
        xAxis: { type: 'value', name: c.x_name, nameLocation: 'middle', nameGap: 28 },
        yAxis: { type: 'value', name: c.y_name, nameLocation: 'middle', nameGap: 40 },
        series: [{ type: 'scatter', symbolSize: 14, data: c.points }],
      };
    },

    _barLineOption(c) {
      return {
        grid: { left: 48, right: 48, top: 24, bottom: 64 },
        tooltip: { trigger: 'axis' },
        legend: { bottom: 0, textStyle: { fontSize: 10 } },
        xAxis: { type: 'category', data: c.labels, axisLabel: { fontSize: 10, rotate: 20 } },
        yAxis: [
          { type: 'value', name: c.bar_name, nameLocation: 'middle', nameGap: 36 },
          { type: 'value', name: c.line_name, nameLocation: 'middle', nameGap: 36 },
        ],
        series: [
          { type: 'bar', name: c.bar_name, data: c.bar_values, yAxisIndex: 0 },
          {
            type: 'line',
            name: c.line_name,
            data: c.line_values,
            yAxisIndex: 1,
            smooth: false,
          },
        ],
      };
    },
  }));
});