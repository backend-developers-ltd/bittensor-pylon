local g = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';
local var = g.dashboard.variable;

local prometheusQuery = g.query.prometheus;
local timeSeries = g.panel.timeSeries;
local stat = g.panel.stat;

// Dashboard variables
local datasourceVar = var.datasource.new('datasource', 'prometheus')
  + var.datasource.generalOptions.withLabel('Prometheus');

local variables = [
  datasourceVar,
];

// Panels
local panels = [
  // CPU Usage
  timeSeries.new('CPU Usage')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'rate(process_cpu_seconds_total{job="pylon"}[5m])'
    )
    + prometheusQuery.withLegendFormat('CPU'),
  ])
  + timeSeries.standardOptions.withUnit('percentunit'),

  // Memory Usage (RSS)
  timeSeries.new('Memory Usage (RSS)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'process_resident_memory_bytes{job="pylon"}'
    )
    + prometheusQuery.withLegendFormat('RSS'),
  ])
  + timeSeries.standardOptions.withUnit('bytes'),

  // Memory Usage (Virtual)
  timeSeries.new('Memory Usage (Virtual)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'process_virtual_memory_bytes{job="pylon"}'
    )
    + prometheusQuery.withLegendFormat('Virtual'),
  ])
  + timeSeries.standardOptions.withUnit('bytes'),

  // File Descriptors
  timeSeries.new('File Descriptors')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'process_open_fds{job="pylon"}'
    )
    + prometheusQuery.withLegendFormat('Open'),
    prometheusQuery.new(
      '$datasource',
      'process_max_fds{job="pylon"}'
    )
    + prometheusQuery.withLegendFormat('Max'),
  ])
  + timeSeries.standardOptions.withUnit('short'),

  // Garbage Collection Rate
  timeSeries.new('Garbage Collection Rate')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum by (generation) (rate(python_gc_objects_collected_total{job="pylon"}[5m]))'
    )
    + prometheusQuery.withLegendFormat('gen{{generation}}'),
  ])
  + timeSeries.standardOptions.withUnit('ops'),

  // GC Uncollectable Objects
  timeSeries.new('GC Uncollectable Objects')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum by (generation) (rate(python_gc_objects_uncollectable_total{job="pylon"}[5m]))'
    )
    + prometheusQuery.withLegendFormat('gen{{generation}}'),
  ])
  + timeSeries.standardOptions.withUnit('ops'),

  // Uptime
  stat.new('Uptime')
  + stat.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      '(time() - process_start_time_seconds{job="pylon"})'
    ),
  ])
  + stat.standardOptions.withUnit('s'),
];

// Dashboard
g.dashboard.new('Pylon System & Runtime')
+ g.dashboard.withUid('pylon-system')
+ g.dashboard.withTags(['pylon', 'system', 'runtime'])
+ g.dashboard.withEditable(true)
+ g.dashboard.withRefresh('30s')
+ g.dashboard.time.withFrom('now-6h')
+ g.dashboard.time.withTo('now')
+ g.dashboard.withVariables(variables)
+ g.dashboard.withPanels(
  g.util.grid.makeGrid(panels, panelWidth=12, panelHeight=8)
)
