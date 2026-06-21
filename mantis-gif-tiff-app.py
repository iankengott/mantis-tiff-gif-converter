#!/usr/bin/env python3
"""Convert between aXis-style GIF stacks and MANTiS TIFF stacks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageSequence


ENERGY_HEADER = "MANTIS_EV_LIST"


def clean_stem(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"\s*\(\d+\)$", "", stem)
    return stem.replace(" ", "_")


def read_energies(path: Path) -> list[str]:
    energies: list[str] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
        if not match:
            raise ValueError(f"{path}: line {line_no} does not contain an energy value: {raw!r}")
        energies.append(match.group(0))
    if not energies:
        raise ValueError(f"{path}: no energy values found")
    return energies


def write_energies(path: Path, energies: Iterable[str]) -> None:
    path.write_text("\n".join(str(e) for e in energies) + "\n", encoding="utf-8")


def linear_energies(base_ev: float, step_ev: float, count: int) -> list[str]:
    return [f"{base_ev + (i * step_ev):.12g}" for i in range(count)]


def gif_comment_for_energies(energies: list[str]) -> bytes:
    text = ENERGY_HEADER + "\n" + "\n".join(energies) + "\n"
    return text.encode("utf-8")


def extract_energies_from_gif(gif_path: Path) -> list[str]:
    with Image.open(gif_path) as img:
        comment = img.info.get("comment")
    if not comment:
        return []
    if isinstance(comment, bytes):
        text = comment.decode("utf-8", errors="replace")
    else:
        text = str(comment)
    if ENERGY_HEADER not in text:
        return []
    text = text.split(ENERGY_HEADER, 1)[1]
    return re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)


def gif_frames(gif_path: Path) -> list[Image.Image]:
    frames: list[Image.Image] = []
    with Image.open(gif_path) as img:
        for frame in ImageSequence.Iterator(img):
            frames.append(frame.convert("L").copy())
    if not frames:
        raise ValueError(f"{gif_path}: no frames found")
    return frames


def tiff_pages(tiff_path: Path) -> list[Image.Image]:
    pages: list[Image.Image] = []
    with Image.open(tiff_path) as img:
        for page in ImageSequence.Iterator(img):
            pages.append(page.convert("L").copy())
    if not pages:
        raise ValueError(f"{tiff_path}: no pages found")
    return pages


def save_multipage_tiff(frames: list[Image.Image], output_tiff: Path) -> None:
    output_tiff.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_tiff,
        save_all=True,
        append_images=frames[1:],
        compression="tiff_deflate",
    )


def save_animated_gif(frames: list[Image.Image], energies: list[str], output_gif: Path) -> None:
    output_gif.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_gif,
        save_all=True,
        append_images=frames[1:],
        duration=120,
        loop=0,
        comment=gif_comment_for_energies(energies),
    )


def ensure_count(label: str, frame_count: int, energies: list[str]) -> None:
    if frame_count != len(energies):
        raise ValueError(
            f"{label}: found {frame_count} image frames/pages but {len(energies)} energy values"
        )


def gif_to_tiff(gif_path: Path, energy_path: Path, output_tiff: Path | None = None) -> tuple[Path, Path]:
    frames = gif_frames(gif_path)
    energies = read_energies(energy_path)
    ensure_count(gif_path.name, len(frames), energies)
    return gif_frames_to_tiff(gif_path, frames, energies, output_tiff)


def gif_to_tiff_linear(
    gif_path: Path,
    base_ev: float,
    step_ev: float,
    output_tiff: Path | None = None,
) -> tuple[Path, Path]:
    frames = gif_frames(gif_path)
    energies = linear_energies(base_ev, step_ev, len(frames))
    return gif_frames_to_tiff(gif_path, frames, energies, output_tiff)


def gif_to_tiff_only(gif_path: Path, output_tiff: Path | None = None) -> Path:
    frames = gif_frames(gif_path)
    if output_tiff is None:
        output_tiff = gif_path.with_name(clean_stem(gif_path) + ".tif")
    save_multipage_tiff(frames, output_tiff)
    return output_tiff


def gif_frames_to_tiff(
    gif_path: Path,
    frames: list[Image.Image],
    energies: list[str],
    output_tiff: Path | None = None,
) -> tuple[Path, Path]:
    if output_tiff is None:
        output_tiff = gif_path.with_name(clean_stem(gif_path) + ".tif")
    output_txt = output_tiff.with_suffix(".txt")
    save_multipage_tiff(frames, output_tiff)
    write_energies(output_txt, energies)
    return output_tiff, output_txt


def tiff_to_gif(tiff_path: Path, energy_path: Path, output_gif: Path | None = None) -> Path:
    frames = tiff_pages(tiff_path)
    energies = read_energies(energy_path)
    ensure_count(tiff_path.name, len(frames), energies)
    if output_gif is None:
        output_gif = tiff_path.with_suffix(".gif")
    save_animated_gif(frames, energies, output_gif)
    return output_gif


def build_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("MANTiS GIF/TIFF Converter")
    root.geometry("780x540")

    mode = tk.StringVar(value="gif_to_tiff_txt")
    input_path = tk.StringVar()
    energy_path = tk.StringVar()
    output_path = tk.StringVar()
    base_ev = tk.StringVar()
    step_ev = tk.StringVar()
    status = tk.StringVar(value="Choose files, then convert.")

    def update_labels(*_args: object) -> None:
        current = mode.get()
        if current.startswith("gif_to_tiff"):
            input_label.configure(text="Input GIF stack")
            output_label.configure(text="Output TIFF")
            output_hint.configure(text="Output is a multi-page TIFF. MANTiS needs a matching TXT for real analysis.")
            if current == "gif_to_tiff_txt":
                convert_button.configure(text="Convert GIF + energy TXT -> TIFF + TXT")
                energy_label.configure(text="Energy TXT")
                energy_entry.configure(state="normal")
                energy_button.configure(state="normal")
                base_entry.configure(state="disabled")
                step_entry.configure(state="disabled")
            elif current == "gif_to_tiff_linear":
                convert_button.configure(text="Convert GIF -> TIFF + assumed linear TXT")
                energy_label.configure(text="Energy TXT")
                energy_entry.configure(state="disabled")
                energy_button.configure(state="disabled")
                base_entry.configure(state="normal")
                step_entry.configure(state="normal")
            else:
                convert_button.configure(text="Convert GIF -> TIFF only")
                energy_label.configure(text="Energy TXT")
                energy_entry.configure(state="disabled")
                energy_button.configure(state="disabled")
                base_entry.configure(state="disabled")
                step_entry.configure(state="disabled")
        else:
            input_label.configure(text="Input TIFF stack")
            output_label.configure(text="Output GIF")
            output_hint.configure(text="Energy values come from the TXT you choose, then get embedded into the GIF.")
            convert_button.configure(text="Convert TIFF + energy TXT -> GIF with eV metadata")
            energy_label.configure(text="Energy TXT")
            energy_entry.configure(state="normal")
            energy_button.configure(state="normal")
            base_entry.configure(state="disabled")
            step_entry.configure(state="disabled")

    def choose_input() -> None:
        if mode.get().startswith("gif_to_tiff"):
            filetypes = [("GIF files", "*.gif"), ("All files", "*.*")]
        else:
            filetypes = [("TIFF files", "*.tif *.tiff"), ("All files", "*.*")]
        picked = filedialog.askopenfilename(title="Choose input image stack", filetypes=filetypes)
        if picked:
            input_path.set(picked)
            if not output_path.get():
                src = Path(picked)
                if mode.get().startswith("gif_to_tiff"):
                    output_path.set(str(src.with_name(clean_stem(src) + ".tif")))
                else:
                    output_path.set(str(src.with_suffix(".gif")))

    def choose_energy() -> None:
        picked = filedialog.askopenfilename(
            title="Choose energy TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if picked:
            energy_path.set(picked)

    def choose_output() -> None:
        if mode.get().startswith("gif_to_tiff"):
            defaultextension = ".tif"
            filetypes = [("TIFF files", "*.tif"), ("All files", "*.*")]
        else:
            defaultextension = ".gif"
            filetypes = [("GIF files", "*.gif"), ("All files", "*.*")]
        picked = filedialog.asksaveasfilename(
            title="Choose output file",
            defaultextension=defaultextension,
            filetypes=filetypes,
        )
        if picked:
            output_path.set(picked)

    def convert() -> None:
        try:
            if not input_path.get():
                raise ValueError("Choose an input image stack first.")
            current = mode.get()
            if current == "gif_to_tiff_txt":
                if not energy_path.get():
                    raise ValueError("Choose the energy TXT file first.")
                output = Path(output_path.get()) if output_path.get() else None
                tiff, txt = gif_to_tiff(Path(input_path.get()), Path(energy_path.get()), output)
                status.set(f"Wrote {tiff.name} and {txt.name}")
                messagebox.showinfo("Conversion complete", f"Wrote:\n{tiff}\n{txt}")
            elif current == "gif_to_tiff_linear":
                if not base_ev.get().strip() or not step_ev.get().strip():
                    raise ValueError("Enter a base eV and step eV.")
                output = Path(output_path.get()) if output_path.get() else None
                tiff, txt = gif_to_tiff_linear(
                    Path(input_path.get()),
                    float(base_ev.get()),
                    float(step_ev.get()),
                    output,
                )
                status.set(f"Wrote {tiff.name} and assumed-energy {txt.name}")
                messagebox.showinfo(
                    "Conversion complete",
                    f"Wrote:\n{tiff}\n{txt}\n\nEnergy values were generated from base + frame_index * step.",
                )
            elif current == "gif_to_tiff_only":
                output = Path(output_path.get()) if output_path.get() else None
                tiff = gif_to_tiff_only(Path(input_path.get()), output)
                status.set(f"Wrote {tiff.name} without an energy TXT")
                messagebox.showinfo(
                    "Conversion complete",
                    f"Wrote:\n{tiff}\n\nNo energy TXT was created. MANTiS may need energies for analysis.",
                )
            else:
                if not energy_path.get():
                    raise ValueError("Choose the energy TXT file first.")
                output = Path(output_path.get()) if output_path.get() else None
                gif = tiff_to_gif(Path(input_path.get()), Path(energy_path.get()), output)
                embedded = extract_energies_from_gif(gif)
                status.set(f"Wrote {gif.name} with {len(embedded)} embedded eV values")
                messagebox.showinfo(
                    "Conversion complete",
                    f"Wrote:\n{gif}\n\nEmbedded {len(embedded)} eV values in GIF comment metadata.",
                )
        except Exception as exc:
            status.set(str(exc))
            messagebox.showerror("Conversion failed", str(exc))

    def extract_metadata() -> None:
        picked = filedialog.askopenfilename(
            title="Choose GIF with embedded eV metadata",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")],
        )
        if not picked:
            return
        try:
            energies = extract_energies_from_gif(Path(picked))
            if not energies:
                raise ValueError("No MANTiS eV metadata found in that GIF.")
            default = str(Path(picked).with_suffix(".txt"))
            out = filedialog.asksaveasfilename(
                title="Save extracted energy TXT",
                initialfile=Path(default).name,
                initialdir=str(Path(default).parent),
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )
            if out:
                write_energies(Path(out), energies)
                status.set(f"Extracted {len(energies)} eV values to {Path(out).name}")
        except Exception as exc:
            status.set(str(exc))
            messagebox.showerror("Extraction failed", str(exc))

    main = ttk.Frame(root, padding=18)
    main.pack(fill="both", expand=True)

    ttk.Label(main, text="MANTiS GIF/TIFF Converter", font=("", 16, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
    )

    ttk.Radiobutton(main, text="GIF + energy TXT -> MANTiS TIFF + TXT", variable=mode, value="gif_to_tiff_txt").grid(
        row=1, column=0, columnspan=3, sticky="w"
    )
    ttk.Radiobutton(main, text="GIF -> TIFF + assumed linear energy TXT", variable=mode, value="gif_to_tiff_linear").grid(
        row=2, column=0, columnspan=3, sticky="w"
    )
    ttk.Radiobutton(main, text="GIF -> TIFF only, no energy TXT", variable=mode, value="gif_to_tiff_only").grid(
        row=3, column=0, columnspan=3, sticky="w"
    )
    ttk.Radiobutton(main, text="TIFF + energy TXT -> GIF with embedded eV metadata", variable=mode, value="tiff_to_gif").grid(
        row=4, column=0, columnspan=3, sticky="w", pady=(0, 14)
    )
    mode.trace_add("write", update_labels)

    input_label = ttk.Label(main, text="Input GIF stack")
    input_label.grid(row=5, column=0, sticky="w", pady=6)
    ttk.Entry(main, textvariable=input_path).grid(row=5, column=1, sticky="ew", padx=8)
    ttk.Button(main, text="Browse", command=choose_input).grid(row=5, column=2, sticky="ew")

    energy_label = ttk.Label(main, text="Energy TXT")
    energy_label.grid(row=6, column=0, sticky="w", pady=6)
    energy_entry = ttk.Entry(main, textvariable=energy_path)
    energy_entry.grid(row=6, column=1, sticky="ew", padx=8)
    energy_button = ttk.Button(main, text="Browse", command=choose_energy)
    energy_button.grid(row=6, column=2, sticky="ew")

    ttk.Label(main, text="Base eV").grid(row=7, column=0, sticky="w", pady=6)
    base_entry = ttk.Entry(main, textvariable=base_ev)
    base_entry.grid(row=7, column=1, sticky="ew", padx=8)
    ttk.Label(main, text="Step eV per frame").grid(row=8, column=0, sticky="w", pady=6)
    step_entry = ttk.Entry(main, textvariable=step_ev)
    step_entry.grid(row=8, column=1, sticky="ew", padx=8)

    output_label = ttk.Label(main, text="Output TIFF")
    output_label.grid(row=9, column=0, sticky="w", pady=6)
    ttk.Entry(main, textvariable=output_path).grid(row=9, column=1, sticky="ew", padx=8)
    ttk.Button(main, text="Browse", command=choose_output).grid(row=9, column=2, sticky="ew")

    convert_button = ttk.Button(main, text="Convert GIF + TXT -> TIFF + TXT", command=convert)
    convert_button.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(18, 8))

    ttk.Button(main, text="Extract embedded eV metadata from GIF", command=extract_metadata).grid(
        row=11, column=0, columnspan=3, sticky="ew"
    )

    ttk.Label(main, textvariable=status, foreground="#444").grid(
        row=12, column=0, columnspan=3, sticky="w", pady=(18, 0)
    )

    output_hint = ttk.Label(
        main,
        text="The energy TXT must contain exactly one eV value per image frame/page.",
        foreground="#666",
    )
    output_hint.grid(row=13, column=0, columnspan=3, sticky="w", pady=(8, 0))

    main.columnconfigure(1, weight=1)
    update_labels()
    root.mainloop()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p1 = sub.add_parser("gif-to-tiff", help="Convert animated GIF to TIFF, with optional energy TXT")
    p1.add_argument("gif")
    p1.add_argument("energies", nargs="?", help="Existing energy TXT with one value per GIF frame")
    p1.add_argument("-o", "--output")
    p1.add_argument("--base-ev", type=float, help="Generate energies from this starting eV")
    p1.add_argument("--step-ev", type=float, help="Generate energies using this eV step per frame")
    p1.add_argument("--no-energy-file", action="store_true", help="Write only the TIFF stack")

    p2 = sub.add_parser("tiff-to-gif", help="Convert TIFF plus energy TXT to GIF with embedded eV metadata")
    p2.add_argument("tiff")
    p2.add_argument("energies")
    p2.add_argument("-o", "--output")

    p3 = sub.add_parser("extract-energies", help="Extract embedded eV metadata from a GIF")
    p3.add_argument("gif")
    p3.add_argument("-o", "--output")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "gif-to-tiff":
            output = Path(args.output) if args.output else None
            if args.no_energy_file:
                tiff = gif_to_tiff_only(Path(args.gif), output)
                print(f"Wrote {tiff}")
                print("No energy TXT written")
            elif args.base_ev is not None or args.step_ev is not None:
                if args.base_ev is None or args.step_ev is None:
                    raise ValueError("--base-ev and --step-ev must be used together")
                tiff, txt = gif_to_tiff_linear(Path(args.gif), args.base_ev, args.step_ev, output)
                print(f"Wrote {tiff}")
                print(f"Wrote {txt}")
            else:
                if not args.energies:
                    raise ValueError("provide an energy TXT, or use --base-ev/--step-ev, or --no-energy-file")
                tiff, txt = gif_to_tiff(Path(args.gif), Path(args.energies), output)
                print(f"Wrote {tiff}")
                print(f"Wrote {txt}")
        elif args.command == "tiff-to-gif":
            gif = tiff_to_gif(
                Path(args.tiff),
                Path(args.energies),
                Path(args.output) if args.output else None,
            )
            print(f"Wrote {gif}")
            print(f"Embedded {len(extract_energies_from_gif(gif))} eV values")
        elif args.command == "extract-energies":
            energies = extract_energies_from_gif(Path(args.gif))
            if not energies:
                raise ValueError("No MANTiS eV metadata found in that GIF.")
            out = Path(args.output) if args.output else Path(args.gif).with_suffix(".txt")
            write_energies(out, energies)
            print(f"Wrote {out}")
        else:
            build_gui()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
