from django.db import models

from wagtail.blocks import CharBlock, ListBlock, RichTextBlock, StreamBlock, StructBlock
from wagtail.blocks.field_block import PageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail_block_fields import ListField, StructField


class AddressBlock(StructBlock):
    street = CharBlock()
    city = CharBlock()
    postal_code = CharBlock(required=False)


class TestModel(models.Model):
    name = models.CharField(max_length=255)
    address = StructField(AddressBlock(), null=True, blank=True)
    contact = StructField(
        [
            ("email", CharBlock()),
            ("phone", CharBlock(required=False)),
        ],
        null=True,
        blank=True,
    )
    tags = ListField(CharBlock(), null=True, blank=True)
    addresses = ListField(AddressBlock(), null=True, blank=True)

    class Meta:
        app_label = "testapp"


class ChooserTestModel(models.Model):
    name = models.CharField(max_length=255)
    hero = StructField(
        [
            ("title", CharBlock()),
            ("description", RichTextBlock(required=False)),
            ("image", ImageChooserBlock(required=False)),
        ],
        null=True,
        blank=True,
    )
    gallery = ListField(ImageChooserBlock(), null=True, blank=True)
    attachments = ListField(DocumentChooserBlock(), null=True, blank=True)
    related_pages = ListField(PageChooserBlock(), null=True, blank=True)

    class Meta:
        app_label = "testapp"


class NestedTestModel(models.Model):
    name = models.CharField(max_length=255)
    nested_addresses = StructField(
        [
            ("primary", AddressBlock()),
            ("secondary", AddressBlock(required=False)),
        ],
        null=True,
        blank=True,
    )
    address_groups = ListField(ListBlock(AddressBlock()), null=True, blank=True)

    class Meta:
        app_label = "testapp"


class StreamBlockTestModel(models.Model):
    name = models.CharField(max_length=255)
    section = StructField(
        [
            ("heading", CharBlock()),
            (
                "content",
                StreamBlock(
                    [
                        ("paragraph", RichTextBlock()),
                        ("image", ImageChooserBlock()),
                    ]
                ),
            ),
        ],
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "testapp"
