# wagtail-block-fields

Use Wagtail's `StructBlock`, `ListBlock`, and `MultipleChoiceBlock` as standalone model fields.

Just like `StreamField` wraps `StreamBlock`, this package provides:
- **`StructField`** - wraps a `StructBlock`
- **`ListField`** - wraps a `ListBlock`
- **`MultipleChoiceField`** - wraps a `MultipleChoiceBlock`

## Installation

```bash
pip install wagtail-block-fields
```

## Usage

### StructField

```python
from wagtail.blocks import CharBlock, StructBlock
from wagtail_block_fields import StructField

class AddressBlock(StructBlock):
    street = CharBlock()
    city = CharBlock()
    postal_code = CharBlock()

class MyPage(Page):
    address = StructField(AddressBlock())
    
    contact = StructField([
        ('email', CharBlock()),
        ('phone', CharBlock()),
    ])
```

### ListField

```python
from wagtail.blocks import CharBlock
from wagtail_block_fields import ListField

class MyPage(Page):
    tags = ListField(CharBlock())
    categories = ListField(CharBlock(), min_num=1, max_num=5)
    addresses = ListField(AddressBlock())
```

### MultipleChoiceField

```python
from wagtail_block_fields import MultipleChoiceField

COLOR_CHOICES = [
    ("red", "Red"),
    ("green", "Green"),
    ("blue", "Blue"),
]

class MyPage(Page):
    colors = MultipleChoiceField(choices=COLOR_CHOICES)
```

### In templates

```html
<p>{{ page.address.street }}, {{ page.address.city }}</p>

<ul>
{% for tag in page.tags %}
    <li>{{ tag }}</li>
{% endfor %}
</ul>

<ul>
{% for color in page.colors %}
    <li>{{ color }}</li>
{% endfor %}
</ul>

{% for address in page.addresses %}
    <p>{{ address.street }}, {{ address.city }}</p>
{% endfor %}
```

## Why?

Sometimes you need structured JSON data in a single field without the complexity of StreamField. These fields:

- Store data as JSON in a single database column
- Provide full Wagtail admin editing UI
- Support validation, search indexing, and reference extraction
- Work with migrations just like StreamField
- Support nesting (e.g., `MultipleChoiceField` inside a `StructField`)

## License

MIT
