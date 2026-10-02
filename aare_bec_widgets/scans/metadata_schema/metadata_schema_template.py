# # By inheriting from BasicScanMetadata you can define a schema by which metadata
# # supplied to a scan must be validated.
# # This schema is a Pydantic model: https://docs.pydantic.dev/latest/concepts/models/
# # but by default it will still allow you to add any arbitrary information to it.
# # That is to say, when you run a scan with which such a model has been associated in the
# # metadata_schema_registry, you can supply any python dictionary with strings as keys
# # and built-in python types (strings, integers, floats) as values, and these will be
# # added to the experiment metadata, but it *must* contain the keys and values of the
# # types defined in the schema class.
# #
# #
# # For example, say that you would like to enforce recording information about sample
# # pretreatment, you could define the following:
# #
#
# from bec_lib.metadata_schema import BasicScanMetadata
#
#
# class ExampleSchema(BasicScanMetadata):
#    treatment_description: str
#    treatment_temperature_k: int
#
#
# # If this was used according to the example in metadata_schema_registry.py,
# # then when calling the scan, the user would need to write something like:
# >>> scans.example_scan(
# >>>     motor,
# >>>     1,
# >>>     2,
# >>>     3,
# >>>     metadata={"treatment_description": "oven overnight", "treatment_temperature_k": 575},
# >>> )
#
# # And the additional metadata would be saved in the HDF5 file created for the scan.
