The StackTach REST Interface
############################

JSON Response Format
********************

StackTach uses an tabular JSON response format to make it easier for
Stacky to display generic results.

The JSON response format is as follows: ::

  [
    ['column header', 'column header', 'column header', ...],
    ['row 1, col 1', 'row 1, col 2', 'row 1, col 3', ...],
    ['row 2, col 1', 'row 2, col 2', 'row 2, col 3', ...],
    ['row 3, col 1', 'row 3, col 2', 'row 3, col 3', ...],
    ...
  ]

stacky/deployments
==================

.. http:get:: http://example.com/stacky/deployments/

   The list of all available deployments

   **Example request**:

   .. sourcecode:: http

      GET /stacky/deployments/ HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ['#', 'Name'],
        [1, 'deployment name'],
        [2, 'deployment name'],
        ...
      ]

stacky/events
=============

.. http:get:: http://example.com/stacky/events/

   The distinct list of all event names

   **Example request**:

   .. sourcecode:: http

      GET /stacky/events/ HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ['Event Name'],
        ["add_fixed_ip_to_instance"],
        ["attach_volume"],
        ["change_instance_metadata"],
        ["compute.instance.create.end"],
        ["compute.instance.create.error"],
        ["compute.instance.create.start"],
        ["compute.instance.create_ip.end"],
        ...
      ]

  :query service: ``nova`` or ``glance``. default="nova"

stacky/hosts
============

.. http:get:: http://example.com/stacky/hosts/

   The distinct list of all hosts sending notifications.

   **Example request**:

   .. sourcecode:: http

      GET /stacky/hosts/ HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ['Host Name'],
        ["compute-1"],
        ["compute-2"],
        ["scheduler-x"],
        ["api-88"],
        ...

  :query service: ``nova`` or ``glance``. default="nova"
      ]

stacky/uuid
===========

.. http:get:: http://example.com/stacky/uuid/

   Retrieve all notifications for instances with a given UUID.

   **Example request**:

   .. sourcecode:: http

      GET /stacky/uuid/?uuid=77e0f192-00a2-4f14-ad56-7467897828ea  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ["#", "?", "When", "Deployment", "Event", "Host", "State",
         "State'", "Task"],
        [
            40065869,
            " ",
            "2014-01-14 15:39:22.574829",
            "region-1",
            "compute.instance.snapshot.start",
            "compute-99",
            "active",
            "",
            ""
        ],
        [
            40065879,
            " ",
            "2014-01-14 15:39:23.599298",
            "region-1",
            "compute.instance.update",
            "compute-99",
            "active",
            "active",
            "image_snapshot"
        ],
        ...
      ]

  :query uuid: UUID of desired instance.
  :query service: ``nova`` or ``glance``. default="nova"


stacky/timings/uuid/
====================

.. http:get:: http://example.com/stacky/timings/uuid/

   Retrieve all timings for a given instance. Timings are the time
   deltas between related .start and .end notifications. For example,
   the time difference between ``compute.instance.run_instance.start``
   and ``compute.instance.run_instance.end``. This url works only for nova.

   The first column of the response will be

   * ``S`` if there is a ``.start`` event and no ``.end``
   * ``E`` if there is a ``.end`` event and no ``.start``
   * ``.`` if there was a ``.start`` and ``.end`` event

   No time difference will be returned in the ``S`` or ``E`` cases.

   **Example request**:

   .. sourcecode:: http

      GET /stacky/timings/uuid/?uuid=77e0f192-00a2-4f14-ad56-7467897828ea  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ["?", "Event", "Time (secs)"],
        [".", "compute.instance.create", "0d 00:00:55.50"],
        [".", "compute.instance.snapshot", "0d 00:14:11.71"],
        [".", "compute.instance.snapshot", "0d 00:17:31.33"],
        [".", "compute.instance.snapshot", "0d 00:16:48.88"]
        ...
      ]

  :query uuid: UUID of desired instance.


stacky/summary
==============

.. http:get:: http://example.com/stacky/summary/

   Returns timing summary information for each event type
   collected. Only notifications with ``.start``/``.end`` pairs
   are considered. This url works only for nova.

   This includes: ::

   * the number of events seen of each type (N)
   * the Minimum time seen
   * the Maximum time seen
   * the Average time seen

   **Example request**:

   .. sourcecode:: http

      GET /stacky/summary/  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ["Event", "N", "Min", "Max", "Avg"],
        ["compute.instance.create", 50,
            "0d 00:00:52.88", "0d 01:41:14.27", "0d 00:08:26"],
        ["compute.instance.create_ip", 50,
            "0d 00:00:06.80", "5d 20:16:47.08", "0d 03:47:17"],
        ...
      ]

  :query uuid: UUID of desired instance.
  :query limit: the number of timings to return.
  :query offset: offset into query result set to start from.


stacky/request
==============

.. http:get:: http://example.com/stacky/request/

   Returns all notifications related to a particular Request ID.

   The ``?`` column will be ``E`` if the event came from the ``.error``
   queue. ``State`` and ``State'`` are the current state and the previous
   state, respectively. This url works only for nova.

   **Example request**:

   .. sourcecode:: http

      GET /stacky/request/?request_id=req-a7517402-6192-4d0a-85a1-e14051790d5a  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ["#", "?", "When", "Deployment", "Event", "Host", "State",
         "State'", "Task'"
        ],
        [
            40368306,
            " ",
            "2014-01-15 15:39:34.130286",
            "region-1",
            "compute.instance.update",
            "api-1",
            "active",
            "active",
            null
        ],
        [
            40368308,
            " ",
            "2014-01-15 15:39:34.552434",
            "region-1",
            "compute.instance.update",
            "api-1",
            "active",
            null,
            null
        ],

        ...
      ]

  :query request_id: desired request ID
  :query when_min: unixtime to start search
  :query when_max: unixtime to end search
  :query limit: the number of timings to return.
  :query offset: offset into query result set to start from.


stacky/reports
==============

.. http:get:: http://example.com/stacky/reports/

   Returns a list of all available reports.

   The ``Start`` and ``End`` columns refer to the time span
   the report covers (in unixtime).

   **Example request**:

   .. sourcecode:: http

      GET /stacky/reports/ HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        ["Id", "Start", "End", "Created", "Name", "Version"],
        [
            5971,
            1389726000.0,
            1389729599.0,
            1389730212.9474499,
            "summary for region: all",
            4
        ],
        [
            5972,
            1389729600.0,
            1389733199.0,
            1389733809.979934,
            "summary for region: all",
            4
        ],

        ...
      ]

  :query created_from: unixtime to start search
  :query created_to: unixtime to end search
  :query limit: the number of timings to return.
  :query offset: offset into query result set to start from.

stacky/report/<report_id>
=========================

.. http:get:: http://example.com/stacky/report/<report_id>

   Returns a specific report.

   The contents of the report varies by the specific report, but
   all are in row/column format with Row 0 being a special *metadata* row.

   Row 0 of each report is a dictionary of metadata about the report. The
   actual row/columns of the report start at Row 1 onwards (where Row 1
   is the Column headers and Rows 2+ are the details, as with other result
   sets)

   **Example request**:

   .. sourcecode:: http

      GET /stacky/report/1/ HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        {
            "4xx failure count": 0,
            "4xx failure percentage": 0.0,
            "5xx failure count": 1,
            "5xx failure percentage": 0.018284904,
            "> 30 failure count": 13,
            "> 30 failure percentage": 1.13479794,
            "cells": [
                "c0001",
                "global",
                "c0003",
                "c0004",
                "c0011",
                "c0010",
                "a0001",
                "c0012",
                "b0002",
                "a0002"
            ],
            "end": 1389729599.0,
            "failure_grand_rate": 0.2445074415308293,
            "failure_grand_total": 14,
            "hours": 1,
            "pct": 0.014999999999999999,
            "percentile": 97,
            "region": null,
            "start": 1389726000.0,
            "state failure count": 0,
            "state failure percentage": 0.0,
            "total": 411
        },
        ["Operation", "Image", "OS Type", "Min", "Max", "Med", "97%", "Requests",
         "4xx", "% 4xx", "5xx", "% 5xx", "> 30", "% > 30", "state", "% state"],
        [
            "aux",
            "snap",
            "windows",
            "0s",
            "5s",
            "0s",
            "5s",
            6,
            0,
            0.0,
            0,
            0.0,
            0,
            0.0,
            0,
            0.0
        ],
        [
            "resize",
            "base",
            "linux",
            "1s",
            "5:44s",
            "1:05s",
            "3:44s",
            9,
            0,
            0.0,
            0,
            0.0,
            0,
            0.0,
            0,
            0.0
        ],

        ...
      ]

stacky/reports/search/
=========================

.. http:get:: http://example.com/stacky/reports/search

   Returns reports that match the search criteria in descending order of id.

   The contents of the report varies by the specific report, but
   all are in row/column format with Row 0 being a special *metadata* row.
   The actual row/columns of the report start at Row 1 onwards.

   **Example request**:

   .. sourcecode:: http

      GET /stacky/reports/search/ HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        [
            "Id",
            "Start",
            "End",
            "Created",
            "Name",
            "Version"
        ],

        [
            4253,
            "2013-11-21 00:00:00",
            "2013-11-22 00:00:00",
            "2013-11-22 01:44:55",
            "public outbound bandwidth",
            1
        ],
        [
            4252,
            "2014-01-18 00:00:00",
            "2013-11-22 00:00:00",
            "2013-11-22 01:44:55",
            "image events audit",
            1
        ],
        [
            4248,
            "2013-11-21 00:00:00",
            "2013-11-22 00:00:00",
            "2013-11-22 01:44:55",
            "Error detail report",
            1
        ],

        ...
      ]

  :query id: integer report id
  :query name: string report name(can include spaces)
  :query period_start: start of period, which the report pertains to, in the following format: YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]
  :query period_end: end of period, which the report pertains to, in the following format: YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]
  :query created: the day, when the report was created, in the following format: YYYY-MM-DD

stacky/show/<event_id>
======================

.. http:get:: http://example.com/stacky/show/<event_id>/

   Show the details on a specific notification.

   The response of this operation is non-standard. It returns 3 rows:

   * The first row is the traditional row-column result set used by most
     commands.
   * The second row is a prettied, stringified version of the full JSON payload
     of the raw notification.
   * The third row is the UUID of the related instance, if any.

   **Example request**:

   .. sourcecode:: http

      GET /stacky/show/1234/  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        [
          ["Key", "Value"],
          ["#", 1234 ],
          ["When", "2014-01-15 20:39:44.277745"],
          ["Deployment", "region-1"],
          ["Category", "monitor.info"],
          ["Publisher", "compute-1"],
          ["State", "active"],
          ["Event", "compute.instance.update"],
          ["Service", "compute"],
          ["Host", "compute-1"],
          ["UUID", "8eba1a6d-43eb-1343-8d1a-5e596f5233b5"],
          ["Req ID", "req-1368539d-f645-4d96-842e-03b5c5c9dc8c"],
          ...
        ],
        "[\n  \"monitor.info\", \n  {\n    \"_context_request_id\": \"req-13685e9d-f645-4d96-842e-03b5c5c9dc8c\", \n    \"_context_quota_class\": null, \n    \"event_type\": \"compute.instance.update\", \n    \"_context_service_catalog\": [], \n    \"_context_auth_token\": \"d81a25d03bb340bb82b4b67d105cc42d\", \n    \"_context_user_id\": \"b83e2fac644c4215bc449fb4b5c9bbfa\", \n    \"payload\": {\n      \"state_description\": \"\", \n      \"availability_zone\": null, \n      \"terminated_at\": \"\", \n      \"ephemeral_gb\": 300, \n ...",
        "8eba1a6d-43eb-1343-8d1a-5e596f5233b5"
      ]

  :query service: ``nova`` or ``glance``. default="nova"
  :query event_id: desired Event ID


stacky/watch/<deployment_id>
============================

.. http:get:: http://example.com/stacky/watch/<deployment_id>/

   Get a real-time feed of notifications.

   Once again, this is a non-standard response (not the typical row-column format).
   This call returns a tuple of information:

   * A list of column widths, to be used as a hint for formatting.
   * A list of events that meet the query criteria.
     * the db id of the event
     * the type of event (``E`` for errors, ``.`` otherwise)
     * stringified date of the event
     * stringified time of the event
     * deployment name
     * the event name
     * the instance UUID, if available
   * The ending unixtime timestamp. The last time covered by this query
     (utcnow, essentially)

      **Example request**:

   .. sourcecode:: http

      GET /stacky/watch/14/  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        [10, 1, 15, 20, 50, 36],
        [
        ... events ...
        ]
        "1389892207"
      ]

  :query service: ``nova`` or ``glance``. default="nova"
  :query since: get all events since ``unixtime``. Defaults to 2 seconds ago.
  :query event_name: only watch for ``event_name`` notifications. Defaults to all events.


stacky/search
=============

.. http:get:: http://example.com/stacky/search/

   Search for notifications.

   Returns:

   * Event ID
   * ``E`` for errors, ``.`` otherwise
   * unixtime for when the event was generated
   * the deployment name
   * the event name
   * the host name
   * the instance UUID
   * the request ID

      **Example request**:

   .. sourcecode:: http

      GET /stacky/search/  HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        [...event info as listed above...]
      ]

  :query service: ``nova`` or ``glance``. default="nova"
  :query field: notification field to search on.
  :query value: notification values to find.
  :query when_min: unixtime to start search
  :query when_max: unixtime to end search
