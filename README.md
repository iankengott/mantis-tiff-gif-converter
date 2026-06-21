# MANTiS TIFF/GIF Converter

Small converter I made for moving between animated GIF stacks, MANTiS TIFF stacks, and the energy text files that go with them.

Main things it does:

- GIF + energy `.txt` -> MANTiS-style TIFF stack + matching `.txt`
- GIF -> TIFF only, if the energies are not known yet
- GIF -> TIFF + generated linear energy list
- TIFF + energy `.txt` -> animated GIF with the eV list embedded in the GIF comment metadata
- Pull the embedded eV list back out of a GIF made by this tool

## Requirements

- Python 3.10+
- Pillow
- Tkinter, for the GUI

Tkinter is sometimes packaged separately on Linux. The command-line mode only needs Pillow.

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
./mantis-gif-tiff-app gif-to-tiff input.gif --base-ev 700 --step-ev 0.2 -o output.tif
./mantis-gif-tiff-app gif-to-tiff input.gif --no-energy-file -o output.tif
./mantis-gif-tiff-app tiff-to-gif input.tif energies.txt -o output.gif
./mantis-gif-tiff-app extract-energies output.gif -o extracted_energies.txt
```

The energy file needs one eV value per GIF frame or TIFF page. Blank lines and lines starting with `#` are ignored.

When a conversion makes both a TIFF and TXT, it puts them together in a folder. For example:

```bash
./mantis-gif-tiff-app gif-to-tiff input.gif energies.txt -o sample.tif
```

writes:

```text
sample/
  sample.tif
  sample.txt
```

Single-file conversions just write the file you picked.

## MANTiS TIFF Format

For TIFF stacks, MANTiS expects a multi-page TIFF plus a same-basename text file:

```text
sample.tif
sample.txt
```

The `.txt` file has one photon energy in eV per line, in the same order as the TIFF pages.

TIFF can technically have metadata tags, but MANTiS's documented TIFF workflow uses the separate `.txt` energy list. For this workflow I treat TIFF + TXT as the pair that matters.

If the energies are not known yet, make a TIFF-only stack for inspection:

```bash
./mantis-gif-tiff-app gif-to-tiff input.gif --no-energy-file -o output.tif
```

If the scan used a constant energy step, generate a temporary linear energy list:

```bash
./mantis-gif-tiff-app gif-to-tiff input.gif --base-ev 700 --step-ev 0.2 -o output.tif
```

That creates an `output/` folder containing `output.tif` and `output.txt`. The values are `base_ev + frame_index * step_ev`. Do not use guessed energies for real analysis unless they match the acquisition settings.

## GIF Metadata Format

When converting TIFF -> GIF, the eV list is stored in a GIF comment extension:

```text
MANTIS_EV_LIST
700.0
700.2
700.4
```

Normal aXis2000 GIF exports may not have this metadata. This can preserve eV data in GIFs it creates, but it cannot recover energies that were never in the source file.
