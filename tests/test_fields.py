import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from wagtail.blocks import CharBlock, IntegerBlock, StructBlock
from wagtail.blocks.list_block import ListValue
from wagtail.blocks.struct_block import StructValue
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtail.models import Page
from wagtail_block_fields import ListField, StructField

from PIL import Image as PILImage

from .testapp.models import (
    AddressBlock,
    ChooserTestModel,
    NestedTestModel,
    StreamBlockTestModel,
    TestModel,
)


def create_test_image(name="test.png"):
    img_io = io.BytesIO()
    PILImage.new("RGB", (100, 100), color="red").save(img_io, format="PNG")
    img_io.seek(0)
    return Image.objects.create(
        title=name,
        file=SimpleUploadedFile(name, img_io.read(), content_type="image/png"),
    )


def create_test_document(name="test.pdf"):
    return Document.objects.create(
        title=name,
        file=SimpleUploadedFile(name, b"PDF content", content_type="application/pdf"),
    )


class StructFieldTests(TestCase):
    def test_init_with_block_instance(self):
        field = StructField(AddressBlock())
        self.assertIsInstance(field.block, StructBlock)

    def test_init_with_block_class(self):
        field = StructField(AddressBlock)
        self.assertIsInstance(field.block, StructBlock)

    def test_init_with_inline_blocks(self):
        field = StructField(
            [
                ("name", CharBlock()),
                ("age", IntegerBlock()),
            ]
        )
        self.assertIn("name", field.block.child_blocks)
        self.assertIn("age", field.block.child_blocks)

    def test_to_python_with_dict(self):
        field = StructField(AddressBlock())
        value = field.to_python({"street": "123 Main St", "city": "Amsterdam"})
        self.assertIsInstance(value, StructValue)
        self.assertEqual(value["street"], "123 Main St")

    def test_to_python_with_none(self):
        field = StructField(AddressBlock())
        value = field.to_python(None)
        self.assertIsInstance(value, StructValue)

    def test_to_python_with_json_string(self):
        field = StructField(AddressBlock())
        value = field.to_python('{"street": "123 Main St", "city": "Amsterdam"}')
        self.assertEqual(value["street"], "123 Main St")

    def test_get_prep_value(self):
        field = StructField(AddressBlock())
        struct_value = field.to_python({"street": "123 Main St", "city": "Amsterdam"})
        prep = field.get_prep_value(struct_value)
        self.assertEqual(prep["street"], "123 Main St")

    def test_get_prep_value_with_none(self):
        field = StructField(AddressBlock())
        self.assertEqual(field.get_prep_value(None), {})

    def test_deconstruct(self):
        field = StructField(AddressBlock())
        name, path, args, kwargs = field.deconstruct()
        self.assertIn("block_lookup", kwargs)
        self.assertIsInstance(args[0], list)

    def test_save_and_load(self):
        obj = TestModel.objects.create(
            name="Test",
            address={"street": "123 Main St", "city": "Amsterdam"},
        )
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertIsInstance(loaded.address, StructValue)
        self.assertEqual(loaded.address["city"], "Amsterdam")

    def test_update(self):
        obj = TestModel.objects.create(
            name="Test",
            address={"street": "Old Street", "city": "Old City"},
        )
        obj.address = {"street": "New Street", "city": "New City"}
        obj.save()
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.address["street"], "New Street")

    def test_render_as_block(self):
        obj = TestModel.objects.create(
            name="Test", address={"street": "123 Main St", "city": "Amsterdam"}
        )
        loaded = TestModel.objects.get(pk=obj.pk)
        html = loaded.address.render_as_block()
        self.assertIn("123 Main St", html)

    def test_bound_blocks(self):
        obj = TestModel.objects.create(
            name="Test", address={"street": "123 Main St", "city": "Amsterdam"}
        )
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.address.bound_blocks["street"].value, "123 Main St")

    def test_image_chooser(self):
        image = create_test_image()
        obj = ChooserTestModel.objects.create(
            name="Test", hero={"title": "Hero", "image": image.pk}
        )
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.hero["image"], image)

    def test_richtext(self):
        obj = ChooserTestModel.objects.create(
            name="Test",
            hero={"title": "Hello", "description": "<p>Rich text</p>"},
        )
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        self.assertIn("Rich text", loaded.hero["description"].source)

    def test_extract_references(self):
        image = create_test_image()
        obj = ChooserTestModel.objects.create(
            name="Test", hero={"title": "Test", "image": image.pk}
        )
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        refs = list(ChooserTestModel._meta.get_field("hero").extract_references(loaded.hero))
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0][0], Image)
        self.assertEqual(refs[0][1], str(image.pk))

    def test_searchable_content(self):
        field = TestModel._meta.get_field("address")
        value = field.to_python({"street": "123 Main St", "city": "Amsterdam"})
        content = field.get_searchable_content(value)
        self.assertIn("123 Main St", content)
        self.assertIn("Amsterdam", content)

    def test_nested_struct_in_struct(self):
        obj = NestedTestModel.objects.create(
            name="Test",
            nested_addresses={
                "primary": {"street": "123 Main", "city": "Amsterdam"},
                "secondary": {"street": "456 Oak", "city": "Rotterdam"},
            },
        )
        loaded = NestedTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.nested_addresses["primary"]["city"], "Amsterdam")
        self.assertEqual(loaded.nested_addresses["secondary"]["city"], "Rotterdam")

    def test_nested_streamblock_empty(self):
        obj = StreamBlockTestModel.objects.create(name="Test")
        loaded = StreamBlockTestModel.objects.get(pk=obj.pk)
        self.assertIsNone(loaded.section["heading"])
        self.assertEqual(len(loaded.section["content"]), 0)

    def test_nested_streamblock_with_data(self):
        obj = StreamBlockTestModel.objects.create(
            name="Test",
            section={
                "heading": "My Section",
                "content": [
                    {"type": "paragraph", "value": "<p>Hello</p>"},
                ],
            },
        )
        loaded = StreamBlockTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.section["heading"], "My Section")
        self.assertEqual(len(loaded.section["content"]), 1)


class ListFieldTests(TestCase):
    def test_init_with_block_instance(self):
        field = ListField(CharBlock())
        self.assertIsInstance(field.block.child_block, CharBlock)

    def test_init_with_block_class(self):
        field = ListField(CharBlock)
        self.assertIsInstance(field.block.child_block, CharBlock)

    def test_init_with_min_max(self):
        field = ListField(CharBlock(), min_num=1, max_num=5)
        self.assertEqual(field.block.meta.min_num, 1)
        self.assertEqual(field.block.meta.max_num, 5)

    def test_to_python_with_list(self):
        field = ListField(CharBlock())
        value = field.to_python(
            [
                {"type": "item", "value": "one", "id": "a"},
                {"type": "item", "value": "two", "id": "b"},
            ]
        )
        self.assertIsInstance(value, ListValue)
        self.assertEqual(value[0], "one")
        self.assertEqual(value[1], "two")

    def test_to_python_with_none(self):
        field = ListField(CharBlock())
        value = field.to_python(None)
        self.assertEqual(len(value), 0)

    def test_get_prep_value(self):
        field = ListField(CharBlock())
        list_value = field.to_python([{"type": "item", "value": "one", "id": "a"}])
        prep = field.get_prep_value(list_value)
        self.assertEqual(prep[0]["value"], "one")

    def test_get_prep_value_with_none(self):
        field = ListField(CharBlock())
        self.assertEqual(field.get_prep_value(None), [])

    def test_deconstruct(self):
        field = ListField(CharBlock())
        name, path, args, kwargs = field.deconstruct()
        self.assertIn("block_lookup", kwargs)
        self.assertIsInstance(args[0], int)

    def test_save_and_load(self):
        obj = TestModel.objects.create(name="Test", tags=["python", "django", "wagtail"])
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertIsInstance(loaded.tags, ListValue)
        self.assertEqual(loaded.tags[0], "python")

    def test_save_and_load_list_of_structs(self):
        obj = TestModel.objects.create(
            name="Test",
            addresses=[
                {"street": "123 Main", "city": "Amsterdam"},
                {"street": "456 Oak", "city": "Rotterdam"},
            ],
        )
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.addresses[0]["city"], "Amsterdam")

    def test_save_and_load_empty(self):
        obj = TestModel.objects.create(name="Test", tags=[])
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertEqual(len(loaded.tags), 0)

    def test_update(self):
        obj = TestModel.objects.create(name="Test", tags=["old"])
        obj.tags = ["new", "tags"]
        obj.save()
        loaded = TestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.tags[0], "new")

    def test_append(self):
        obj = TestModel.objects.create(name="Test", tags=["one"])
        loaded = TestModel.objects.get(pk=obj.pk)
        loaded.tags.append("two")
        loaded.save()
        reloaded = TestModel.objects.get(pk=obj.pk)
        self.assertEqual(reloaded.tags[1], "two")

    def test_render(self):
        obj = TestModel.objects.create(name="Test", tags=["python", "django"])
        loaded = TestModel.objects.get(pk=obj.pk)
        html = loaded.tags.list_block.render(loaded.tags)
        self.assertIn("python", html)

    def test_image_chooser(self):
        images = [create_test_image(f"test{i}.png") for i in range(2)]
        obj = ChooserTestModel.objects.create(name="Test", gallery=[img.pk for img in images])
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.gallery[0], images[0])
        self.assertEqual(loaded.gallery[1], images[1])

    def test_document_chooser(self):
        doc = create_test_document()
        obj = ChooserTestModel.objects.create(name="Test", attachments=[doc.pk])
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.attachments[0], doc)

    def test_page_chooser(self):
        root = Page.objects.get(depth=1)
        page = root.add_child(instance=Page(title="Test Page", slug="test-page"))
        obj = ChooserTestModel.objects.create(name="Test", related_pages=[page.pk])
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.related_pages[0], page)

    def test_extract_references(self):
        images = [create_test_image(f"ref{i}.png") for i in range(2)]
        obj = ChooserTestModel.objects.create(name="Test", gallery=[img.pk for img in images])
        loaded = ChooserTestModel.objects.get(pk=obj.pk)
        refs = list(ChooserTestModel._meta.get_field("gallery").extract_references(loaded.gallery))
        self.assertEqual(len(refs), 2)

    def test_searchable_content(self):
        field = TestModel._meta.get_field("tags")
        value = field.to_python(["python", "django", "wagtail"])
        content = field.get_searchable_content(value)
        self.assertIn("python", content)
        self.assertIn("wagtail", content)

    def test_validation_min_num(self):
        field = ListField(CharBlock(), min_num=2)
        with self.assertRaises(ValidationError):
            field.block.clean([{"type": "item", "value": "one", "id": "a"}])

    def test_validation_max_num(self):
        field = ListField(CharBlock(), max_num=2)
        with self.assertRaises(ValidationError):
            field.block.clean(
                [
                    {"type": "item", "value": "one", "id": "a"},
                    {"type": "item", "value": "two", "id": "b"},
                    {"type": "item", "value": "three", "id": "c"},
                ]
            )

    def test_list_of_lists(self):
        obj = NestedTestModel.objects.create(
            name="Test",
            address_groups=[
                [
                    {"street": "123 Main", "city": "Amsterdam"},
                    {"street": "456 Oak", "city": "Rotterdam"},
                ],
            ],
        )
        loaded = NestedTestModel.objects.get(pk=obj.pk)
        self.assertEqual(loaded.address_groups[0][0]["city"], "Amsterdam")
