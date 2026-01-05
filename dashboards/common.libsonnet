#!/usr/bin/env -S jsonnet -J ../../vendor
local grafonnet = import '../../vendor/gen/grafonnet-v11.4.0/main.libsonnet';
local var = grafonnet.dashboard.variable;
local ts = grafonnet.panel.timeSeries;
local bc = grafonnet.panel.barChart;
local bg = grafonnet.panel.barGauge;

{
  // grafonnet ref: https://grafana.github.io/grafonnet/API/dashboard/variable.html
  variables: {
    infinity_datasource:
      var.datasource.new('infinity_datasource', 'yesoreyeram-infinity-datasource')
      + var.datasource.generalOptions.showOnDashboard.withNothing(),
    prometheus_datasource:
      var.datasource.new('prometheus_datasource',
      'prometheus')
      + var.datasource.generalOptions.showOnDashboard.withNothing(),
    hub_general:
      var.query.new(
        'hub_general',
        {
          query: '',
          queryType: 'infinity',
          infinityQuery: {
            format: 'table',
            parser: 'backend',
            refId: 'variable',
            source: 'url',
            type: 'json',
            url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/hub-names?from=${__from:date}&to=${__to:date}',
            url_options: {
              data: '',
              method: 'GET',
            },
          },
        },
      )
      + var.query.withDatasourceFromVariable(self.infinity_datasource)
      + var.query.generalOptions.withLabel('hub')
      + var.query.generalOptions.withCurrent({
        text: [
          'All',
        ],
        value: [
          '$__all',
        ],
      })
      + var.query.selectionOptions.withIncludeAll(value=true)
      + var.query.selectionOptions.withMulti(value=true)
      + var.query.refresh.onTime(),    
    hub_user:
      var.query.new(
        'hub_user',
        {
          query: '',
          queryType: 'infinity',
          infinityQuery: {
            format: 'table',
            parser: 'backend',
            refId: 'variable',
            root_selector: '$append($filter($, function($v) {$v != "support" and $v != "binder"}) , "All")',
            source: 'url',
            type: 'json',
            url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/hub-names?from=${__from:date}&to=${__to:date}',
            url_options: {
              data: '',
              method: 'GET',
            },
          },
        },
      )
      + var.query.withDatasourceFromVariable(self.infinity_datasource)
      + var.query.generalOptions.withLabel('hub')
      + var.query.generalOptions.withCurrent('All')
      + var.query.selectionOptions.withIncludeAll(value=false)
      + var.query.selectionOptions.withMulti(value=true)
      + var.query.refresh.onTime(),
    component:
      var.query.new(
        'component',
        {
          query: '',
          queryType: 'infinity',
          infinityQuery: {
            format: 'table',
            parser: 'backend',
            refId: 'variable',
            source: 'url',
            type: 'json',
            url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/component-names?from=${__from:date}&to=${__to:date}',
            url_options: {
              data: '',
              method: 'GET',
            },
          },
        },
      )
      + var.query.withDatasourceFromVariable(self.infinity_datasource)
      + var.query.generalOptions.withCurrent('All')
      + var.query.selectionOptions.withIncludeAll(value=true, customAllValue='all')
      + var.query.selectionOptions.withMulti(value=false)
      + var.query.refresh.onTime(),
    usergroup:
      var.query.new(
        'usergroup', 
        query='label_values(jupyterhub_user_group_info,usergroup)')
      + var.query.withDatasource(
        type='prometheus',
        uid='${prometheus_datasource}',
      )
      + var.query.generalOptions.withLabel('group')
      + var.query.generalOptions.withCurrent('All')
      + var.query.selectionOptions.withIncludeAll(value=true, customAllValue='all')
      + var.query.selectionOptions.withMulti(value=true)
      + var.query.refresh.onTime(),
    limit:
      var.textbox.new('limit')
      + var.textbox.generalOptions.withDescription('Limit display to top N users. Leave empty to show all.')
      + var.textbox.generalOptions.withLabel('Number of users')
  },

  // grafonnet ref: https://grafana.github.io/grafonnet/API/panel/timeSeries/index.html#obj-queryoptions
  queryDailyTarget: {
    datasource: {
      type: 'yesoreyeram-infinity-datasource',
      uid: '${infinity_datasource}',
    },
    columns: [
      { selector: 'date', text: 'Date', type: 'timestamp' },
      { selector: 'name', text: 'Name', type: 'string' },
      { selector: 'cost', text: 'Cost', type: 'number' },
    ],
    parser: 'simple',
    type: 'json',
    source: 'url',
    url_options: {
      method: 'GET',
      data: '',
    },
    format: 'timeseries',
    refId: 'A',
  },

  queryHubTarget: {
    datasource: {
      type: 'yesoreyeram-infinity-datasource',
      uid: '${infinity_datasource}',
    },
    columns: [
      { selector: 'date', text: 'Date', type: 'timestamp' },
      { selector: 'cost', text: 'Cost', type: 'number' },
      { selector: 'name', text: 'Hub', type: 'string' },
    ],
    parser: 'simple',
    type: 'json',
    source: 'url',
    url_options: {
      method: 'GET',
      data: '',
    },
    format: 'table',
    refId: 'A',
  },

  queryComponentTarget: {
    datasource: {
      type: 'yesoreyeram-infinity-datasource',
      uid: '${infinity_datasource}',
    },
    columns: [
      { selector: 'date', text: 'Date', type: 'timestamp' },
      { selector: 'cost', text: 'Cost', type: 'number' },
      { selector: 'component', text: 'Component', type: 'string' },
    ],
    parser: 'simple',
    type: 'json',
    source: 'url',
    url_options: {
      method: 'GET',
      data: '',
    },
    format: 'table',
  },

  // Individual queries for each component for accurate aggregation in table totals in the legend.
  queryComponentArray: [
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=compute',
      refid: 'compute',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=home%20storage',
      refid: 'home storage',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=object%20storage',
      refid: 'object storage',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=core',
      refid: 'core',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=networking',
      refid: 'networking',
    },    
  ],

  queryComponentHubArray: [
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=compute' + '&hub=$hub_general',
      refid: 'compute',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=home%20storage' + '&hub=$hub_general',
      refid: 'home storage',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=object%20storage' + '&hub=$hub_general',
      refid: 'object storage',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=core' + '&hub=$hub_general',
      refid: 'core',
    },
    $.queryComponentTarget + {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}' + '&component=networking' + '&hub=$hub_general',
      refid: 'networking',
    },    
  ],

  queryUsersTarget: {
    datasource: {
      type: 'yesoreyeram-infinity-datasource',
      uid: '${infinity_datasource}',
    },
    columns: [
      { selector: 'date', text: 'Date', type: 'timestamp' },
      { selector: 'value', text: 'Cost', type: 'number' },
      { selector: 'user', text: 'User', type: 'string' },
      { selector: 'usergroup', text: 'Group', type: 'string' },
      { selector: 'component', text: 'Component', type: 'string' },
    ],
    parser: 'simple',
    type: 'json',
    source: 'url',
    url_options: {
      method: 'GET',
      data: '',
    },
    format: 'table',
    refId: 'A',
  },

  queryGroupTarget: {
    datasource: {
      type: 'yesoreyeram-infinity-datasource',
      uid: '${infinity_datasource}',
    },
    columns: [
      { selector: 'date', text: 'Date', type: 'timestamp' },
      { selector: 'cost', text: 'Cost', type: 'number' },
      { selector: 'usergroup', text: 'Group', type: 'string' },
    ],
    parser: 'simple',
    type: 'json',
    source: 'url',
    url_options: {
      method: 'GET',
      data: '',
    },
    format: 'table',
    refId: 'A',
  },

  queryGroupMembershipTarget: {
    datasource: {
      type: 'yesoreyeram-infinity-datasource',
      uid: '${infinity_datasource}',
    },
    parser: 'simple',
    root_selector: '',
    type: 'json',
    source: 'url',
    url_options: {
      method: 'GET',
      data: '',
    },
    format: 'table',
    refId: 'A',
  },

  // grafana ref:   https://grafana.com/docs/grafana/v11.1/panels-visualizations/visualizations/time-series/
  // grafonnet ref: https://grafana.github.io/grafonnet/API/panel/timeSeries/index.html
  tsOptions:
    ts.standardOptions.withMin(0)
    + ts.options.withTooltip({ mode: 'multi', sort: 'desc' })
    + ts.fieldConfig.defaults.custom.withLineInterpolation('stepAfter')
    + ts.fieldConfig.defaults.custom.withFillOpacity(10)
    + ts.standardOptions.withUnit('currencyUSD')
    + ts.standardOptions.withNoValue('$0.00')
    + ts.standardOptions.withDecimals(2)
    + ts.options.withLegend({
      calcs: [
        'count',
        'min',
        'mean',
        'max',
        'sum',
      ],
      displayMode: 'table',
      placement: 'bottom',
      sortBy: 'Total',
      sortDesc: true,
    }),

  bcOptions:
    bc.standardOptions.withMin(0)
    + bc.standardOptions.withDecimals(2)
    + bc.standardOptions.withUnit('currencyUSD')
    + bc.options.withBarWidth(0.9)
    + bc.options.withFullHighlight(false)
    + bc.options.withLegend({ calcs: ['sum'] })
    + bc.options.legend.withDisplayMode('table')
    + bc.options.legend.withPlacement('right')
    + bc.options.legend.withSortBy('Total')
    + bc.options.legend.withSortDesc(true)
    + bc.options.tooltip.withMode('multi')
    + bc.options.tooltip.withSort('desc')
    + bc.options.withXTickLabelSpacing(100)
    + bc.options.withShowValue('never')
    + bc.options.withStacking('normal')
    + bc.queryOptions.withTransformations([
      bc.queryOptions.transformation.withId('formatTime')
      + bc.queryOptions.transformation.withOptions({
        outputFormat: 'MMM DD',
        timeField: 'Date',
        useTimezone: true,
      }),
      bc.queryOptions.transformation.withId('groupBy')
      + bc.queryOptions.transformation.withOptions({
        fields: {
          Component: {
            aggregations: [],
          },
          Cost: {
            aggregations: [
              'sum',
            ],
            operation: 'aggregate',
          },
          Date: {
            aggregations: [],
            operation: 'groupby',
          },
          User: {
            aggregations: [],
            operation: 'groupby',
          },
        },
      }),
      bc.queryOptions.transformation.withId('groupingToMatrix')
      + bc.queryOptions.transformation.withOptions({
        columnField: 'User',
        emptyValue: 'zero',
        rowField: 'Date',
        valueField: 'Cost (sum)',
      })
    ]),

  bgOptions:
    bg.options.withDisplayMode('basic')
    + bg.options.withOrientation('horizontal')
    + bg.options.withValueMode('text')
    + bg.standardOptions.withMin(0)
    + bg.standardOptions.withDecimals(2)
    + bg.standardOptions.withUnit('currencyUSD'),

  tsStylingComponents:
    ts.standardOptions.withOverrides([
      {
        matcher: { id: 'byName', options: 'compute' },
        properties: [{
          id: 'color',
          value: {
            fixedColor: 'blue',
            mode: 'fixed',
          },
        }],
      },
      {
        matcher: { id: 'byName', options: 'home storage' },
        properties: [{
          id: 'color',
          value: {
            fixedColor: 'yellow',
            mode: 'fixed',
          },
        }],
      },
      {
        matcher: { id: 'byName', options: 'object storage' },
        properties: [{
          id: 'color',
          value: {
            fixedColor: 'red',
            mode: 'fixed',
          },
        }],
      },
      {
        matcher: { id: 'byName', options: 'core' },
        properties: [{
          id: 'color',
          value: {
            fixedColor: 'green',
            mode: 'fixed',
          },
        }],
      },
      {
        matcher: { id: 'byName', options: 'networking' },
        properties: [{
          id: 'color',
          value: {
            fixedColor: 'orange',
            mode: 'fixed',
          },
        }],
      },
    ])
}
