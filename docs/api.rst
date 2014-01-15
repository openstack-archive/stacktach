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
      ]

  :query service: ``nova`` or ``glance``. default="nova"


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


stacky/timings
==============

stacky/timings/uuid
===================

stacky/summary
==============

stacky/request
==============

stacky/reports
==============

stacky/report/<report_id>
=========================

stacky/show/<event_id>
======================

stacky/watch/<deployment_id>
============================

stacky/search
=============

stacky/kpi
==========

stacky/kpi/<tenant_id>
======================

stacky/usage/launches
=====================

stacky/usage/deletes
====================

stacky/usage/exists
===================
