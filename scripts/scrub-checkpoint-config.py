#!/usr/bin/env python3
"""Hugging Face 上のチェックポイントから、ローカルの絶対パスを洗い落とす。

`--save_checkpoint_to_hub` で上がるチェックポイントには `train_config.json` が同梱され、
起動時の `--output_dir` がそのまま入る。その値が借用インスタンスのマウント先だと、
**モデルを公開した時点で調達元が読める**（docs/02-before-arm.md の「やらかし」節）。

このスクリプトはリポジトリ内の `train_config.json` を走査し、
ローカルの絶対パスに見える値だけをプレースホルダに置き換えて上書きする。

「絶対パス」の判定は形だけで行う。事業者名やパスのハードコードは持たない:

  - POSIX の絶対パス   /var/foo, /mnt/data
  - Windows のドライブ  C:\\Users\\foo
  - ホームの短縮形      ~/outputs

`org/model` のような Hugging Face のリポジトリ ID や
`huggingface/lerobot-gpu:latest` のようなイメージ名は絶対パスではないので残る。

使い方:
    export HF_TOKEN=...
    python scripts/scrub-checkpoint-config.py <user>/<model>            # 差分を出すだけ
    python scripts/scrub-checkpoint-config.py <user>/<model> --apply    # 実際に書き換える
"""

import argparse
import json
import os
import re
import sys

PLACEHOLDER = "<redacted-local-path>"
CONFIG_NAME = "train_config.json"

# 絶対パスらしさの判定。中身ではなく形で見る。
ABSOLUTE = re.compile(r"^(?:/|~/|[A-Za-z]:[\\/])")


def scrub(node, placeholder=PLACEHOLDER):
    """再帰的に絶対パスを置き換え、(結果, 変更点) を返す。"""
    changes = []

    def walk(value, path=""):
        if isinstance(value, dict):
            return {k: walk(v, f"{path}.{k}" if path else k) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v, f"{path}[{i}]") for i, v in enumerate(value)]
        if isinstance(value, str) and ABSOLUTE.match(value):
            changes.append((path, value))
            return placeholder
        return value

    return walk(node), changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo_id", help="対象の Hugging Face model リポジトリ (<user>/<model>)")
    ap.add_argument("--apply", action="store_true", help="実際に書き換える。既定は差分表示のみ")
    ap.add_argument("--placeholder", default=PLACEHOLDER, help=f"置換後の値 (既定: {PLACEHOLDER})")
    args = ap.parse_args()

    if not os.environ.get("HF_TOKEN"):
        print("HF_TOKEN が未設定。環境変数で渡すこと。", file=sys.stderr)
        return 2

    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("huggingface_hub が要る: pip install huggingface_hub", file=sys.stderr)
        return 2

    api = HfApi(token=os.environ["HF_TOKEN"])
    targets = [f for f in api.list_repo_files(args.repo_id) if f.endswith(CONFIG_NAME)]
    if not targets:
        print(f"{CONFIG_NAME} が見つからない: {args.repo_id}", file=sys.stderr)
        return 1

    print(f"{args.repo_id}: {CONFIG_NAME} を {len(targets)} 件見つけた")
    dirty = 0

    for remote in sorted(targets):
        local = hf_hub_download(args.repo_id, remote, token=os.environ["HF_TOKEN"])
        with open(local, encoding="utf-8") as fh:
            original = json.load(fh)

        cleaned, changes = scrub(original, args.placeholder)
        if not changes:
            print(f"  {remote}: 変更なし")
            continue

        dirty += 1
        for key, was in changes:
            print(f"  {remote}: {key}\n      - {was}\n      + {args.placeholder}")

        if args.apply:
            payload = json.dumps(cleaned, indent=4, ensure_ascii=False).encode()
            api.upload_file(
                path_or_fileobj=payload,
                path_in_repo=remote,
                repo_id=args.repo_id,
                repo_type="model",
                commit_message=f"Redact local paths from {remote}",
            )
            print("      -> アップロードした")

    if not args.apply and dirty:
        print(f"\n{dirty} 件に変更が要る。実際に書き換えるには --apply を付ける。")
    elif args.apply:
        print(f"\n{dirty} 件を書き換えた。公開前に中身をもう一度確認すること。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
