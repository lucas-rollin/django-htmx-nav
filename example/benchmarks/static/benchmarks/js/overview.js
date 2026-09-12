/**
 * @fileoverview Fixed, hand-picked ECharts panels for the benchmarks
 * overview page.
 */

document.addEventListener('alpine:init', () => {
  const chartRegistry = new Set();

  window.addEventListener('resize', () => {
    chartRegistry.forEach((chart) => {
      if (!chart.isDisposed()) chart.resize();
    });
  });

  ['htmx:beforeCleanupElement', 'htmx:before:cleanup'].forEach((evtName) => {
    document.body.addEventListener(evtName, (evt) => {
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
  });

  Alpine.data('overviewDashboard', (panelsDataId) => ({
    panels: [],
    _instances: [], // [{ el, chart, panel, index }]
    _panelPalettes: [],
    _onThemeChange: null,

    init() {
      this.panels = JSON.parse(document.getElementById(panelsDataId).textContent);
      this._computePanelPalettes();
      this._onThemeChange = (themeName) => this._rebuildAll(themeName);
      this.$nextTick(() => {
        chartTheme.onChange(this._onThemeChange);
      });
    },

    destroy() {
      if (this._onThemeChange) chartTheme.offChange(this._onThemeChange);
    },

    _seriesCountFor(c) {
      if (!c) return 1;
      if (c.type === 'grouped_bar' || c.series) return c.series ? c.series.length : 1;
      if (c.type === 'bar_line') return 2;
      return 1;
    },

    _computePanelPalettes() {
      const cursor = chartTheme.createPaletteCursor();
      this._panelPalettes = this.panels.map((p) => {
        const seriesCount = this._seriesCountFor(p.chart);
        return cursor.nextPalette(seriesCount);
      });
    },

    /** Called via x-init="mount($el, panel, index)" on each panel's chart div. */
    mount(el, panel, index = 0) {
      const chart = echarts.init(el, chartTheme.themeName(), { renderer: 'canvas' });
      chartRegistry.add(chart);
      this._instances.push({ el, chart, panel, index });

      const palette = (this._panelPalettes && this._panelPalettes[index]) || chartTheme.palette();
      chart.setOption({ ...this._optionFor(panel), color: palette });

      requestAnimationFrame(() => {
        if (!chart.isDisposed()) chart.resize();
      });
    },

    _rebuildAll(themeName) {
      this._computePanelPalettes();
      for (const entry of this._instances) {
        if (!entry.chart.isDisposed()) {
          chartRegistry.delete(entry.chart);
          entry.chart.dispose();
        }
        entry.chart = echarts.init(entry.el, themeName, { renderer: 'canvas' });
        chartRegistry.add(entry.chart);

        const palette = (this._panelPalettes && this._panelPalettes[entry.index]) || chartTheme.palette();
        entry.chart.setOption({ ...this._optionFor(entry.panel), color: palette });

        requestAnimationFrame(() => {
          if (!entry.chart.isDisposed()) entry.chart.resize();
        });
      }
    },

    _optionFor(panel) {
      const c = panel.chart;
      if (c.type === 'scatter') return this._scatterOption(c);
      if (c.type === 'bar_line') return this._barLineOption(c);
      if (c.type === 'grouped_bar' || c.series) return this._groupedBarOption(c);
      return this._barOption(c);
    },

    _groupedBarOption(c) {
      return {
        grid: { left: 52, right: 16, top: 32, bottom: 64 },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params) => {
            if (!params || !params.length) return '';
            let res = `<div class="font-bold text-xs mb-1">${params[0].axisValue}</div>`;
            params.forEach((p) => {
              if (p.value === null || p.value === undefined) return;
              const val = typeof p.value === 'number'
                ? (Number.isInteger(p.value) ? p.value : p.value.toFixed(1))
                : p.value;
              res += `<div class="flex items-center justify-between gap-4 text-xs">
                <span>${p.marker} ${p.seriesName}</span>
                <span class="font-mono font-semibold">${val} ${c.y_name || ''}</span>
              </div>`;
            });
            return res;
          },
        },
        legend: { type: 'scroll', top: 0, textStyle: { fontSize: 10 } },
        xAxis: { type: 'category', data: c.labels, axisLabel: { fontSize: 10, rotate: 20 } },
        yAxis: { type: 'value', name: c.y_name, nameLocation: 'middle', nameGap: 40 },
        series: c.series.map((s) => ({
          type: 'bar',
          name: s.name,
          data: s.data,
          stack: s.stack,
          emphasis: { focus: 'series' },
        })),
      };
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
        grid: { left: 52, right: 48, top: 32, bottom: 64 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { type: 'scroll', top: 0, textStyle: { fontSize: 10 } },
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