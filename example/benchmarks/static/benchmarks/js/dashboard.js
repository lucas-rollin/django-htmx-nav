/**
 * @fileoverview Alpine.js and ECharts integration for an interactive metrics dashboard.
 * Provides dynamic chart rendering (scatter and ranked bar charts), theme synchronisation,
 * automatic chart lifecycle management for HTMX and window resizing, and tabular data sorting.
 */

document.addEventListener('alpine:init', () => {
  const chartRegistry = new Set();

  /**
   * Global window resize handler. Triggers a responsive redraw on all active, non-disposed charts.
   */
  window.addEventListener('resize', () => {
    chartRegistry.forEach((chart) => {
      if (!chart.isDisposed()) chart.resize();
    });
  });

  /**
   * HTMX lifecycle event listener. Garbage collects and disposes of ECharts instances
   * attached to elements being cleaned up or removed by HTMX swaps.
   */
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

  const IDENTIFIER_LABELS = { variant_label: 'Variant', family_label: 'Family', axis: 'Axis' };

  /**
   * Register the main `metricDashboard` component in Alpine.js.
   *
   * @param {string} chartDataId - DOM ID of the JSON `<script>` element containing chart series data.
   * @param {string} tableDataId - DOM ID of the JSON `<script>` element containing tabular rows and columns.
   * @param {string} descriptionsDataId - DOM ID of the JSON `<script>` element containing metric descriptions and metadata.
   */
  Alpine.data('metricDashboard', (chartDataId, tableDataId, descriptionsDataId) => ({
    metrics: [],
    columns: [],
    rows: [],
    columnRanges: {},
    descriptions: {},
    sortKey: null,
    sortDir: 1,
    scatterX: null,
    scatterY: null,
    rankedMetric: null,
    _chartData: {},
    _scatterChart: null,
    _rankedChart: null,
    _onThemeChange: null,

    init() {
      this._chartData = JSON.parse(document.getElementById(chartDataId).textContent);
      const tableData = JSON.parse(document.getElementById(tableDataId).textContent);
      this.descriptions = JSON.parse(document.getElementById(descriptionsDataId).textContent);
      this.metrics = Object.keys(this._chartData);
      this.columns = tableData.columns;
      this.rows = tableData.rows;
      this.columnRanges = this._computeRanges();

      this.scatterX = this.metrics[0] || null;
      this.scatterY = this.metrics[1] || this.metrics[0] || null;
      this.rankedMetric = this.metrics[0] || null;

      this._onThemeChange = (themeName) => this.rebuildCharts(themeName);

      this.$nextTick(() => {
        if (!this.metrics.length) return;
        this.rebuildCharts(chartTheme.themeName());
        chartTheme.onChange(this._onThemeChange);
      });
    },

    destroy() {
      if (this._onThemeChange) chartTheme.offChange(this._onThemeChange);
    },

    hasDescription(col) {
      return Object.prototype.hasOwnProperty.call(this.descriptions, col);
    },

    labelFor(col) {
      if (IDENTIFIER_LABELS[col]) return IDENTIFIER_LABELS[col];
      const info = this.descriptions[col];
      return (info && info.label) || this.columnLabel(col);
    },

    describeFor(col) {
      const info = this.descriptions[col];
      if (!info) return '';
      const direction = info.lower_is_better === true ? ' (lower is better)'
        : info.lower_is_better === false ? ' (higher is better)' : '';
      const unit = info.unit ? ` [${info.unit}]` : '';
      return `${info.description}${direction}${unit}`;
    },

    rebuildCharts(themeName) {
      if (this._scatterChart) {
        chartRegistry.delete(this._scatterChart);
        this._scatterChart.dispose();
      }
      if (this._rankedChart) {
        chartRegistry.delete(this._rankedChart);
        this._rankedChart.dispose();
      }
      this._scatterChart = echarts.init(this.$refs.scatterEl, themeName, { renderer: 'canvas' });
      this._rankedChart = echarts.init(this.$refs.rankedEl, themeName, { renderer: 'canvas' });
      chartRegistry.add(this._scatterChart);
      chartRegistry.add(this._rankedChart);
      this.renderScatter();
      this.renderRanked();
    },

    _computeRanges() {
      const ranges = {};
      for (const col of this.columns) {
        if (!this.isNumericColumn(col)) continue;
        const values = this.rows.map((r) => r[col]).filter((v) => typeof v === 'number');
        ranges[col] = values.length
          ? { min: Math.min(...values), max: Math.max(...values) }
          : { min: 0, max: 0 };
      }
      return ranges;
    },

    isNumericColumn(col) {
      return !['variant_label', 'family_label', 'axis'].includes(col);
    },

    renderScatter() {
      if (!this._scatterChart || !this.scatterX || !this.scatterY) return;
      const xSeries = this._chartData[this.scatterX];
      const ySeries = this._chartData[this.scatterY];
      if (!xSeries || !ySeries) return;

      const byFamily = {};
      xSeries.labels.forEach((variant, i) => {
        const row = this.rows.find((r) => r.variant === variant);
        const familyLabel = row ? row.family_label : 'Unknown';
        (byFamily[familyLabel] ||= []).push({
          value: [xSeries.values[i], ySeries.values[i]],
          name: xSeries.display_labels[i],
        });
      });

    /**
     * Renders or updates the Scatter plot comparing selected `scatterX` and `scatterY` metrics grouped by family.
     */
      this._scatterChart.setOption({
        tooltip: {
          trigger: 'item',
          formatter: (p) =>
            `${p.data.name}<br/>${this.labelFor(this.scatterX)}: ${p.data.value[0]}<br/>${this.labelFor(this.scatterY)}: ${p.data.value[1]}`,
        },
        legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
        grid: { left: 56, right: 24, top: 24, bottom: 64 },
        xAxis: { type: 'value', name: this.labelFor(this.scatterX), nameLocation: 'middle', nameGap: 28 },
        yAxis: { type: 'value', name: this.labelFor(this.scatterY), nameLocation: 'middle', nameGap: 40 },
        series: Object.entries(byFamily).map(([familyLabel, data]) => ({
          name: familyLabel,
          type: 'scatter',
          symbolSize: 12,
          data,
          emphasis: { focus: 'series' },
        })),
      }, true);
    },

    /**
     * Renders or updates the horizontal stacked bar chart ranking variants for the selected `rankedMetric`.
     */
    renderRanked() {
      if (!this._rankedChart || !this.rankedMetric) return;
      const series = this._chartData[this.rankedMetric];
      if (!series) return;

      const paired = series.labels
        .map((label, i) => ({
          label,
          displayLabel: series.display_labels[i],
          value: series.values[i] ?? 0,
          axis: this._axisFor(label),
        }))
        .sort((a, b) => b.value - a.value)
        .reverse(); // ascending, since ECharts renders category axes bottom-to-top

      const axisGroups = [...new Set(paired.map((p) => p.axis))];
      const orderedDisplayLabels = paired.map((p) => p.displayLabel);

      this._rankedChart.setOption({
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        legend: { type: 'scroll', bottom: 0, textStyle: { fontSize: 10 } },
        grid: { left: 160, right: 24, top: 16, bottom: 40 },
        xAxis: { type: 'value' },
        yAxis: { type: 'category', data: orderedDisplayLabels, axisLabel: { fontSize: 10 } },
        series: axisGroups.map((axis) => ({
          name: axis,
          type: 'bar',
          stack: 'ranked',
          emphasis: { focus: 'series' },
          data: paired.map((p) => (p.axis === axis ? p.value : null)),
        })),
      }, true);
    },

    _axisFor(variant) {
      const row = this.rows.find((r) => r.variant === variant);
      return row ? row.axis : 'base';
    },

    barStyle(col, value) {
      const range = this.columnRanges[col];
      if (!range || typeof value !== 'number' || range.max === range.min) {
        return { width: '0%' };
      }
      const pct = ((value - range.min) / (range.max - range.min)) * 100;
      return { width: `${Math.max(pct, 2)}%` };
    },

    sortBy(col) {
      if (this.sortKey === col) {
        this.sortDir *= -1;
      } else {
        this.sortKey = col;
        this.sortDir = 1;
      }
    },

    sortIndicator(col) {
      if (this.sortKey !== col) return '';
      return this.sortDir === 1 ? '▲' : '▼';
    },

    columnLabel(col) {
      return col.replace(/_/g, ' ');
    },

    fmt(value) {
      if (value === null || value === undefined) return '–';
      if (typeof value === 'number') {
        return Number.isInteger(value) ? String(value) : value.toFixed(2);
      }
      return value;
    },

    /**
     * Computed getter returning the list of dataset rows sorted according to `sortKey` and `sortDir`.
     * @returns {Array} A sorted shallow copy of the table rows.
     */
    get sortedRows() {
      if (!this.sortKey) return this.rows;
      const key = this.sortKey;
      const dir = this.sortDir;
      return [...this.rows].sort((a, b) => {
        const av = a[key];
        const bv = b[key];
        if (av === null || av === undefined) return 1;
        if (bv === null || bv === undefined) return -1;
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
        return String(av).localeCompare(String(bv)) * dir;
      });
    },
  }));
});