#!/usr/bin/env python3
"""lerobot-train のログから学習曲線を CSV に抽出する。

W&B を使わずに回した run でも、学習曲線を repo に残せるようにするためのもの。
生ログには `--output_dir` などのパスがそのまま含まれており、
**そのまま commit するとプロバイダの調達元が漏れる**（実際にやらかした。
docs/02-before-arm.md の「やらかし」節を参照）。

このスクリプトが取り出すのは数値メトリクスだけなので、出力は安全に commit できる。

使い方:
    python scripts/extract-train-metrics.py train.log > docs/data/<run>.csv
    ssh <host> 'cat /path/to/train.log' | python scripts/extract-train-metrics.py - > out.csv
"""

import argparse
import csv
import re
import sys

# lerobot-train が 200 ステップごとに吐く進捗行の例:
#   step:12K smpl:781K ep:2K epch:39.77 loss:0.023 grdn:0.511 lr:3.5e-05
#
# 先頭の否定後読みが要る。tqdm の進捗と INFO ログが改行なしで連結されることがあり、
# `INFO ... ot_train.py:576` の `py:576` をフィールドとして拾ってしまうため。
FIELD = re.compile(r"(?<![\w.])(?P<key>[a-z_]+):(?P<val>[0-9][0-9.]*(?:[eE][+-]?\d+)?[KM]?)")
NEEDLE = re.compile(r"(?<![\w.])loss:")

# 念のための保険。数値以外を拾ってしまった場合に備えて、
# パスらしき文字列が出力に混ざっていないかを最後に検査する。
PATHISH = re.compile(r"/[A-Za-z0-9_.-]+/")

SUFFIX = {"K": 1_000, "M": 1_000_000}


def to_number(raw: str) -> float:
    """`781K` のような省略表記を数値に戻す。"""
    if raw and raw[-1] in SUFFIX:
        return float(raw[:-1]) * SUFFIX[raw[-1]]
    return float(raw)


def parse(lines):
    """進捗行だけを拾って dict の列にする。"""
    for line in lines:
        # tqdm がキャリッジリターンで上書きするので、まず行に割り直す
        for chunk in line.replace("\r", "\n").split("\n"):
            if not NEEDLE.search(chunk):
                continue
            row = {m["key"]: to_number(m["val"]) for m in FIELD.finditer(chunk)}
            if "step" in row and "loss" in row:
                yield row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logfile", help="lerobot-train のログ。'-' で標準入力")
    args = ap.parse_args()

    src = sys.stdin if args.logfile == "-" else open(args.logfile, encoding="utf-8", errors="replace")
    try:
        rows = list(parse(src))
    finally:
        if src is not sys.stdin:
            src.close()

    if not rows:
        print("進捗行が見つからなかった。ログの形式を確認すること。", file=sys.stderr)
        return 1

    # 列順は出現順を保ちつつ、step だけ先頭に固定する。
    # 並べ替えのキーは事前に確定させること（sort 中に index() を引くと壊れる）。
    seen = list(dict.fromkeys(k for r in rows for k in r))
    order = {name: i for i, name in enumerate(seen)}
    columns = sorted(seen, key=lambda c: (c != "step", order[c]))

    writer = csv.DictWriter(sys.stdout, fieldnames=columns, restval="")
    writer.writeheader()
    writer.writerows(rows)

    leaked = [c for c in columns if PATHISH.search(c)]
    if leaked:
        print(f"列名にパスらしき文字列がある: {leaked}", file=sys.stderr)
        return 1

    first, last = rows[0], rows[-1]
    print(
        f"{len(rows)} 行 / step {first['step']:.0f} -> {last['step']:.0f} / "
        f"loss {first['loss']:.4f} -> {last['loss']:.4f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
