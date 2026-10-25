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

## 2026-10-25 — Full-scene completion pass (local only)

Added analyse_scene/windows/exclude_context/evaluate_mask and a --all entry point. Processed all three source TIFFs, keeping partial edges and merging before global 300m2 filtering. Cached OSM buildings/residential/private polygons are now applied automatically, with disjoint removal areas and incomplete-context coverage reported. Native grid, valid counts and artifact hashes checked from real outputs. 27 synthetic tests passed. Prepared 51 draft inspection points; real reviewed labels remain zero.

Results: Theos00 473661.50 m2; Theos01 2796586.50 m2; Theos02 621733.25 m2 candidate vegetation after mapped exclusions and patch filtering. These cover all valid source pixels, unlike earlier polygon-AOI figures. Results remain unvalidated.

Park desk checks: row-476 has registry photograph and Dec 2025 street-view context from prior desk check; row-35 source Maps short link resolves to the same coordinate, but direct Street View query returns no imagery. Neither has independently confirmed current access/entrance. Original reference positions preserved. See FULL-SCENE-METHODS-th.md and Output/nike-scenes-20261025/checks.json.

No GitHub push, remote branch creation, PR or merge attempted. Existing local grid.py edit remains untouched and outside Nike commits.

OSM context snapshots were formatted to one GeoJSON feature per line to keep code reviews manageable; parsed JSON content was checked unchanged. Exact pre-format input bytes used for the actual runs remain recoverable in local commit 1817988, matching per-scene context_sha256. Formatting changed file hashes, not geometry or results; no duplicate full-scene run was performed for formatting alone. Exact module bytes matching every code_sha256 (8/8 modules per scene) were archived under each result's code-used/ folder.
