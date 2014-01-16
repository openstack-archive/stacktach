
StackTach Usage Verification
############################

Usage Basics
************
In OpenStack, usage is tracked through notifications. The notifications are emitted by each service as users request changes and each service performs those changes. Services like Nova can also be configured to emitted periodic audit notifications exposing the state of the database at the time of the audit. The periodic audit notifications are useful for billing as it is not necessary to store past states.

But, we want to be sure what we're billing for is correct and that we've received audit notifications for every instance that should be billable. Thus, it is a good idea to track instance state so that periodic audit notifications can be validated against that state. The notifications each service sends as changes are requested and performed are extremely useful for tracking instance state through different billable states.

The idea behind StackTach's Usage Verification is to track changes through instantaneous notifications, then compare them to the periodic audit notifications for correctness. After being validated, StackTach itself will emit a copy of the notification with a new event_type indicating that is has been verified. StackTach also provides a set of scripts which can be used to confirm that exists were sent for all instances in a billable state.

Configuring Usage Verification
******************************
Usage Verification in StackTach is done by a separate verifier process. A sample configuration file can be found at ``./etc/sample_stacktach_verifier_config.sjon``

The default config provides most all settings that are required for the verifier. ::

    {
        "tick_time": 30,
        "settle_time": 5,
        "settle_units": "minutes",
        "pool_size": 2,
        "enable_notifications": true,
        "validation_level": "all",
        "flavor_field_name": "instance_type_id",
        "rabbit": {
            "durable_queue": false,
            "host": "10.0.0.1",
            "port": 5672,
            "userid": "rabbit",
            "password": "rabbit",
            "virtual_host": "/",
            "topics": {
                "nova": ["notifications.info"],
                "glance": ["notifications.info"]
            }
        }
    }

* tick_time: Time in seconds to sleep before attempting to retrieve pending usage entries for verifications
* settle_time: Amount of time between when a usage notification was emitted and when it should be picked up for verification.
* settle_units: Units for the settle_time value
* pool_size: Amount of verifier processes to create for the verifier pool.
* enable_notifications: Whether or not to emit verified notifications.
* validation_level: Determines how strict datatype validation will be on usage notifications. Values are ``none``, ``basic``, and ``all``.
* flavor_field_name: Field to use for flavor verification. Values are ``instance_type_id`` and ``instance_flavor_id``.
* rabbit: Rabbit config, please see :ref:`StackTach install guide <stacktach-config-files>` for rabbit config details.

 * The topics here are how the verifier determines which services to verify. For example, Nova and Glance services will be verified and verified notifications will be emitted with a routing_key of notifications.info with our sample config.
 * An alternate config that would only verify Nova and emit verified notifications on notifications.info and monitor.info: ::

      "topics": {
          "nova": ["notifications.info", "monitor.info"]
      }

* Other Config Options:

 * nova_event_type: Event type to emit for Nova events

  * Default: compute.instance.exists.verified.old

 * glance_event_type: Event type to emit for Glance events

  * Default: image.exists.verified.old

Starting the Verifier
*********************

``./verifier/start_verifier.py`` will spawn a verifier.py process for each service being verified along with a pool of processes to verify each usage entry.

Audit Reports
*************

StackTach also provides a few reports for auditing the audit notifications, which can be useful for confirming all usage was sent for a deployment.

* ``./reports/nova_usage_audit.py``

 * Suggested Arguments:
 * --period_length: ``day`` or ``year``, default: ``day``
 * --utcdatetime: Overrides datetime used to audit, default: current utc datetime
 * --store: ``True`` or ``False``, whether or not to store report in StackTach database

* ``./reports/glance_usage_audit``

 * Suggested Arguments:
 * --period_length: ``day`` or ``year``, default: ``day``
 * --utcdatetime: Overrides datetime used to audit, default: current utc datetime
 * --store: ``True`` or ``False``, whether or not to store report in StackTach database