#!/usr/bin/env python3
"""Run copisteria on every page and convert the ordered score to MIDI."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODELS = {
    "28m": ("small/v7_obj-recall-30m_best.pt", "copista-28m"),
    "2m": ("small/v7_obj-recall_best.pt", "copista-2m"),
}
EVIDENCE = "evidence-2m.pt"
MODEL_REPOS = {"28m": "kobimusic/copista-28m", "2m": "kobimusic/copista-2m"}


def ensure_models(size: str) -> None:
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import HfHubHTTPError
    root = Path("/opt/copisteria/models")
    files = [EVIDENCE, MODELS[size][0]]
    try:
        for name in files:
            dest = root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.is_file():
                downloaded = hf_hub_download(repo_id=MODEL_REPOS[size], filename=name)
                shutil.copy2(downloaded, dest)
    except Exception as exc:
        raise RuntimeError(f"モデルの取得に失敗しました ({MODEL_REPOS[size]}, {size}): {exc}") from exc


def merge_xmls(paths: list[Path], target: Path) -> None:
    """Merge page scores by stable part position and append measures in PDF order."""
    from music21 import converter, stream
    scores = [converter.parse(str(path)) for path in paths]
    if not scores:
        raise ValueError("MusicXMLが生成されませんでした")
    base_parts = list(scores[0].parts)
    if not base_parts:
        raise ValueError("最初のページにパートがありません")
    merged = stream.Score()
    out_parts = []
    for idx, first in enumerate(base_parts):
        part = stream.Part(id=first.id or f"P{idx + 1}")
        part.partName = first.partName
        measure_number = 1
        for page_no, score in enumerate(scores, 1):
            parts = list(score.parts)
            if len(parts) != len(base_parts):
                raise ValueError(f"ページ{page_no}のパート数({len(parts)})が先頭ページ({len(base_parts)})と一致しません")
            # Page-local numbering can repeat. Retain physical measure order and renumber.
            measures = list(parts[idx].getElementsByClass("Measure"))
            if not measures:
                raise ValueError(f"ページ{page_no}のパート{idx + 1}に小節がありません")
            for measure in measures:
                measure.number = measure_number
                measure_number += 1
                part.append(measure)
        out_parts.append(part)
        merged.insert(0, part)
    target.parent.mkdir(parents=True, exist_ok=True)
    merged.write("musicxml", fp=str(target))


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF楽譜をMusicXMLとMIDIに変換します (Docker Compose向け)")
    ap.add_argument("score", nargs="?", help="/input内のPDF名、またはPDFパス")
    ap.add_argument("--input", dest="input_path", help="入力PDFのパス")
    ap.add_argument("--output", help="出力MIDIのパス (既定: /output/<入力名>.mid)")
    ap.add_argument("--model", choices=MODELS, default="28m", help="認識モデル (既定: 28m)")
    args = ap.parse_args()
    raw = args.input_path or args.score
    if not raw:
        ap.error("入力PDFを指定してください")
    src = Path(raw)
    if not src.is_absolute():
        src = Path("/input") / src
    src = src.resolve()
    if not src.is_file():
        print(f"エラー: 入力PDFが見つかりません: {src}", file=sys.stderr)
        return 2
    if src.suffix.lower() != ".pdf":
        print("エラー: 入力ファイルはPDFである必要があります", file=sys.stderr)
        return 2
    dest = Path(args.output) if args.output else Path("/output") / f"{src.stem}.mid"
    xml_out = dest.with_suffix(".musicxml") if args.output else Path("/output") / f"{src.stem}.musicxml"
    debug = dest.parent / "debug" / src.stem
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(src))
        count = len(reader.pages)
        if not count:
            raise ValueError("PDFにページがありません")
        ensure_models(args.model)
        temp = Path("/tmp/copisteria-job")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        xmls = []
        for page in range(1, count + 1):
            print(f"ページ {page}/{count} を認識中...", flush=True)
            page_out = temp / f"p{page:04d}"
            subprocess.run([
                sys.executable, "/app/src/run_copisteria.py",
                "--model", args.model,
                "--pdf", str(src),
                "--page", str(page),
                "--out", str(page_out),
            ], check=True, env=os.environ.copy())
            candidates = list(page_out.glob("*.musicxml"))
            if len(candidates) != 1 or candidates[0].stat().st_size < 100:
                raise ValueError(f"ページ{page}のMusicXMLが空、または曖昧です")
            xmls.append(candidates[0])
        debug.mkdir(parents=True, exist_ok=True)
        for n, x in enumerate(xmls, 1):
            shutil.copy2(x, debug / f"page-{n:03d}.musicxml")
        merge_xmls(xmls, xml_out)
        from music21 import converter
        score = converter.parse(str(xml_out))
        midi = score.write("midi", fp=str(dest))
        if not Path(midi).is_file() or not converter.parse(midi).recurse().notes:
            raise ValueError("MIDIにノートイベントがありません")
        print(f"完了: {dest}\nMusicXML: {xml_out}\nページ別XML: {debug}")
        return 0
    except Exception as exc:
        print(f"変換エラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
