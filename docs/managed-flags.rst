.. _automatic-flags:

Automatic Flags
===============

The reactive framework will automatically set some flags for your charm,
based on lifecycle events from Juju.  These flags can inform your charm
of things such as upgrades, config changes, relation activity, etc.

With a few exceptions, noted below, these flags will be set by the framework
but it is up to your charm to clear them, if need be.  To avoid conflicts
between layers, it is recommended that only the top-level charm layer (or
interface layer, in the case of endpoint flags) use any of the automatic flags
directly; any base layer should instead use
:func:`~charms.reactive.flags.register_trigger` to "wrap" the automatic flag
with a layer-specific flag that can be safely used within that layer.

It is worth mentioning that any set flag will execute on every hook run as
long as it stays set. This means that code inside a function wrapped in,
for example, ``endpoint.{endpoint_name}.joined`` will run every time hooks
run when .joined is true. This could be due to something completely unrelated
such as relation data changing or even an update-status hook. It is best
not to rely on such things due to the obfusificative nature of the code as
it makes it harder for someone to reason about, but it is a good point to
remember.

The flags that are set by the framework are:

+----------------------------------------------+------------------------------------------------------------+
| ``upgrade.series.in-progress``               | This is set when the operator is about to start an OS      |
|                                              | upgrade, and removed after the operator has completed the  |
|                                              | upgrade.  See :doc:`series-upgrade` for more information.  |
+----------------------------------------------+------------------------------------------------------------+
| ``config.changed``                           | This is set when any config option has changed. [1]_       |
+----------------------------------------------+------------------------------------------------------------+
| ``config.changed.{option_name}``             | This is set for each config option that has changed. [1]_  |
+----------------------------------------------+------------------------------------------------------------+
| ``config.set.{option_name}``                 | This is set for each config option whose value is not      |
|                                              | ``None``, ``False``, or an empty string. [1]_              |
+----------------------------------------------+------------------------------------------------------------+
| ``config.default.{option_name}``             | This is set for each config option whose value is equal to |
|                                              | its default value, and cleared if it has been changed. [1]_|
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.is_leader``                     | This is set when the unit is the leader. The unit will     |
|                                              | remain the leader for the remainder of the hook, but       |
|                                              | may not be leader in future hooks. [2]_                    |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.changed``                       | This is set when any leadership setting has changed. [2]_  |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.changed.{setting_name}``        | This is set for each leadership setting that has           |
|                                              | changed. [2]_                                              |
+----------------------------------------------+------------------------------------------------------------+
| ``leadership.set.{setting_name}``            | This is set for each leadership setting that has been      |
|                                              | to set to a value other than ``None``. [2]_                |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.joined``          | This is set when a relation is joined on an endpoint. [3]_ |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.changed``         | This is set when relation data has changed. [3]_           |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.changed.{field}`` | This is set for each field of relation data which has      |
|                                              | changed. [3]_                                              |
+----------------------------------------------+------------------------------------------------------------+
| ``endpoint.{endpoint_name}.departed``        | This is set when a unit leaves a relation. [3]_            |
+----------------------------------------------+------------------------------------------------------------+

.. [1]

The ``config.*`` flags are currently managed by :doc:`the base layer
<layer-basic>` and are automatically cleared a the end of the hook context in
which they were set.  However, this is expected to change in the future, with
the flags being set by this library instead and the automatic clearing behavior
changed or removed.

.. [2]

The ``leadership.*`` flags are currently managed by `the leadership layer
<https://git.launchpad.net/layer-leadership/>`_ and the ``leadership.changed*``
flags are automatically cleared at the end of the hook context in which they
were set.  If this layer is not included by the charm or one of its base
layers, these flags will not be set.  However, this is expected to change in
the future, with the flags being managed by this library instead and the
automatic clearing behavior changed or removed.

.. [3]

See :class:`~charms.reactive.endpoints.Endpoint` for more information
on the ``endpoint.{endpoint_name}.*`` flags.  The
``endpoint.{endpoint_name}.joined`` flag is automatically cleared when
appropriate.
