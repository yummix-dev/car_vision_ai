# Category photos

Shown on the section cards of the "Что примеряем?" screen. Drop a file here and
name it in `app/data/catalog.yaml`:

```yaml
- id: rul
  label: Руль
  photo: rul.jpg          # -> web/img/categories/rul.jpg
```

Unlike product photos, these are **illustration only** — they are never sent to
the image model. They just need to make the section obvious at a glance.

Cropped to roughly 2:1 (the card strip is 78px tall and full card width), so a
wide shot works better than a square one. A missing file named here fails at
startup, same as everywhere else in the catalog.
