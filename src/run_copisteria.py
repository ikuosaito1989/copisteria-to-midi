#!/usr/bin/env python3
"""Verify and run the requested copisteria detector checkpoint."""
import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("28m", "2m"), required=True)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    os.environ["COPISTERIA_DETECTOR"] = args.model
    from copisteria import detect, pipeline
    from copisteria.paths import DETECTORS, detector as selected_detector

    checkpoint, tag = selected_detector()
    expected = DETECTORS[args.model][0]
    checkpoint = Path(checkpoint).resolve()
    expected = Path(expected).resolve()
    if checkpoint != expected:
        raise RuntimeError(
            f"copisteria selected unexpected detector for {args.model}: {checkpoint} (expected {expected})"
        )
    if not checkpoint.is_file():
        raise FileNotFoundError(f"{args.model} detector checkpoint is missing: {checkpoint}")

    print(f"copisteria detector requested: copista-{args.model}", flush=True)
    print(f"copisteria detector checkpoint: {checkpoint} ({checkpoint.stat().st_size:,} bytes)", flush=True)
    print(f"copisteria detector cache tag: {tag}", flush=True)
    loaded_detector = detect.Detector(weights=checkpoint, device="cpu")
    parameter_count = sum(p.numel() for p in loaded_detector.model.parameters())
    if args.model == "28m" and parameter_count < 10_000_000:
        raise RuntimeError(f"28m selection loaded only {parameter_count:,} detector parameters")
    if args.model == "2m" and parameter_count >= 10_000_000:
        raise RuntimeError(f"2m selection unexpectedly loaded {parameter_count:,} detector parameters")
    print(f"copisteria detector checkpoint loaded: copista-{args.model} ({parameter_count:,} parameters)", flush=True)

    # Reuse the verified instance so the checkpoint logged above is the one used.
    detect.Detector = lambda *unused_args, **unused_kwargs: loaded_detector
    pipeline.main([
        "--pdf", args.pdf,
        "--range", str(args.page),
        "--out", args.out,
        "--device", "cpu",
        "--detector", args.model,
    ])


if __name__ == "__main__":
    main()
