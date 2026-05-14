# Monitorr-II

A Python rewrite of [Monitorr](https://github.com/Monitorr/Monitorr) — a self-hosted
service-status dashboard for homelabs. Same dark UI, same tile grid, with two
quality-of-life fixes:

- Pick service icons from a **dropdown** populated by an icons folder (no path pasting).
- Monitor **any number of drives** (the original was capped at 3).

## Run

```
docker compose up -d monitorr-ii
```

On first boot, if `/config/legacy/` is mounted and contains the original Monitorr
`services_settings-data.json` / `site_settings-data.json` / `user_preferences-data.json`,
they are migrated into `/config/monitorr.json` automatically.

## Auth

Set `MONITORR_PASSWORD` to gate the settings UI. Without it, settings is open
(useful behind SWAG / Tailscale only).

## Icons

Drop `*.png` / `*.jpg` / `*.svg` / `*.ico` into `/config/icons/` on the host and
they immediately appear in the icon dropdown. User icons shadow bundled ones of
the same filename.
