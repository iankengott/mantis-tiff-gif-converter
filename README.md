# MANTiS TIFF/GIF Converter

A small GUI and command-line converter for moving between aXis-style animated GIF stacks and MANTiS-friendly multi-page TIFF stacks.

It supports:

- GIF stack + energy `.txt` -> multi-page MANTiS `.tif` + same-basename `.txt`
- TIFF stack + energy `.txt` -> animated `.gif` with the eV list embedded in GIF comment metadata
- Extracting embedded eV metadata from a GIF back into a `.txt`

## Requirements

- Python 3.10+
- Pillow
- Tkinter, for the GUI

On many Linux systems Tkinter is packaged separately from Python. The command-line mode only needs Pillow.

## Install Dependency

```bash
python3 -m pip install pillow
```

## Run The App

```bash
./mantis-gif-tiff-app
```

If your Python does not have Tkinter, use the command-line commands instead.

## Command-Line Usage

```bash
./mantis-gif-tiff-app gif-to-tiff input.gif energies.txt -o output.tif
./mantis-gif-tiff-app tiff-to-gif input.tif energies.txt -o output.gif
./mantis-gif-tiff-app extract-energies output.gif -o extracted_energies.txt
```

The energy file must contain exactly one energy value per GIF frame or TIFF page. Blank lines and lines beginning with `#` are ignored.

## MANTiS TIFF Format

MANTiS expects a multi-page TIFF plus a same-basename text file:

```text
sample.tif
sample.txt
```

The `.txt` file should contain one photon energy in eV per line, in the same order as the image pages.

## GIF Metadata Format

When converting TIFF -> GIF, this tool stores the eV list in a GIF comment extension:

```text
MANTIS_EV_LIST
700.0
700.2
700.4
```

Standard aXis2000 GIF exports may not include this metadata. This tool can preserve eV data in GIFs it creates, but it cannot recover energies that were not present in the source file.
