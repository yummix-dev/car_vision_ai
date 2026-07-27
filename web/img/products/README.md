# Product photos

Drop a photo here and name it in `app/data/catalog.yaml`:

```yaml
- id: amg
  name: Mercedes-AMG Performance
  photo: amg.jpg          # -> web/img/products/amg.jpg
```

A product with no `photo:` (e.g. `rs` / Carbon RS, awaiting a real shot) shows
the striped placeholder and falls back to describing the part in words.

The same file does two jobs: it replaces the striped placeholder on the catalog
card, and it is handed to the image model as a reference so the customer sees
**the part the shop actually stocks** rather than the model's idea of one.

What makes a good reference:

* the part alone, filling the frame, on a plain background;
* lit evenly, in focus, no heavy shadows;
* the angle a customer would see it from — for a steering wheel, straight on;
* JPEG or PNG, at least ~800px on the long side.

A watermark, a price tag or a busy background will be reproduced onto the
customer's car, so crop them out.

A name that points at a missing file fails at startup rather than silently
falling back — the shop should never believe customers are seeing a real part
while the model quietly invents one.
