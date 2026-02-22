# Background themes for base_state

- Every file in this folder describes one visual background preset.
- `settings.json` controls active preset via `base_background_id` (1, 2, 3...).
- Add a new `theme-N.css` and map `N` in `states/base_backgrounds/catalog.py`.
- Existing markup/animations stay compatible, so future animated redesigns can be introduced without touching state logic.
