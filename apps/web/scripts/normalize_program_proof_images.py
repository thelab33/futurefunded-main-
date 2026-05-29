from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path("app/static/images/program-proof")
SOURCE = ROOT / "source"

targets = {
    "6th-grade.jpg": ["6th.jpg", "6th.png", "sixth.jpg", "sixth.png", "6th.jpeg", "sixth.jpeg"],
    "7th-grade.jpg": [
        "7th.jpg",
        "7th.png",
        "seventh.jpg",
        "seventh.png",
        "7th.jpeg",
        "seventh.jpeg",
    ],
    "8th-grade.jpg": ["8th.jpg", "8th.png", "eighth.jpg", "eighth.png", "8th.jpeg", "eighth.jpeg"],
}


def normalize(src: Path, dest: Path):
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(
            im,
            (1600, 1100),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.44),
        )
        im.save(dest, "JPEG", quality=88, optimize=True, progressive=True)


ROOT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)

for dest_name, candidates in targets.items():
    dest = ROOT / dest_name
    matched = None

    for name in candidates:
        candidate = SOURCE / name
        if candidate.exists():
            matched = candidate
            break

    if not matched:
        print(f"⚠️ Missing source image for {dest_name}.")
        print(f"   Drop one of these into {SOURCE}: {', '.join(candidates)}")
        continue

    normalize(matched, dest)
    print(f"✅ {dest_name} normalized from {matched}")
