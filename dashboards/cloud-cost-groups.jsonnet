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

local TotalGroup =
  common.bgOptions
  + bg.new('Total by Group')
  + bg.panelOptions.withDescription(
    |||
      Total costs by group are summed over the time period selected.

      *Note:* Users with multiple group memberships are double-counted. E.g. if user 1 is a member of group 1 and group 2, then the user's individual costs are included in the total sum for group 1 and group 2. To avoid double-counting, assign each user to a unique group.
    |||
  )
  + bg.panelOptions.withGridPos(h=7, w=8, x=0, y=0)
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

      *Note:* Users with multiple group memberships are double-counted. E.g. if user 1 is a member of group 1 and group 2, then the user's individual costs are included in the total sums of each group. To avoid double-counting, assign each user to a unique group.
    |||
  )
  + tb.panelOptions.withGridPos(h=7, w=8, x=8, y=0)
  + tb.queryOptions.withTargets([
    common.queryGroupMembershipTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/users-with-multiple-groups',
    },
  ])
  + tb.queryOptions.withTransformations([
    tb.queryOptions.transformation.withId('organize')
    + tb.queryOptions.transformation.withOptions({
      renameByName: {
        hub: 'Hub',
        usergroup: 'Group',
        username: 'User',
      },
    }),
    tb.queryOptions.transformation.withId('groupToNestedTable')
    + tb.queryOptions.transformation.withOptions({
      "fields": {
        "User": {
          "aggregations": [],
          "operation": "groupby"
        },      
      },
      "showSubframeHeaders": true
    }),    
  ])
  + tb.fieldConfig.defaults.custom.withFilterable(value=true)    
;

local NoGroup =
  tb.new('Users with no group memberships')
  + tb.panelOptions.withDescription(
    |||
      Users with no group memberships assigned. This could mean:

        - this user has not logged into the hub, since user group memberships are updated during the authorization flow
        - this user used to be assigned a group and has since been removed.
    |||
  )
  + tb.panelOptions.withGridPos(h=7, w=8, x=16, y=0)
  + tb.queryOptions.withTargets([
    common.queryGroupMembershipTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/users-with-no-groups',
    },
  ])
  + tb.queryOptions.withTransformations([
    tb.queryOptions.transformation.withId('organize')
    + tb.queryOptions.transformation.withOptions({
      "indexByName": {
        "hub": 1,
        "username": 0
      },
      "orderByMode": "manual",
      "renameByName": {
        "hub": "Hub",
        "username": "User",
      }
    }), 
  ])
  + tb.fieldConfig.defaults.custom.withFilterable(value=true)  
;

local Hub =
  common.bcOptions
  + bc.new('Hub – $hub_user, Component – $component')
  + bc.panelOptions.withDescription(
    |||
      Shows daily group costs by hub, with a total across all hubs, components and groups shown by default.

      Try toggling the *hub*, *component* and *group* variable dropdown above to filter per group costs.
    |||
  )
  + bg.panelOptions.withGridPos(h=12, w=24, x=0, y=8)
  + bc.queryOptions.withTargets([
    common.queryUsersTarget
    {
      url: 'http://jupyterhub-cost-monitoring.support.svc.cluster.local/costs-per-user?from=${__from:date}&to=${__to:date}&hub=$hub_user&component=$component&usergroup=$usergroup',
    },
  ])
  + bc.panelOptions.withRepeat('hub_user')
  + bc.panelOptions.withRepeatDirection('v')
  + bc.queryOptions.withTransformations([
      bc.queryOptions.transformation.withId('formatTime')
      + bc.queryOptions.transformation.withOptions({
        "outputFormat": "MMM DD",
        "timeField": "Date",
        "timezone": "utc",
        "useTimezone": true        
      }),
      bc.queryOptions.transformation.withId('groupBy')
      + bc.queryOptions.transformation.withOptions({
        fields: {
          Cost: {
            aggregations: [
              'sum',
            ],
            operation: 'aggregate',
          },
          Date: {
            "aggregations": [],
            "operation": "groupby"
          },
          Group: {
            "aggregations": [],
            "operation": "groupby"
          },
        },
      }),
      bc.queryOptions.transformation.withId('groupingToMatrix')
      + bc.queryOptions.transformation.withOptions({
        "columnField": "Group",
        "emptyValue": "zero",
        "rowField": "Date",
        "valueField": "Cost (sum)"
      })
  ])
;

dashboard.new('Group cloud costs')
+ dashboard.withUid('cloud-cost-users')
+ dashboard.withTimezone('utc')
+ dashboard.withEditable(true)
+ dashboard.time.withFrom('now-30d')
+ dashboard.withVariables([
  common.variables.infinity_datasource,
  common.variables.prometheus_datasource,
  common.variables.hub_user,
  common.variables.component,
  common.variables.usergroup,
])
+ dashboard.withLinks([
  link.link.new('Community Hub Guide', 'https://docs.2i2c.org/admin/monitoring/'),
])
+ dashboard.withPanels(
  [
    TotalGroup,
    MultipleGroup,
    NoGroup,
    Hub,
  ],
)
