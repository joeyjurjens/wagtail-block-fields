"""
StructField and ListField for Wagtail.

API based on how StreamField wraps StreamBlock:
https://github.com/wagtail/wagtail/blob/main/wagtail/fields.py
https://github.com/wagtail/wagtail/blob/main/wagtail/blocks/stream_block.py
"""

import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.functional import cached_property

from wagtail.blocks import Block, BlockField, ListBlock, StructBlock
from wagtail.blocks.definition_lookup import (
    BlockDefinitionLookup,
    BlockDefinitionLookupBuilder,
)
from wagtail.blocks.list_block import ListValue
from wagtail.blocks.struct_block import StructValue
from wagtail.fields import Creator


class _ListBlock(ListBlock):
    """Fixes missing form data handling for nested blocks."""

    def value_from_datadict(self, data, files, prefix):
        if self.value_omitted_from_data(data, files, prefix):
            return self.get_default()
        return super().value_from_datadict(data, files, prefix)


class _StructBlock(StructBlock):
    """Fixes missing form data handling for nested blocks."""

    def value_from_datadict(self, data, files, prefix):
        return self._to_struct_value(
            [
                (
                    name,
                    (
                        block.value_from_datadict(data, files, f"{prefix}-{name}")
                        if not block.value_omitted_from_data(data, files, f"{prefix}-{name}")
                        else block.get_default()
                    ),
                )
                for name, block in self.child_blocks.items()
            ]
        )


class BaseBlockField(models.Field):
    def __init__(self, block_lookup=None, **kwargs):
        self.block_lookup = block_lookup
        super().__init__(**kwargs)

    @cached_property
    def block(self):
        raise NotImplementedError

    def empty_value(self):
        raise NotImplementedError

    def _get_block_from_arg(self, block_arg):
        has_block_lookup = self.block_lookup is not None
        if has_block_lookup:
            lookup = BlockDefinitionLookup(self.block_lookup)

        if isinstance(block_arg, Block):
            return block_arg
        elif isinstance(block_arg, int) and has_block_lookup:
            return lookup.get_block(block_arg)
        elif isinstance(block_arg, type) and issubclass(block_arg, Block):
            return block_arg()
        return None

    @property
    def json_field(self):
        return models.JSONField(encoder=DjangoJSONEncoder)

    def get_internal_type(self):
        return "JSONField"

    def get_lookup(self, lookup_name):
        return self.json_field.get_lookup(lookup_name)

    def get_transform(self, lookup_name):
        return self.json_field.get_transform(lookup_name)

    def get_db_prep_value(self, value, connection, prepared=False):
        if not prepared:
            value = self.get_prep_value(value)
        return self.json_field.get_db_prep_value(value, connection=connection, prepared=True)

    def from_db_value(self, value, expression, connection):
        value = self.json_field.from_db_value(value, expression, connection)
        return self.to_python(value)

    def formfield(self, **kwargs):
        defaults = {"form_class": BlockField, "block": self.block}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return json.dumps(self.get_prep_value(value), cls=self.json_field.encoder)

    def get_searchable_content(self, value):
        return self.block.get_searchable_content(value)

    def extract_references(self, value):
        yield from self.block.extract_references(value)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self.block.check(field=self, **kwargs))
        return errors

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.name, Creator(self))


class StructField(BaseBlockField):
    def __init__(self, block_type, block_lookup=None, **kwargs):
        self.block_type_arg = block_type
        super().__init__(block_lookup=block_lookup, **kwargs)

    @cached_property
    def block(self):
        block = self._get_block_from_arg(self.block_type_arg)

        if block is None:
            if isinstance(self.block_type_arg, list):
                has_block_lookup = self.block_lookup is not None
                if has_block_lookup:
                    lookup = BlockDefinitionLookup(self.block_lookup)

                child_blocks = []
                for name, child_block in self.block_type_arg:
                    if isinstance(child_block, int) and has_block_lookup:
                        child_blocks.append((name, lookup.get_block(child_block)))
                    else:
                        child_blocks.append((name, child_block))
                block = _StructBlock(child_blocks)
            else:
                raise TypeError(
                    f"StructField requires a StructBlock instance, class, or list of "
                    f"(name, block) tuples, got {type(self.block_type_arg).__name__}"
                )

        if not isinstance(block, StructBlock):
            raise TypeError(f"StructField requires a StructBlock, got {type(block).__name__}")

        if not isinstance(block, _StructBlock):
            block = _StructBlock(list(block.child_blocks.items()))

        return block

    @property
    def struct_block(self):
        return self.block

    def empty_value(self):
        return self.block.get_default()

    def get_default(self):
        return self.block.get_default()

    def deconstruct(self):
        name, path, _, kwargs = super().deconstruct()
        lookup = BlockDefinitionLookupBuilder()
        block_types = [
            (child_name, lookup.add_block(child_block))
            for child_name, child_block in self.block.child_blocks.items()
        ]
        args = [block_types]
        kwargs["block_lookup"] = lookup.get_lookup_as_dict()
        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return self.block.get_default()
        if isinstance(value, StructValue):
            return value
        if isinstance(value, str) and value:
            try:
                value = json.loads(value)
            except ValueError:
                return self.block.get_default()
        if isinstance(value, dict):
            return self.block.to_python(value)
        return self.block.get_default()

    def get_prep_value(self, value):
        if value is None:
            return {}
        if isinstance(value, StructValue):
            return self.block.get_prep_value(value)
        if isinstance(value, dict):
            return value
        return {}


class ListField(BaseBlockField):
    def __init__(self, child_block, block_lookup=None, **kwargs):
        self.block_opts = {}
        for arg in ["min_num", "max_num"]:
            if arg in kwargs:
                self.block_opts[arg] = kwargs.pop(arg)

        self.child_block_arg = child_block
        super().__init__(block_lookup=block_lookup, **kwargs)

    @cached_property
    def block(self):
        child_block = self._get_block_from_arg(self.child_block_arg)

        if child_block is None:
            raise TypeError(
                f"ListField requires a Block instance or class, "
                f"got {type(self.child_block_arg).__name__}"
            )

        block = _ListBlock(child_block)
        block.set_meta_options(self.block_opts)
        return block

    @property
    def list_block(self):
        return self.block

    def empty_value(self):
        return self.block.empty_value()

    def get_default(self):
        return self.block.empty_value()

    def deconstruct(self):
        name, path, _, kwargs = super().deconstruct()
        lookup = BlockDefinitionLookupBuilder()
        block_id = lookup.add_block(self.block.child_block)
        args = [block_id]
        kwargs["block_lookup"] = lookup.get_lookup_as_dict()
        return name, path, args, kwargs

    def to_python(self, value):
        if value is None:
            return self.block.empty_value()
        if isinstance(value, ListValue):
            return value
        if isinstance(value, str) and value:
            try:
                value = json.loads(value)
            except ValueError:
                return self.block.empty_value()
        if isinstance(value, list):
            return self.block.to_python(value)
        return self.block.empty_value()

    def get_prep_value(self, value):
        if value is None:
            return []
        if isinstance(value, ListValue):
            return self.block.get_prep_value(value)
        if isinstance(value, list):
            return self.block.get_prep_value(self.block.normalize(value))
        return []
