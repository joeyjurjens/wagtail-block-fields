# wagtail-block-fields

Use Wagtail's `StructBlock` and `ListBlock` as standalone model fields.

Just like `StreamField` wraps `StreamBlock`, this package provides:
- **`StructField`** - wraps a `StructBlock`
- **`ListField`** - wraps a `ListBlock`

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

### In templates

```html
<p>{{ page.address.street }}, {{ page.address.city }}</p>

<ul>
{% for tag in page.tags %}
    <li>{{ tag }}</li>
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

## License

MIT
