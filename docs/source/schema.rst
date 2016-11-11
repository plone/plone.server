Schema
======

``plone.server`` has its own schema inspired on dexterity but smaller and without dynamic schemas. 

They are not persistent in DB.

Utils
-----

Register a Schema Factory : FTI

.. code::
  <plone:contenttype
      portal_type="Item"
      schema=".types.IItem"
      class=".types.Item"
      behaviors=".behaviors.dublincore.IDublinCore"
    />

Get all fieldsets/behaviors of a schema

.. code::
  from 
  iterSchemataForType(portal_type)

Serialize schema to json

.. code::
  from plone.jsonserializer.interfaces import IFieldSerializer
  from plone.jsonserializer.interfaces import IFieldsetSerializer
  from plone.jsonserializer.interfaces import ISchemaSerializer
  from plone.jsonserializer.interfaces import ISerializeToJson
  from plone.jsonserializer.interfaces import ISerializeToJsonSummary

Deserialize schema from json

.. code::

  from plone.jsonserializer.interfaces import IDeserializeFromJson
  from plone.jsonserializer.exceptions import DeserializationError
  from plone.jsonserializer.interfaces import IFieldDeserializer


from plone.server.content.interfaces import IFormFieldProvider
mergedTaggedValueDict
sortedFields
iterSchemata
iterSchemataForType
from zope.schema import getFields

