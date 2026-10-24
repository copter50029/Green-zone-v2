# Work log — 2026-10-25

## Scope reviewed

Read the repository's source/configuration/docs (grid.py, README.md, .gitignore and license header), current Git diff/history, grid_index.csv header/sample and source metadata for Images/Theos00.tif, Theos01.tif and Theos02.tif. Dependencies in .venv and binary imagery were inspected as metadata, not counted as project source. This is the working clone at Documents/Codex/Green-zone-v2; the older clone under 2026-10-15/evi-ndvi is a separate checkout.

## Changes

- New branch nike/green-zone-functions from the existing main checkout.
- Preserved the user's uncommitted grid.py change (Theos2.tif -> Theos00.tif). No Nike edit to grid.py; local SHA256 before/after: c3601bb25c081cb92de6512d730c646139ec563d147cde858af44e9f975e20e4. Excluded grid.py from Nike commit.
- Reused previously tested standalone heatmap/park-review functions from the older Nike checkout; added a compact detector and run_nike.py integration example. No old HTTP server, ML models or frontend copied.
- Added cached public registry with snapshot date and source hash. No real review decision was created.
- Added Thai README/NIKE manual and ignores for environments, generated outputs and local config.
- Installed scipy in this clone's existing .venv; environments are ignored.

## Validation

20 synthetic unit/integration tests passed: detector classes and uint16 handling, NoData, exclusions, minimum patch area, fading colours, park evidence requirements, image-edge coverage, CRS/shape validation, GeoTIFF grid/alpha roundtrip and output overwrite protection. These are software tests, not semantic accuracy.

Ran the example on existing Theos00 tile_r7_c9.tif with experimental bands 3/4: 26,478.75 m2 candidate after filtering, 30 retained groups, 1 registry review task, 0 verified parks. Outputs remain local under Output/nike-preview-r7c9 and are not Git content.

## Limitations / next work

Band mapping/calibration still unverified; ratio detection alone cannot guarantee roof/private-garden rejection. No real labels/accuracy or automatic public-access verification. run_nike.py is a bounded raster example; complete-scene tiled inference and core merging remain the integration task before final patch filtering and whole-scene statistics. grid.py's partial-tile skipping and sampled valid fraction are documented, not changed.

Frontend should consume georeferenced outputs; this package does not add HTTP/XYZ serving. Human park checks and confirmed entrances are still required before scoring public access.

## Publication status

Local Git push could not invoke credential manager (MSYS directory object access error), so no authenticated push occurred. The connected GitHub account reported push permission, but the subsequent create-tree tool call was rejected with "user rejected MCP tool call". No remote branch or PR was created by this work. docs/PULL_REQUEST.md contains the prepared description and manual publish command. No alternate publication was attempted after the rejection.
