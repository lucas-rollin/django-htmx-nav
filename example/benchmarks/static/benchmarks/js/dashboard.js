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

  const IDENTIFIER_LABELS = { variant_label: 'Variant', family_label: 'Family', axis: 'Axis' };
  const BASE_FAMILY_ORDER = [
    'mpa',
    'vanilla_htmx_unaware_views',
    'vanilla_htmx_composite',
    'vanilla_htmx_atomic',
    'htmx_nav_baseline',
    'htmx_nav_composite',
    'htmx_nav_declarative',
    'htmx_nav_atomic',
  ];

  /**
   * Register the main `metricDashboard` component in Alpine.js.
   *
   * @param {string} chartDataId - DOM ID of the JSON `<script>` element containing chart series data.
   * @param {string} tableDataId - DOM ID of the JSON `<script>` element containing tabular rows and columns.
   * @param {string} descriptionsDataId - DOM ID of the JSON `<script>` element containing metric descriptions and metadata.
   * @param {string} [scenariosDataId] - Optional DOM ID of the JSON `<script>` element containing scenario breakdown views.
   */
  Alpine.data('metricDashboard', (chartDataId, tableDataId, descriptionsDataId, scenariosDataId) => ({
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
    _comparisonChart: null,
    _onThemeChange: null,

    // Scenario support
    scenarios: null,
    scenarioList: [],
    currentScenario: 'all',
    comparisonMetric: null,
    comparisonScope: 'base',

    _scatterPalette: [],
    _rankedPalette: [],
    _comparisonPalette: [],

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
      this.comparisonMetric = this.metrics[0] || null;

      if (scenariosDataId) {
        const scEl = document.getElementById(scenariosDataId);
        if (scEl && scEl.textContent && scEl.textContent.trim() !== 'null') {
          try {
            this.scenarios = JSON.parse(scEl.textContent);
            if (this.scenarios) {
              this.scenarioList = Object.values(this.scenarios).map((s) => ({
                key: s.key,
                label: s.label,
              }));
            }
          } catch (e) {
            console.error('Failed parsing scenarios data:', e);
          }
        }
      }

      this._initPalettes();
      this._onThemeChange = (themeName) => this.rebuildCharts(themeName);

      this.$nextTick(() => {
        if (!this.metrics.length) return;
        this.rebuildCharts(chartTheme.themeName());
        chartTheme.onChange(this._onThemeChange);
      });
    },

    _initPalettes() {
      const cursor = chartTheme.createPaletteCursor();
      // Scatter chart: up to 8 families
      this._scatterPalette = cursor.nextPalette(8);
      // Ranked chart: up to 4 axis stacks
      this._rankedPalette = cursor.nextPalette(4);
      // Comparison chart: 3 swap scenarios
      this._comparisonPalette = cursor.nextPalette(3);
    },

    destroy() {
      if (this._onThemeChange) chartTheme.offChange(this._onThemeChange);
      if (this._scatterChart) {
        chartRegistry.delete(this._scatterChart);
        this._scatterChart.dispose();
      }
      if (this._rankedChart) {
        chartRegistry.delete(this._rankedChart);
        this._rankedChart.dispose();
      }
      if (this._comparisonChart) {
        chartRegistry.delete(this._comparisonChart);
        this._comparisonChart.dispose();
      }
    },

    get hasScenarioComparison() {
      return Boolean(this.scenarioList && this.scenarioList.length > 1);
    },

    get currentScenarioLabel() {
      const sc = this.scenarioList.find((s) => s.key === this.currentScenario);
      return sc ? sc.label : 'All Scenarios (Average)';
    },

    setScenario(key) {
      if (!this.scenarios || !this.scenarios[key]) return;
      this.currentScenario = key;
      this._chartData = this.scenarios[key].charts;
      this.rows = this.scenarios[key].table.rows;
      this.columns = this.scenarios[key].table.columns;
      this.columnRanges = this._computeRanges();
      this.renderScatter();
      this.renderRanked();
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
      this._initPalettes();
      if (this._scatterChart) {
        chartRegistry.delete(this._scatterChart);
        this._scatterChart.dispose();
      }
      if (this._rankedChart) {
        chartRegistry.delete(this._rankedChart);
        this._rankedChart.dispose();
      }
      if (this._comparisonChart) {
        chartRegistry.delete(this._comparisonChart);
        this._comparisonChart.dispose();
      }
      this._scatterChart = echarts.init(this.$refs.scatterEl, themeName, { renderer: 'canvas' });
      this._rankedChart = echarts.init(this.$refs.rankedEl, themeName, { renderer: 'canvas' });
      chartRegistry.add(this._scatterChart);
      chartRegistry.add(this._rankedChart);
      if (this.$refs.comparisonEl && this.hasScenarioComparison) {
        this._comparisonChart = echarts.init(this.$refs.comparisonEl, themeName, { renderer: 'canvas' });
        chartRegistry.add(this._comparisonChart);
      }
      this.renderScatter();
      this.renderRanked();
      if (this.hasScenarioComparison) {
        this.renderComparison();
      }
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
        color: this._scatterPalette,
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
        color: this._rankedPalette,
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

    renderComparison() {
      if (!this._comparisonChart || !this.hasScenarioComparison || !this.comparisonMetric) return;

      const compScenarios = this.scenarioList.filter((s) => s.key !== 'all');
      if (!compScenarios.length) return;

      let targetRows = this.scenarios && this.scenarios.all ? this.scenarios.all.table.rows : this.rows;
      if (this.comparisonScope === 'base') {
        targetRows = targetRows.filter((r) => r.axis === 'base');
        targetRows.sort((a, b) => {
          const idxA = BASE_FAMILY_ORDER.indexOf(a.variant);
          const idxB = BASE_FAMILY_ORDER.indexOf(b.variant);
          return (idxA === -1 ? 999 : idxA) - (idxB === -1 ? 999 : idxB);
        });
      } else {
        targetRows = [...targetRows].sort((a, b) => a.variant_label.localeCompare(b.variant_label));
      }

      const labels = targetRows.map((r) => r.variant_label);
      const metricInfo = this.descriptions[this.comparisonMetric] || {};
      const unit = metricInfo.unit || 'bytes';

      const series = compScenarios.map((sc) => {
        const scData = this.scenarios[sc.key]?.charts[this.comparisonMetric];
        const data = targetRows.map((r) => {
          if (!scData) return null;
          const idx = scData.labels.indexOf(r.variant);
          return idx !== -1 ? scData.values[idx] : null;
        });
        return {
          name: sc.label,
          type: 'bar',
          data,
        };
      });

      const option = {
        color: this._comparisonPalette,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params) => {
            if (!params || !params.length) return '';
            let res = `<div class="font-bold text-xs mb-1">${params[0].axisValue}</div>`;
            params.forEach((p) => {
              const val = typeof p.value === 'number'
                ? (Number.isInteger(p.value) ? p.value : p.value.toFixed(1))
                : (p.value ?? '–');
              res += `<div class="flex items-center justify-between gap-4 text-xs">
                <span>${p.marker} ${p.seriesName}</span>
                <span class="font-mono font-semibold">${val} ${unit}</span>
              </div>`;
            });
            return res;
          },
        },
        legend: {
          type: 'scroll',
          top: 0,
          textStyle: { fontSize: 11 },
        },
        grid: {
          left: 64,
          right: 24,
          top: 36,
          bottom: this.comparisonScope === 'all' ? 76 : 56,
        },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: {
            fontSize: 10,
            rotate: this.comparisonScope === 'all' ? 35 : 20,
            interval: 0,
          },
        },
        yAxis: {
          type: 'value',
          name: unit,
          nameLocation: 'middle',
          nameGap: 48,
        },
        series,
      };

      if (this.comparisonScope === 'all') {
        option.dataZoom = [
          { type: 'inside' },
          { type: 'slider', bottom: 6, height: 18, textStyle: { fontSize: 10 } },
        ];
      }

      this._comparisonChart.setOption(option, true);
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