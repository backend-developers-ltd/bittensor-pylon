local g = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';
local var = g.dashboard.variable;

local prometheusQuery = g.query.prometheus;
local timeSeries = g.panel.timeSeries;

// Dashboard variables
local datasourceVar = var.datasource.new('datasource', 'prometheus')
  + var.datasource.generalOptions.withLabel('Prometheus');

local variables = [
  datasourceVar,

  var.query.new('netuid')
  + var.query.withDatasourceFromVariable(datasourceVar)
  + var.query.queryTypes.withLabelValues('netuid', 'pylon_bittensor_operation_duration_seconds_bucket')
  + var.query.generalOptions.withLabel('netuid')
  + var.query.selectionOptions.withIncludeAll(true, '.*')
  + var.query.selectionOptions.withMulti(true),

  var.query.new('hotkey')
  + var.query.withDatasourceFromVariable(datasourceVar)
  + var.query.queryTypes.withLabelValues('hotkey', 'pylon_bittensor_operation_duration_seconds_bucket')
  + var.query.generalOptions.withLabel('hotkey')
  + var.query.selectionOptions.withIncludeAll(true, '.*')
  + var.query.selectionOptions.withMulti(true),

  var.query.new('uri')
  + var.query.withDatasourceFromVariable(datasourceVar)
  + var.query.queryTypes.withLabelValues('uri', 'pylon_bittensor_operation_duration_seconds_bucket')
  + var.query.generalOptions.withLabel('BT URI')
  + var.query.selectionOptions.withIncludeAll(true, '.*')
  + var.query.selectionOptions.withMulti(true),
];

// Panels
local panels = [
  // Operation Latency (p50)
  timeSeries.new('Operation Latency (p50)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.5, sum by (operation, le) (rate(pylon_bittensor_operation_duration_seconds_bucket{uri=~"$uri"}[5m])))'
    )
    + prometheusQuery.withLegendFormat('{{operation}}'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Operation Latency (p95)
  timeSeries.new('Operation Latency (p95)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.95, sum by (operation, le) (rate(pylon_bittensor_operation_duration_seconds_bucket{uri=~"$uri"}[5m])))'
    )
    + prometheusQuery.withLegendFormat('{{operation}}'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Operation Errors
  timeSeries.new('Operation Errors')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum by (operation) (rate(pylon_bittensor_operation_duration_seconds_count{status="error", uri=~"$uri"}[5m]))'
    )
    + prometheusQuery.withLegendFormat('{{operation}}'),
  ])
  + timeSeries.standardOptions.withUnit('ops'),

  // Archive Fallbacks
  timeSeries.new('Archive Fallbacks')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum by (reason, operation) (rate(pylon_bittensor_fallback_total{hotkey=~"$hotkey"}[15m]))'
    )
    + prometheusQuery.withLegendFormat('{{operation}} {{reason}}'),
  ])
  + timeSeries.standardOptions.withUnit('ops'),

  // Apply Weights: Job Duration (p50)
  timeSeries.new('Apply Weights: Job Duration (p50)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.5, sum by (job_status, le) (rate(pylon_apply_weights_job_duration_seconds_bucket{netuid=~"$netuid", hotkey=~"$hotkey"}[15m])))'
    )
    + prometheusQuery.withLegendFormat('{{job_status}}'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Apply Weights: Job Duration (p95)
  timeSeries.new('Apply Weights: Job Duration (p95)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.95, sum by (job_status, le) (rate(pylon_apply_weights_job_duration_seconds_bucket{netuid=~"$netuid", hotkey=~"$hotkey"}[15m])))'
    )
    + prometheusQuery.withLegendFormat('{{job_status}}'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Apply Weights: Attempt Duration (p50)
  timeSeries.new('Apply Weights: Attempt Duration (p50)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.5, sum by (status, le) (rate(pylon_apply_weights_attempt_duration_seconds_bucket{netuid=~"$netuid", hotkey=~"$hotkey"}[15m])))'
    )
    + prometheusQuery.withLegendFormat('{{status}}'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Apply Weights: Attempt Duration (p95)
  timeSeries.new('Apply Weights: Attempt Duration (p95)')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'histogram_quantile(0.95, sum by (status, le) (rate(pylon_apply_weights_attempt_duration_seconds_bucket{netuid=~"$netuid", hotkey=~"$hotkey"}[15m])))'
    )
    + prometheusQuery.withLegendFormat('{{status}}'),
  ])
  + timeSeries.standardOptions.withUnit('s'),

  // Apply Weights: Errors
  timeSeries.new('Apply Weights: Errors')
  + timeSeries.queryOptions.withTargets([
    prometheusQuery.new(
      '$datasource',
      'sum(rate(pylon_apply_weights_attempt_duration_seconds_count{status="error", netuid=~"$netuid", hotkey=~"$hotkey"}[15m]))'
    )
    + prometheusQuery.withLegendFormat('errors'),
  ])
  + timeSeries.standardOptions.withUnit('ops'),
];

// Dashboard
g.dashboard.new('Pylon Bittensor Operations')
+ g.dashboard.withUid('pylon-bittensor')
+ g.dashboard.withTags(['pylon', 'bittensor'])
+ g.dashboard.withEditable(true)
+ g.dashboard.withRefresh('30s')
+ g.dashboard.time.withFrom('now-6h')
+ g.dashboard.time.withTo('now')
+ g.dashboard.withVariables(variables)
+ g.dashboard.withPanels(
  g.util.grid.makeGrid(panels, panelWidth=12, panelHeight=8)
)
