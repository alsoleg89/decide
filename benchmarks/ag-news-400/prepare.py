"""Create a fixed, stratified 400-row sample from the AG News test CSV."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("csv", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
raw = args.csv.read_bytes()
if hashlib.sha256(raw).hexdigest() != "521465c2428ed7f02f8d6db6ffdd4b5447c1c701962353eb2c40d548c3c85699":
    parser.error("CSV does not match the pinned AG News test snapshot")
rows = list(csv.reader(raw.decode("utf-8").splitlines()))
assert len(rows) == 7600 and all(len(row) == 3 for row in rows)
classes = {"1": "world", "2": "sports", "3": "business", "4": "science_technology"}
assert set(row[0] for row in rows) == classes.keys()
rng = random.Random(20260919)
indices = []
for label in classes:
    indices.extend(rng.sample([i for i, row in enumerate(rows) if row[0] == label], 100))
rng.shuffle(indices)
args.output.mkdir(parents=True, exist_ok=True)
inputs, labels = [], []
for index in indices:
    label, title, description = rows[index]
    identity = f"ag-news-test:{index + 1}"
    inputs.append({"id": identity, "content": {"title": title, "description": description}})
    labels.append({"id": identity, "expected": classes[label]})
for name, data in [("items.jsonl", inputs), ("labels.jsonl", labels)]:
    (args.output / name).write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in data), encoding="utf-8")
manifest = {"dataset": "AG News, test split, 100 examples per class", "seed": 20260919,
            "source_url": "https://raw.githubusercontent.com/mhjabreel/CharCnn_Keras/555590db4219b1243abb1918effd6a7425a2d75f/data/ag_news_csv/test.csv",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "input_jsonl_sha256": hashlib.sha256((args.output / "items.jsonl").read_bytes()).hexdigest(),
            "items": len(inputs), "selection": "random.Random(seed); sample 100 zero-based indices per class in class order, then shuffle; IDs store one-based CSV row numbers"}
(args.output / "dataset.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2))
