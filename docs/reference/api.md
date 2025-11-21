

<h1 id="fastapi-default">Default</h1>

## Index

<a id="opIdindex__get"></a>

`GET /`

<h3 id="index-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|

## Ready

<a id="opIdready_health_ready_get"></a>

`GET /health/ready`

Readiness probe endpoint.

<h3 id="ready-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|

## Hub Names

<a id="opIdhub_names_hub_names_get"></a>

`GET /hub-names`

Endpoint to query hub names.

<h3 id="hub-names-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|

<h3 id="hub-names-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Component Names

<a id="opIdcomponent_names_component_names_get"></a>

`GET /component-names`

Endpoint to serve component names.

<h3 id="component-names-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|

## Total Costs

<a id="opIdtotal_costs_total_costs_get"></a>

`GET /total-costs`

Endpoint to query total costs.

<h3 id="total-costs-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|

<h3 id="total-costs-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## User Groups

<a id="opIduser_groups_user_groups_get"></a>

`GET /user-groups`

Endpoint to serve user group memberships.

<h3 id="user-groups-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|
|hub|query|any|false|Name of the hub to filter results|
|username|query|any|false|Name of the user to filter results|
|usergroup|query|any|false|Name of the group to filter results|

<h3 id="user-groups-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Users With Multiple Groups

<a id="opIdusers_with_multiple_groups_users_with_multiple_groups_get"></a>

`GET /users-with-multiple-groups`

Endpoint to serve users with multiple groups.

<h3 id="users-with-multiple-groups-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|hub_name|query|any|false|Name of the hub to filter results|
|user_name|query|any|false|Name of the user to filter results|

<h3 id="users-with-multiple-groups-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Users With No Groups

<a id="opIdusers_with_no_groups_users_with_no_groups_get"></a>

`GET /users-with-no-groups`

Endpoint to serve users with no groups.

<h3 id="users-with-no-groups-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|hub_name|query|any|false|Name of the hub to filter results|
|user_name|query|any|false|Name of the user to filter results|

<h3 id="users-with-no-groups-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Total Costs Per Hub

<a id="opIdtotal_costs_per_hub_total_costs_per_hub_get"></a>

`GET /total-costs-per-hub`

Endpoint to query total costs per hub.

<h3 id="total-costs-per-hub-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|

<h3 id="total-costs-per-hub-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Total Costs Per Component

<a id="opIdtotal_costs_per_component_total_costs_per_component_get"></a>

`GET /total-costs-per-component`

Endpoint to query total costs per component.

<h3 id="total-costs-per-component-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|
|hub|query|any|false|Name of the hub to filter results|
|component|query|any|false|Name of the component to filter results|

<h3 id="total-costs-per-component-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Total Costs Per Group

<a id="opIdtotal_costs_per_group_total_costs_per_group_get"></a>

`GET /total-costs-per-group`

Endpoint to query total costs per user group.

<h3 id="total-costs-per-group-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|

<h3 id="total-costs-per-group-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Costs Per User

<a id="opIdcosts_per_user_costs_per_user_get"></a>

`GET /costs-per-user`

Endpoint to query costs per user by combining AWS costs with Prometheus usage data.

This endpoint calculates individual user costs by:
1. Getting total AWS costs per component (compute, storage) from Cost Explorer
2. Getting usage fractions per user from Prometheus metrics
3. Multiplying total costs by each user's usage fraction

Query Parameters:
    from (str): Start date in YYYY-MM-DD format (defaults to 30 days ago)
    to (str): End date in YYYY-MM-DD format (defaults to current date)
    hub (str, optional): Filter to specific hub namespace
    component (str, optional): Filter to specific component (compute, home storage)
    user (str, optional): Filter to specific user
    usergroup (str, optional): Filter to specific user group
    limit (int, optional): Limit number of results to top N users by total cost.

Returns:
    List of dicts with keys: date, hub, component, user, value (cost in USD)
    Results are sorted by date, hub, component, then value (highest cost first)

<h3 id="costs-per-user-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|
|hub|query|any|false|Name of the hub to filter results|
|component|query|any|false|Name of the component to filter results|
|user|query|any|false|Name of the user to filter results|
|usergroup|query|any|false|Name of user group to filter results|
|limit|query|any|false|Limit number of results to top N users by total cost.|

<h3 id="costs-per-user-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

## Total Usage

<a id="opIdtotal_usage_total_usage_get"></a>

`GET /total-usage`

Endpoint to query total usage.
Expects 'from' and 'to' query parameters in the api_provider YYYY-MM-DD.
Optionally accepts 'hub', 'component' and 'user', query parameters.

<h3 id="total-usage-parameters">Parameters</h3>

|Name|In|Type|Required|Description|
|---|---|---|---|---|
|from|query|any|false|Start date in YYYY-MM-DDTHH:MMZ format|
|to|query|any|false|End date in YYYY-MM-DDTHH:MMZ format|
|hub|query|any|false|Name of the hub to filter results|
|component|query|any|false|Name of the component to filter results|
|user|query|any|false|Name of the user to filter results|

<h3 id="total-usage-responses">Responses</h3>

|Status|Meaning|Description|
|---|---|---|
|200|[OK](https://tools.ietf.org/html/rfc7231#section-6.3.1)|Successful Response|
|422|[Unprocessable Entity](https://tools.ietf.org/html/rfc2518#section-10.3)|Validation Error|

