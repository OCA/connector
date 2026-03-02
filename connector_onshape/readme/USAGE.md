## Import Documents

Click **Import Documents** on the backend form to fetch all Onshape
documents from your Onshape account. Documents are created with their elements
(part studios, assemblies, drawings).

## Import Products

Click **Import Products** to scan all part studio elements and create
product bindings. The module uses a 4-strategy matching algorithm:

1. **Exact filename**: Part name matches an Odoo product SKU
2. **Part number**: Onshape Part Number metadata matches an Odoo SKU
3. **McMaster catalog**: Extracted catalog numbers (e.g., 90185A632) match
4. **Case-insensitive**: Fallback case-insensitive match

Unmatched parts will be auto-created as products if configured.

## Import BOMs

Click **Import BOMs** to fetch assembly BOMs from Onshape and create
`mrp.bom` records. Each BOM includes a **match score** indicating
what percentage of Onshape components were matched to Odoo products.

## Export Part Numbers

Click **Export Part Numbers** to push Odoo product SKUs and names
back to Onshape. This writes the `default_code` as "Part Number"
and `name` as "Description" in Onshape metadata.

## Automatic Export

When a product's `default_code` or `name` is changed in Odoo,
a background job is automatically queued to export the update to
Onshape (if the product is bound to an Onshape part).

## Import Wizard

Use **Onshape > Onshape Data > Import from Onshape** for a guided
import process with options for documents-only, documents+products,
or full sync including BOMs.
