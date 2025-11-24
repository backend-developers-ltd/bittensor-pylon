local g = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';
local var = g.dashboard.variable;

local prometheusQuery = g.query.prometheus;
local timeSeries = g.panel.timeSeries;

// Dashboard variables
local datasourceVar = var.datasource.new('datasource', 'prometheus')
  + var.datasource.generalOptions.withLabel('Prometheus');

local variables = [
  datasourceVar,

  var.query.new('path')
  + var.query.withDatasourceFromVariable(datasourceVar)
  + var.query.queryTypes.withLabelValues('path', 'pylon_requests_total')
  + var.query.generalOptions.withLabel('HTTP path')
  + var.query.selectionOptions.withIncludeAll(true, '.*')
  + var.query.selectionOptions.withMulti(true),
];

// Panels
local panels = [
  // Request Rate by Status
  timeSeries.new('Request Rate by Status')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum by (status_code) (rate(pylon_requests_total{path=~"$path"}[5m]))'
    )
    + prometheusQuery.withLegendFormat('{{status_code}}'),
  ])
  + timeSeries.standardOptions.withUnit('reqps'),

  // Request Latency (p50)
  timeSeries.new('Request Latency (p50)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.5, sum by (le) (rate(pylon_request_duration_seconds_bucket{path=~"$path"}[5m])))'
    )
    + prometheusQuery.withLegendFormat('p50'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Request Latency (p95)
  timeSeries.new('Request Latency (p95)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.95, sum by (le) (rate(pylon_request_duration_seconds_bucket{path=~"$path"}[5m])))'
    )
    + prometheusQuery.withLegendFormat('p95'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // In-Flight Requests
  timeSeries.new('In-Flight Requests')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum by (path) (pylon_requests_in_progress{path=~"$path"})'
    )
    + prometheusQuery.withLegendFormat('{{path}}'),
  ]),
];

// Dashboard
g.dashboard.new('Pylon HTTP Operations')
+ g.dashboard.withUid('pylon-http')
+ g.dashboard.withTags(['pylon', 'http'])
+ g.dashboard.withEditable(true)
+ g.dashboard.withRefresh('30s')
+ g.dashboard.time.withFrom('now-6h')
+ g.dashboard.time.withTo('now')
+ g.dashboard.withVariables(variables)
+ g.dashboard.withPanels(
  g.util.grid.makeGrid(panels, panelWidth=12, panelHeight=8)
)
