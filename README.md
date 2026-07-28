# SynthEyes AYON Addon

AYON host integration for [Boris FX SynthEyes](https://borisfx.com/products/syntheyes/).
It uses the vendor-supplied SyPy3 API and does not modify the SynthEyes
installation.

## Current scope

- Launch SynthEyes from AYON with a private local SyPy listener.
- Open the selected or last `.sni` workfile on launch.
- Companion panel for AYON Workfiles and Publish tools.
- Loader for AYON `plate` and `render` products, including version
  update/switch/remove.
- AYON `IWorkfileHost` and `IPublishHost` integration.
- Workfile collection for the generic AYON publish pipeline.
- AYON context, creator data, and loader containers persisted in the Scene
  Information **Description** field without replacing artist-authored text.
- Profile-driven native Multi-Export publishing for Nuke scripts, geometry,
  STMaps, camera exports, Blender scripts, and other file outputs.
- Perspective viewport review creation as image sequences, with settings and
  representation tags compatible with AYON review and burn-in extraction.
- Processed plate rendering through Image Preprocessor Save Sequence, with
  optional temporary Filtering/Color reset and source-plate colorspace.
- Configurable SyPy3 location and listener connection timeout.
- Project-configured frame matching, half/float processing depths, 3-D LUT,
  and Image Preprocessor level adjustment.

This first version deliberately does not automate tracking or solving. The SyPy
license restricts unattended, remote, and high-volume processing; the bridge is
designed for an artist-driven local session.

## Build and install

1. Build the package:

   ```powershell
   python create_package.py
   ```

2. Upload `package/syntheyes-0.5.0+dev.zip` in AYON's **Bundles & Addons**
   administration page and add it to the production bundle.
3. In the Applications addon, create or update a `syntheyes` application
   variant. On this workstation the executable is:

   ```text
   C:\Program Files\BorisFX\SynthEyes 2026\SynthEyes64.exe
   ```

4. Assign the application to a project and launch it from AYON.

The addon resolves `SyPy3` beside the configured executable. For a nonstandard
layout, set **SynthEyes > SyPy3 directory override** to the directory that
contains the `SyPy3` package.

## Architecture

SynthEyes uses "bring your own Python." AYON's Python process launches
SynthEyes with `-l <port> -pin <pin>`, connects through SyPy3 on localhost, and
hosts AYON's tools outside the SynthEyes process. The random listener
credentials are scoped to that launch and are never persisted.

## Multi-Export publishing

Publishing is configured under **SynthEyes > Publish** in two parts:

1. **Export presets** define a filename-safe name, a SynthEyes `.szl`
   exporter, a Workflow Preset JSON file, and one or more expected products.
2. **Preset profiles** select one or more export-preset names by AYON task type
   and/or task name.

The preset name accepts only `a-z`, `A-Z`, `0-9`, and `_`. Preset paths may use
context and anatomy tokens such as `{root[work]}` and `{project[name]}`.

Create each Workflow Preset JSON in SynthEyes from the Multi-Export
**Exporters** tree. The file must contain exactly one exporter stage. The
configured `.szl` identifies and validates the intended native exporter; its
human-readable name is read from the file's `//SIZZLEX` header. The JSON owns
the saved options for that exporter.

During publish, AYON temporarily points SynthEyes' **Multi-Export Files**
directory at:

```text
<directory containing the .sni>/<task>/v<workfile version>/<preset>
```

For example, `shot010_matchmove_v012.sni`, task `matchmove`, and preset
`nuke_full` export below `matchmove/v012/nuke_full`. The version is taken from
the last `v###` token in the `.sni` filename. AYON restores the user's
Multi-Export directory preference after the export.

Expected products are collected recursively from that preset directory. Each
rule matches the extension and an optional case-insensitive substring in the
filename, then assigns AYON product base and product types.

| Output | Extension | Filename includes | Base type | Product type |
| --- | --- | --- | --- | --- |
| Nuke scene | `nk` | *(empty)* | `workfile` | `workfile` |
| Mesh | `obj` | *(empty)* | `model` | `model` |
| Undistort STMap | `exr` | `undistort` | `image` | `image` |
| Redistort STMap | `exr` | `redistort` | `image` | `image` |
| Alembic camera | `abc` | *(empty)* | `camera` | `camera` |
| FBX camera/scene | `fbx` | *(empty)* | `camera` | `camera` |
| Blender import script | `py` | *(empty)* | `workfile` | `workfile` |

If a native export stage has a **Keep File Spec**-style option, leave it
disabled when its outputs should follow the AYON-managed Multi-Export
directory.

## Perspective review publishing

Create a **Review** product in AYON's Publisher. Suggested creator variants
come from **SynthEyes > Creator plugins > Create Review > Default variants**
and default to `Main`.

The creator settings also control the image extension, viewport-item and grid
visibility, square-pixel output, anti-aliasing/motion-blur quality, shutter
angle and phase, SynthEyes frame/time burn-in, and representation tags.
Supported output extensions are image formats only:
`jpg`, `jpeg`, `png`, `tif`, `tiff`, `tga`, `sgi`, and `exr`. Movie/container
formats are rejected.

During extraction, AYON temporarily activates the Perspective view and invokes
the same **Preview Movie** operation as the Perspective **RENDER** button. The
result is a numbered image-sequence representation with the configured tags.
Include the `review` tag for AYON's Extract Review plugin and `burnin` when the
source should also be eligible for configured Extract Burnin processing.

## Processed plate publishing

Create a **Processed Plate Render** product to render the active shot through
Image Preprocessor **Output > Save Sequence**. Creator variant suggestions are
configured under **SynthEyes > Creator plugins > Create Processed Plate
Render** and default to `Undistorted`.

Project settings control the image extension, RGB, alpha, meshes, frame/time
burn-in, representation tags, and whether Filtering and Color are temporarily
reset. Output is restricted to numbered image sequences; movie/container
formats are rejected.

With temporary reset enabled, AYON snapshots the complete live Image
Preprocessor state, creates default Color and Filtering groups, and applies
only those two groups during rendering. Lens correction, stabilization,
cropping, resolution, ROI, and their animation remain active. The complete
original state and active preset are restored afterward, including when
rendering fails.

The resulting AYON product base/type is `render`. Its `colorspace` is copied
from the AYON plate/render representation loaded as the active SynthEyes shot.
Add `review` and/or `burnin` representation tags to route it through the
corresponding AYON Extract Review and Extract Burnin configuration.

## Development

Run the dependency-light unit tests with:

```powershell
pytest
```

The local Boris FX manuals used during development live under
`docs/syntheyes/`. The implementation targets the SynthEyes 2026 SyPy API.

## Known limitations

- SynthEyes 2026 SyPy exposes `SaveIfChanged`, but no non-mutating dirty-state
  query. The host conservatively reports that a scene may have changes.
- Save As is driven through the public `SetSNIFileName` and `File/Save` action.
  This needs an interactive smoke test against each SynthEyes maintenance
  release because menu action identifiers are resolved at runtime.
- Exporter-specific dialogs and preset contents remain owned by SynthEyes;
  AYON validates the configured exporter and runs the saved native stage.

## References

- [AYON documentation](https://docs.ayon.dev/)
- [SyPy API overview](https://support.borisfx.com/hc/en-us/articles/24365288989197--SyPy-A-Python-API-SDK-for-SynthEyes)
- [ayon-equalizer reference addon](https://github.com/ynput/ayon-equalizer)
