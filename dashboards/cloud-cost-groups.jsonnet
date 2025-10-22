#!/usr/bin/env -S jsonnet -J ../../vendor
local grafonnet = import '../../vendor/gen/grafonnet-v11.4.0/main.libsonnet';
local dashboard = grafonnet.dashboard;
local bc = grafonnet.panel.barChart;
local bg = grafonnet.panel.barGauge;
local tb = grafonnet.panel.table;
local tb = grafonnet.panel.table;
local var = grafonnet.dashboard.variable;
local link = grafonnet.dashboard.link;

local common = import './common.libsonnet';

local TotalHub =
  common.bgOptions
  + bg.new('Total by Hub')
  + bg.panelOptions.withDescription(
    |||
      Total costs by hub are summed over the time period selected.

      - prod: the main production hub, e.g. <your-community>.2i2c.cloud
      - staging: a hub for testing, e.g. staging.<your-community>.2i2c.cloud
      - workshop: a hub for events such as workshops and tutorials, e.g. workshop.<your-community>.2i2c.cloud
    |||
  )
  + bg.panelOptions.withGridPos(h=7, w=8, x=0, y=0)
  + bg.panelOptions.withGridPos(h=7, w=8, x=0, y=0)
  + bg.queryOptions.withTargets([
    common.queryHubTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-hub?from=${__from:date}&to=${__to:date}',
    },
  ])
  + bg.queryOptions.withTransformations([
    bg.queryOptions.transformation.withId('groupBy')
    + bg.queryOptions.transformation.withOptions({
      fields: {
        Cost: {
          aggregations: [
            'sum',
          ],
          operation: 'aggregate',
        },
        Hub: {
          aggregations: [],
          operation: 'groupby',
        },
      },
    }),
    bg.queryOptions.transformation.withId('transpose'),
    bg.queryOptions.transformation.withId('organize')
    + bg.queryOptions.transformation.withOptions({
      excludeByName: {
        shared: true,
        support: true,
        binder: true,
      },
      includeByName: {},
      indexByName: {
        Field: 0,
        prod: 1,
        shared: 4,
        staging: 2,
        workshop: 3,
      },
      renameByName: {
        shared: 'support',
      },
    }),
  ])
  + bg.standardOptions.color.withMode('continuous-BlYlRd')
;

local TotalComponent =
  common.bgOptions
  + bg.new('Total by Component')
  + bg.panelOptions.withDescription(
    |||
      Total costs by component are summed over the time period selected.

      - compute: CPU and memory of user nodes
      - home storage: storage disks for user directories
      - networking: load balancing and virtual private cloud
      - object storage: cloud storage, e.g. AWS S3
      - core: resources to operate core infrastructure
    |||
  )
  + bg.panelOptions.withGridPos(h=7, w=8, x=8, y=0)
  + bg.queryOptions.withTargets([
    common.queryComponentTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-component?from=${__from:date}&to=${__to:date}',
    },
  ])
  + bg.queryOptions.withTransformations([
    bg.queryOptions.transformation.withId('groupBy')
    + bg.queryOptions.transformation.withOptions({
      fields: {
        Cost: {
          aggregations: [
            'sum',
          ],
          operation: 'aggregate',
        },
        Component: {
          aggregations: [],
          operation: 'groupby',
        },
      },
    }),
    bg.queryOptions.transformation.withId('transpose'),
    bg.queryOptions.transformation.withId('organize')
    + bg.queryOptions.transformation.withOptions({
      indexByName: {
        Field: 0,
        compute: 1,
        core: 5,
        'home storage': 2,
        networking: 4,
        'object storage': 3,
      },
    }),
  ])
  + bg.standardOptions.color.withMode('continuous-BlYlRd')
;

local TotalGroup =
  common.bgOptions
  + bg.new('Total by Group')
  + bg.panelOptions.withDescription(
    |||
      Total costs by group are summed over the time period selected.

      Note: Users with multiple group memberships are double-counted. E.g. if user 1 is a member of group 1 and group 2, then the user's individual costs are included in the total sum for group 1 and group 2. 
    |||
  )
  + bg.panelOptions.withGridPos(h=7, w=12, x=0, y=8)
  + bg.queryOptions.withTargets([
    common.queryGroupTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-group?from=${__from:date}&to=${__to:date}',
    },
  ])
  + bg.queryOptions.withTransformations([
    bg.queryOptions.transformation.withId('groupBy')
    + bg.queryOptions.transformation.withOptions({
      fields: {
        Cost: {
          aggregations: [
            'sum',
          ],
          operation: 'aggregate',
        },
        Group: {
          aggregations: [],
          operation: 'groupby',
        },
      },
    }),
    bg.queryOptions.transformation.withId('sortBy')
    + bg.queryOptions.transformation.withOptions({
      sort: [
        {
          asc: true,
          field: 'Group',
        },
      ],
    }),    
    bg.queryOptions.transformation.withId('transpose')
  ])
  + bg.standardOptions.color.withMode('continuous-BlYlRd')
;

local Top5 =
  common.bgOptions
  + bg.new('Top 5 users')
  + bg.panelOptions.withDescription(
    |||
      Shows the top 5 users by cost across all hubs and components over the selected time period.
    |||
  )
  + bg.panelOptions.withGridPos(h=7, w=8, x=16, y=0)
  + bg.queryOptions.withTargets([
    common.queryUsersTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/costs-per-user?from=${__from:date}&to=${__to:date}',
    },
  ])
  + bg.options.reduceOptions.withValues(true)
  + bg.standardOptions.color.withMode('thresholds')
  + bg.standardOptions.thresholds.withMode('percentage')
  + bg.standardOptions.thresholds.withSteps([
    {
      color: 'green',
    },
    {
      color: 'red',
      value: 80,
    },
  ])
  + bg.queryOptions.withTransformations([
    bg.queryOptions.transformation.withId('groupBy')
    + bg.queryOptions.transformation.withOptions({
      fields: {
        Cost: {
          aggregations: [
            'sum',
          ],
          operation: 'aggregate',
        },
        User: {
          aggregations: [],
          operation: 'groupby',
        },
        date: {
          aggregations: [],
        },
        user: {
          aggregations: [],
          operation: 'groupby',
        },
        value: {
          aggregations: [
            'sum',
          ],
          operation: 'aggregate',
        },
      },
    }),
    bg.queryOptions.transformation.withId('sortBy')
    + bg.queryOptions.transformation.withOptions({
      sort: [
        {
          desc: true,
          field: 'Cost (sum)',
        },
      ],
    }),
    bg.queryOptions.transformation.withId('limit')
    + bg.queryOptions.transformation.withOptions({
      limitField: '5',
    }),
  ])
;

local TotalGroup =
  common.bgOptions
  + bg.new('Total by Group')
  + bg.panelOptions.withDescription(
    |||
      Total costs by group are summed across all hubs and components over the time period selected.

      Note: Users with multiple group memberships are double-counted. E.g. if user 1 is a member of group 1 and group 2, then the user's individual costs are included in the total sums of each group.
    |||
  )
  + bg.panelOptions.withGridPos(h=7, w=12, x=0, y=8)
  + bg.queryOptions.withTargets([
    common.queryGroupTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/total-costs-per-group?from=${__from:date}&to=${__to:date}',
    },
  ])
  + bg.queryOptions.withTransformations([
    bg.queryOptions.transformation.withId('groupBy')
    + bg.queryOptions.transformation.withOptions({
      fields: {
        Cost: {
          aggregations: [
            'sum',
          ],
          operation: 'aggregate',
        },
        Group: {
          aggregations: [],
          operation: 'groupby',
        },
      },
    }),
    bg.queryOptions.transformation.withId('sortBy')
    + bg.queryOptions.transformation.withOptions({
      sort: [
        {
          asc: true,
          field: 'Group',
        },
      ],
    }),    
    bg.queryOptions.transformation.withId('transpose')
  ])
  + bg.standardOptions.color.withMode('continuous-BlYlRd')
;

local MultipleGroup =
  tb.new('Users with multiple group memberships')
  + tb.panelOptions.withDescription(
    |||
      List of users with multiple group memberships.

      Note: Users with multiple group memberships are double-counted. E.g. if user 1 is a member of group 1 and group 2, then the user's individual costs are included in the total sums of each group.
    |||
  )
  + tb.panelOptions.withGridPos(h=7, w=12, x=12, y=7)
  + tb.queryOptions.withTargets([
    common.queryMultipleGroupTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/user-groups?from=${__from:date}&to=${__to:date}',
    },
  ])
  + tb.queryOptions.withTransformations([
    tb.queryOptions.transformation.withId('groupBy')
    + tb.queryOptions.transformation.withOptions({
      fields: {
        usergroup: {
          aggregations: [],
          operation: 'aggregate',
        },
        username_escaped: {
          aggregations: [],
          operation: 'groupby',
        },
      },
    }),
    tb.queryOptions.transformation.withId('groupToNestedTable')
    + tb.queryOptions.transformation.withOptions({
      fields: {
        "usergroup": {
          "aggregations": []
        },
        "username_escaped": {
          "aggregations": [],
          "operation": "groupby"
        }
      }
    }),    
    tb.queryOptions.transformation.withId('organize')
    + tb.queryOptions.transformation.withOptions({
      renameByName: {
        username_escaped: 'User',
      },
    }),
  ])
;

local Hub =
  common.bcOptions
  + bc.new('Hub – $hub_user, Component – $component')
  + bc.panelOptions.withDescription(
    |||
      Shows daily user costs by hub, with a total across all hubs, components and groups shown by default.

      Try toggling the *hub*, *component* and *group* variable dropdown above to filter per user costs.
    |||
  )
  + bg.panelOptions.withGridPos(h=12, w=24, x=0, y=8)
  + bc.queryOptions.withTargets([
    common.queryUsersTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/costs-per-user?from=${__from:date}&to=${__to:date}&hub=$hub_user&component=$component&limit=$limit',
    },
  ])
  + bc.panelOptions.withRepeat('hub_user')
  + bc.panelOptions.withRepeatDirection('v')
;

dashboard.new('Group cloud costs')
+ dashboard.withUid('cloud-cost-users')
+ dashboard.withTimezone('utc')
+ dashboard.withEditable(true)
+ dashboard.time.withFrom('now-30d')
+ dashboard.withVariables([
  common.variables.infinity_datasource,
  common.variables.hub_user,
  common.variables.component,
  common.variables.user_groups,
  common.variables.limit,
])
+ dashboard.withLinks([
  link.link.new('Community Hub Guide', 'https://docs.2i2c.org/admin/monitoring/'),
])
+ dashboard.withPanels(
  [
    TotalGroup,
    Hub,
  ],
)
