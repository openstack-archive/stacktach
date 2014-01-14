The StackTach REST Interface
############################

stacky/deployments
==================

.. http:get:: /stacky/deployments/

   The list of all available deployments

   **Example request**:

   .. sourcecode:: http

      GET /stacky/deployments HTTP/1.1
      Host: example.com
      Accept: application/json

   **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: text/json

      [
        {
          "post_id": 12345,
          "author_id": 123,
          "tags": ["server", "web"],
          "subject": "I tried Nginx"
        },
        {
          "post_id": 12346,
          "author_id": 123,
          "tags": ["html5", "standards", "web"],
          "subject": "We go to HTML 5"
        }
      ]

   :query sort: one of ``hit``, ``created-at``
   :query offset: offset number. default is 0
   :query limit: limit number. default is 30
   :reqheader Accept: the response content type depends on
                      :mailheader:`Accept` header
   :reqheader Authorization: optional OAuth token to authenticate
   :resheader Content-Type: this depends on :mailheader:`Accept`
                            header of request
   :statuscode 200: no error
   :statuscode 404: there's no user


stacky/events
=============

stacky/hosts
============

stacky/uuid
===========

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
