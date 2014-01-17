The StackTach Database REST Interface
############################

JSON Response Format
********************

The StackTach Database API uses a more standard data model for access to database objects. The Database API is read only, with the exception of usage confirmation, which is used to indicate that usage has been sent downstream.

The JSON response format uses an envelope with a single key to indicate the type of object returned. This object can be either a dictionary in the case of queries that return single objects, or a list when multiple objects are turned.

Sample JSON response, single object: ::

  {
    "enitity":
    {
      "id": 1
      "key1": "value1",
      "key2": "value2"
    }
  }

Sample JSON response, multiple objects: ::

  {
    "enitities":
    [
      {
        "id": 1,
        "key1": "value1",
        "key2": "value2"
      },
      {
        "id": 2,
        "key1": "value1",
        "key2": "value2"
      }
    ]
  }


db/confirm/usage/exists/batch/
=====================================

.. http:put:: http://example.com/db/confirm/usage/exists/batch/

  Uses the provided message_id's and http status codes to update image and instance exists send_status values.

  **Example V0 request**:

   .. sourcecode:: http

      PUT db/confirm/usage/exists/batch/ HTTP/1.1
      Host: example.com
      Accept: application/json

      {
        "messages":
        [
          {"nova_message_id": 200},
          {"nova_message_id": 400}
        ]
      }

  **Example V1 request**:

   .. sourcecode:: http

      PUT db/confirm/usage/exists/batch/ HTTP/1.1
      Host: example.com
      Accept: application/json

      {
        "messages":
        [
          {
            "nova":
            [
              {"nova_message_id1": 200},
              {"nova_message_id2": 400}
            ],
            "glance":
            [
              {"glance_message_id1": 200},
              {"glance_message_id2": 400}
            ]
          }
        ]
        "version": 1
      }
  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

db/usage/launches/
==================

.. http:get:: http://example.com/db/usage/launches/

Deprecated, see: :ref:`dbapi-nova-launches`

.. _dbapi-nova-launches:

db/usage/nova/launches/
=======================

.. http:get:: http://example.com/db/usage/nova/launches/

  Returns a list of instance launches matching provided query criteria.

  **Query Parameters**

  * ``launched_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``launched_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``instance``: uuid
  * ``limit``: int, default: 50, max: 1000
  * ``offset``: int, default: 0

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/nova/launches/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "launches":
        [
          {
            "os_distro": "org.centos",
            "os_version": "5.8",
            "instance_flavor_id": "2",
            "instance_type_id": "2",
            "launched_at": "2014-01-17 15:35:44",
            "instance": "72e4d8e8-9f63-47cb-a904-0193e5edac6e",
            "os_architecture": "x64",
            "request_id": "req-7a86ed49-e1f4-4403-b3ef-22636f7acb7d",
            "rax_options": "0",
            "id": 91899,
            "tenant": "5853600"
          },
          {
            "os_distro": "org.centos",
            "os_version": "5.8",
            "instance_flavor_id": "performance1-4",
            "instance_type_id": "11",
            "launched_at": "2014-01-17 15:35:20",
            "instance": "932bcfd9-af68-4261-805e-6e43156c3b40",
            "os_architecture": "x64",
            "request_id": "req-6bfe911f-40f2-4fd8-946a-070c10bed014",
            "rax_options": "0",
            "id": 91898,
            "tenant": "5853595"
          }
        ]
      }

db/usage/glance/images/
=======================

.. http:get:: http://example.com/db/usage/glance/images/

  Returns a list of images matching provided query criteria.

  **Query Parameters**

  * ``created_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``created_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``limit``: int, default: 50, max: 1000
  * ``offset``: int, default: 0

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/glance/images/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "images":
        [
          {
            "uuid": "2048efd8-fdce-4123-bdbc-add3bfe64b83",
            "created_at": "2014-01-17 02:28:08",
            "owner": null,
            "last_raw": 299977,
            "id": 4837,
            "size": 9192352
          },
          {
            "uuid": "aa2c07dd-fd1c-4ad3-9f73-6a6d7d8a0dbd",
            "created_at": "2014-01-17 02:24:18",
            "owner": "5937488",
            "last_raw": 299967,
            "id": 4836,
            "size": 9
          }
        ]
      }

db/usage/launches/<launch_id>/
==============================

.. http:get:: http://example.com/db/usage/launches/<launch_id>/

Deprecated, see: :ref:`dbapi-nova-launch`

.. _dbapi-nova-launch:

db/usage/nova/launches/<launch_id>/
===================================

.. http:get:: http://example.com/db/usage/nova/launches/<launch_id>/

Returns the single launch with id matching the provided id.

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/nova/launches/91898/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "launch":
        {
          "os_distro": "org.centos",
          "os_version": "5.8",
          "instance_flavor_id": "performance1-4",
          "instance_type_id": "11",
          "launched_at": "2014-01-17 15:35:20",
          "instance": "932bcfd9-af68-4261-805e-6e43156c3b40",
          "os_architecture": "x64",
          "request_id": "req-6bfe911f-40f2-4fd8-946a-070c10bed014",
          "rax_options": "0",
          "id": 91898,
          "tenant": "5853595"
        }
      }

db/usage/glance/images/<image_id>/
==================================

.. http:get:: http://example.com/db/usage/glance/images/<image_id>/

Returns the single image with id matching the provided id.

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/glance/images/4836/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "launch":
        {
          "uuid": "aa2c07dd-fd1c-4ad3-9f73-6a6d7d8a0dbd",
          "created_at": "2014-01-17 02:24:18",
          "owner": "5937488",
          "last_raw": 299967,
          "id": 4836,
          "size": 9
        }
      }

db/usage/deletes/
=================

.. http:get:: http://example.com/db/usage/deletes/

Deprecated, see: :ref:`dbapi-nova-deletes`

.. _dbapi-nova-deletes:

db/usage/nova/deletes/
======================

.. http:get:: http://example.com/db/usage/nova/deletes/

  Returns a list of instance deletes matching provided query criteria.

  **Query Parameters**

  * ``launched_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``launched_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``instance``: uuid
  * ``limit``: int, default: 50, max: 1000
  * ``offset``: int, default: 0

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/nova/deletes/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "deletes":
        [
          {
            "raw": 14615347,
            "instance": "b36a8c2d-af88-4371-b14c-14dadf7073e5",
            "deleted_at": "2014-01-17 16:07:30",
            "id": 65110,
            "launched_at": "2014-01-17 16:06:54"
          },
          {
            "raw": 14615248,
            "instance": "3fd6797d-bc35-42d9-ad85-157a2ea93023",
            "deleted_at": "2014-01-17 16:05:23",
            "id": 65108,
            "launched_at": "2014-01-17 16:05:00"
          }
        ]
      }

db/usage/glance/deletes/
========================

.. http:get:: http://example.com/db/usage/glance/deletes/

  Returns a list of image deletes matching provided query criteria.

  **Query Parameters**

  * ``deleted_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``limit``: int, default: 50, max: 1000
  * ``offset``: int, default: 0

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/glance/deletes/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "deletes":
        [
          {
            "raw": 300523,
            "deleted_at": "2014-01-17 15:28:18.154927",
            "id": 3169,
            "uuid": "f8b02f0e-b392-40f5-9d39-0458ae6ebfb3"
          },
          {
            "raw": 300512,
            "deleted_at": "2014-01-17 14:28:20.544617",
            "id": 3168,
            "uuid": "4c9dc0be-856b-4e98-81a5-1b63df108e7d"
          }
        ]
      }

db/usage/deletes/<delete_id>/
=============================

.. http:get:: http://example.com/db/usage/deletes/

Deprecated, see: :ref:`dbapi-nova-delete`

.. _dbapi-nova-delete:

db/usage/nova/deletes/<delete_id>/
==================================

.. http:get:: http://example.com/db/usage/nova/deletes/<deleted_id>

Returns the single instance delete with id matching the provided id.

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/nova/deletes/65110/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "delete":
        {
          "raw": 14615347,
          "instance": "b36a8c2d-af88-4371-b14c-14dadf7073e5",
          "deleted_at": "2014-01-17 16:07:30",
          "id": 65110,
          "launched_at": "2014-01-17 16:06:54"
        }
      }

db/usage/glance/deletes/<delete_id>/
====================================

.. http:get:: http://example.com/db/usage/glance/deletes/<deleted_id>

Returns the single image delete with id matching the provided id.

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/glance/deletes/3168/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "delete":
        {
          "raw": 300512,
          "deleted_at": "2014-01-17 14:28:20.544617",
          "id": 3168,
          "uuid": "4c9dc0be-856b-4e98-81a5-1b63df108e7d"
        }
      }

db/usage/exists/
================

.. http:get:: http://example.com/db/usage/exists/

Deprecated, see: :ref:`dbapi-nova-exists`

.. _dbapi-nova-exists:

db/usage/nova/exists/
=====================

.. http:get:: http://example.com/db/usage/nova/exists/

  Returns a list of instance exists matching provided query criteria.

  **Query Parameters**

  * ``audit_period_beginning_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``audit_period_beginning_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``audit_period_ending_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``audit_period_ending_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``launched_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``launched_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``received_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``received_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``instance``: uuid
  * ``limit``: int, default: 50, max: 1000
  * ``offset``: int, default: 0

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/nova/exists/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "exists":
        [
          {
            "status": "verified",
            "os_distro": "org.centos",
            "bandwidth_public_out": 0,
            "received": "2014-01-17 16:16:43.695474",
            "instance_type_id": "2",
            "raw": 14615544,
            "os_architecture": "x64",
            "rax_options": "0",
            "audit_period_ending": "2014-01-17 16:16:43",
            "deleted_at": null,
            "id": 135106,
            "tenant": "5889124",
            "audit_period_beginning": "2014-01-17 00:00:00",
            "fail_reason": null,
            "instance": "978b32ea-374b-48c6-814b-bb6151e2fb5c",
            "instance_flavor_id": "2",
            "launched_at": "2014-01-17 16:16:09",
            "os_version": "6.0",
            "usage": 91932,
            "send_status": 201,
            "message_id": "9d28fa15-d163-40c7-8195-2853ad13179b",
            "delete": null
          },
          {
            "status": "verified",
            "os_distro": "org.centos",
            "bandwidth_public_out": 0,
            "received": "2014-01-17 16:10:42.112505",
            "instance_type_id": "2",
            "raw": 14615459,
            "os_architecture": "x64",
            "rax_options": "0",
            "audit_period_ending": "2014-01-17 16:10:42",
            "deleted_at": null,
            "id": 135105,
            "tenant": "5824940",
            "audit_period_beginning": "2014-01-17 00:00:00",
            "fail_reason": null,
            "instance": "860b5df0-d58b-498d-8838-7156d701732c",
            "instance_flavor_id": "2",
            "launched_at": "2014-01-17 16:10:08",
            "os_version": "5.9",
            "usage": 91937,
            "send_status": 201,
            "message_id": "0a6b1c58-8443-4788-ac08-05cd03e6be53",
            "delete": null
          }
        ]
      }

db/usage/glance/exists/
=======================

.. http:get:: http://example.com/db/usage/glance/exists/

  Returns a list of instance exists matching provided query criteria.

  **Query Parameters**

  * ``audit_period_beginning_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``audit_period_beginning_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``audit_period_ending_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``audit_period_ending_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``created_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``created_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``deleted_at_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``received_min``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``received_max``: datetime (yyyy-mm-dd hh:mm:ss)
  * ``limit``: int, default: 50, max: 1000
  * ``offset``: int, default: 0

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/glance/exists/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "exists":
        [
          {
            "status": "verified",
            "audit_period_beginning": "2014-01-13 00:00:00",
            "fail_reason": null,
            "uuid": "d39a04bd-6ba0-4d20-8591-937ab43897dc",
            "usage": 2553,
            "created_at": "2013-05-11 15:37:34",
            "size": 11213393920,
            "owner": "389886",
            "message_id": "9c5fd5af-60b4-45ad-b524-c4a9964f31e4",
            "raw": 283303,
            "audit_period_ending": "2014-01-13 23:59:59",
            "received": "2014-01-13 09:20:02.777965",
            "deleted_at": null,
            "send_status": 0,
            "id": 5301,
            "delete": null
          },
          {
            "status": "verified",
            "audit_period_beginning": "2014-01-13 00:00:00",
            "fail_reason": null,
            "uuid": "6713c136-0555-4a93-b726-edb181d4b69e",
            "usage": 1254,
            "created_at": "2013-05-11 15:37:56",
            "size": 11254732800,
            "owner": "389886",
            "message_id": "9c5fd5af-60b4-45ad-b524-c4a9964f31e4",
            "raw": 283303,
            "audit_period_ending": "2014-01-13 23:59:59",
            "received": "2014-01-13 09:20:02.777965",
            "deleted_at": null,
            "send_status": 0,
            "id": 5300,
            "delete": null
          }
        ]
      }

db/usage/exists/<exist_id>/
===========================

.. http:get:: http://example.com/db/usage/exists/<exist_id>

Deprecated, see: :ref:`dbapi-nova-exist`

.. _dbapi-nova-exist:

db/usage/nova/exists/<exist_id>/
================================

.. http:get:: http://example.com/db/usage/nova/exists/<exist_id>

  Returns a single instance exists matching provided id

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/nova/exists/135105/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "exist":
        {
          "status": "verified",
          "os_distro": "org.centos",
          "bandwidth_public_out": 0,
          "received": "2014-01-17 16:10:42.112505",
          "instance_type_id": "2",
          "raw": 14615459,
          "os_architecture": "x64",
          "rax_options": "0",
          "audit_period_ending": "2014-01-17 16:10:42",
          "deleted_at": null,
          "id": 135105,
          "tenant": "5824940",
          "audit_period_beginning": "2014-01-17 00:00:00",
          "fail_reason": null,
          "instance": "860b5df0-d58b-498d-8838-7156d701732c",
          "instance_flavor_id": "2",
          "launched_at": "2014-01-17 16:10:08",
          "os_version": "5.9",
          "usage": 91937,
          "send_status": 201,
          "message_id": "0a6b1c58-8443-4788-ac08-05cd03e6be53",
          "delete": null
        }
      }

db/usage/glance/exists/<exist_id>/
==================================

.. http:get:: http://example.com/db/usage/glance/exists/<exist_id>/

  Returns a single instance exists matching provided id

  **Example request**:

   .. sourcecode:: http

      GET /db/usage/glance/exists/5300/ HTTP/1.1
      Host: example.com
      Accept: application/json

  **Example response**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Vary: Accept
      Content-Type: application/json

      {
        "exist":
        {
          "status": "verified",
          "audit_period_beginning": "2014-01-13 00:00:00",
          "fail_reason": null,
          "uuid": "6713c136-0555-4a93-b726-edb181d4b69e",
          "usage": 1254,
          "created_at": "2013-05-11 15:37:56",
          "size": 11254732800,
          "owner": "389886",
          "message_id": "9c5fd5af-60b4-45ad-b524-c4a9964f31e4",
          "raw": 283303,
          "audit_period_ending": "2014-01-13 23:59:59",
          "received": "2014-01-13 09:20:02.777965",
          "deleted_at": null,
          "send_status": 0,
          "id": 5300,
          "delete": null
        }
      }