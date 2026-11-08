#!/usr/bin/env python3
"""Transcribe PDF score pages with SMT++ and export MusicXML and MIDI."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODELS = {
    "grandstaff": "antoniorv6/smt-grandstaff",
    "polish": "PRAIG/smt-fp-polish-scores",
}


def render_page(pdf: Path, page: int, target: Path) -> None:
    subprocess.run([
        "pdftoppm", "-f", str(page), "-l", str(page), "-r", "300",
        "-gray", "-png", "-singlefile", str(pdf), str(target.with_suffix("")),
    ], check=True, stdout=subprocess.DEVNULL)


def to_kern(tokens: list[str]) -> str:
    text = "".join(token for token in tokens if token not in {"<pad>", "<bos>", "<eos>"})
    text = text.replace("<t>", "\t").replace("<b>", "\n").replace("<s>", " ")
    text = text.strip()
    if not text:
        raise ValueError("SMT++が空の譜面を返しました")
    if "**bekern" in text:
        text = text.replace("**bekern", "**kern")
    elif "**kern" not in text:
        text = "**kern\n" + text
    if "*-" not in text:
        text += "\n*-\n"
    return text + ("" if text.endswith("\n") else "\n")


def merge_scores(paths: list[Path], target: Path) -> None:
    from music21 import converter, stream

    scores = [converter.parse(str(p), format="humdrum") for p in paths]
    parts0 = list(scores[0].parts)
    if not parts0:
        raise ValueError("譜面パートを読み取れませんでした")
    merged = stream.Score()
    for i, first in enumerate(parts0):
        part = stream.Part(id=first.id or f"P{i + 1}")
        part.partName = first.partName
        number = 1
        for page_no, score in enumerate(scores, 1):
            parts = list(score.parts)
            if len(parts) != len(parts0):
                raise ValueError(f"ページ{page_no}のパート数が他のページと一致しません")
            measures = list(parts[i].getElementsByClass("Measure"))
            if not measures:
                raise ValueError(f"ページ{page_no}のパート{i + 1}に小節がありません")
            for measure in measures:
                measure.number = number
                number += 1
                part.append(measure)
        merged.insert(0, part)
    target.parent.mkdir(parents=True, exist_ok=True)
    merged.write("musicxml", fp=str(target))


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF楽譜をSMT++で認識し、MusicXMLとMIDIを作成します")
    ap.add_argument("score", nargs="?", help="/input内のPDF名、またはPDFパス")
    ap.add_argument("--input", dest="input_path", help="入力PDFパス")
    ap.add_argument("--output", help="出力MIDIパス (既定: /output/<入力名>.mid)")
    ap.add_argument("--model", choices=MODELS, default="grandstaff", help="SMT++チェックポイント (既定: grandstaff)")
    args = ap.parse_args()
    raw = args.input_path or args.score
    if not raw:
        ap.error("入力PDFを指定してください")
    src = Path(raw)
    if not src.is_absolute():
        src = Path("/input") / src
    src = src.resolve()
    if not src.is_file() or src.suffix.lower() != ".pdf":
        print(f"エラー: PDFが見つからないか、PDFではありません: {src}", file=sys.stderr)
        return 2
    dest = Path(args.output) if args.output else Path("/output") / f"{src.stem}.mid"
    xml_out = dest.with_suffix(".musicxml")
    debug = dest.parent / "debug" / src.stem
    temp = Path("/tmp/smt-midi-job")
    try:
        from pypdf import PdfReader
        import numpy as np
        import torch
        from PIL import Image
        from data_augmentation.data_augmentation import convert_img_to_tensor
        from smt_model import SMTModelForCausalLM

        count = len(PdfReader(str(src)).pages)
        if count < 1:
            raise ValueError("PDFにページがありません")
        model_id = os.environ.get(f"SMT_MODEL_{args.model.upper()}", MODELS[args.model])
        print(f"SMT++ checkpoint: {model_id}", flush=True)
        device = torch.device("cpu")
        model = SMTModelForCausalLM.from_pretrained(model_id).to(device).eval()
        maxh = int(model.config.maxh)
        maxw = int(model.config.maxw)
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        kerns = []
        for page in range(1, count + 1):
            print(f"ページ {page}/{count} を認識中...", flush=True)
            image_path = temp / f"page-{page:03d}.png"
            render_page(src, page, image_path)
            image = Image.open(image_path).convert("L")
            scale = min(1.0, maxw / image.width, maxh / image.height)
            if scale < 1:
                image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
            tensor = convert_img_to_tensor(np.asarray(image)).unsqueeze(0).to(device)
            with torch.inference_mode():
                tokens, _ = model.predict(tensor, convert_to_str=True)
            kern_path = temp / f"page-{page:03d}.krn"
            kern_path.write_text(to_kern(tokens), encoding="utf-8")
            kerns.append(kern_path)
        debug.mkdir(parents=True, exist_ok=True)
        for i, kern in enumerate(kerns, 1):
            shutil.copy2(kern, debug / f"page-{i:03d}.krn")
        merge_scores(kerns, xml_out)
        from music21 import converter
        score = converter.parse(str(xml_out))
        midi_path = Path(score.write("midi", fp=str(dest)))
        if not midi_path.is_file() or not converter.parse(str(midi_path)).recurse().notes:
            raise ValueError("出力MIDIにノートイベントがありません")
        print(f"完了: {dest}\nMusicXML: {xml_out}\nページ別bekern: {debug}", flush=True)
        return 0
    except Exception as exc:
        print(f"変換エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
