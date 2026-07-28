# 最初のポリシー：データ収集と学習

**状態: 未着手（実機待ち）**

参考: [Imitation Learning on Real-World Robots](https://huggingface.co/docs/lerobot/en/il_robots)

## タスク設定（予定）

まずは定番の pick & place から。ハンドドリップに向けた最初の一歩として、
**軽量な物体を掴んで所定の位置に置く**を選ぶ。

## データ収集の設計

[02-before-arm.md](02-before-arm.md) で確認した通り、
公式が「25 エピソードでは足りず、50 エピソードで成立した」と明言している。
そのため **50 エピソード**を目標にする。

SmolVLA 論文のデータセットは「5 箇所の初期位置 × 10 エピソード」という構成だった。
**同じバリエーションを複数回繰り返す**構造が汎化に効いたと書かれているので、これに倣う。

| 項目 | 計画 |
|---|---|
| エピソード数 | 50 |
| 初期位置のバリエーション | 5 箇所 × 10 回 |
| 1 エピソードの長さ | 30 秒程度 |
| カメラ | 固定 1 台（正面）。余裕があれば手首 1 台を追加 |

### カメラの設定

> **カメラ名は `camera1` / `camera2` にしておくことを推奨する。**
>
> SmolVLA のベースモデルは `observation.images.camera1` / `camera2` / `camera3` を想定している。
> 別の名前（`top` / `wrist` など）で収録すると、学習のたびに `--rename_map` が必要になる。
> 実際、公式データセット `lerobot/svla_so100_pickplace` は `top` / `wrist` なので噛み合わない
> → [02-before-arm.md の落とし穴 2](02-before-arm.md#落とし穴-2-カメラのキー名が合わない)
>
> ACT だけを使うなら任意の名前でよいが、後から VLA を試したくなったときに効いてくる。

OpenCV 経由の USB カメラの場合:

```bash
--robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: \"MJPG\"}}"
```

`fourcc: "MJPG"` の指定が効くことがある。無指定だと生の YUV で転送され、
**USB 帯域が足りず fps が落ちる**ことがあるため。カメラを 2 台繋ぐ場合は特に。

複数台の場合はキーを増やす:

```bash
--robot.cameras="{ front: {...}, wrist: {...} }"
```

`index_or_path` の番号はマシンによって変わる。接続後に確認する。

### 撮影背景について（重要）

**データセットを Hugging Face Hub に public で push すると、カメラ画像がそのまま公開される。**
50 エピソード分の背景（部屋、書類、モニタの中身）がすべて含まれる。

対策として、**無地の背景紙を敷いた固定の撮影セット**を最初に用意する。
学習の観点でも背景が固定されているほうが素直なので、一石二鳥。

## 学習

### ACT（まずはこちら）

```bash
lerobot-train \
  --dataset.repo_id=${HF_USER}/<dataset> \
  --policy.type=act \
  --output_dir=outputs/train/first_policy \
  --job_name=first_policy \
  --policy.device=cuda \
  --wandb.enable=true
```

### SmolVLA（言語条件づけを試すなら）

```bash
lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --dataset.repo_id=${HF_USER}/<dataset> \
  --batch_size=64 \
  --steps=20000 \
  --output_dir=outputs/train/first_smolvla \
  --policy.device=cuda
```

## 実機での推論

```bash
lerobot-rollout \
  --strategy.type=base \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_follower_arm \
  --robot.cameras="{ front: {type: opencv, index_or_path: 8, width: 640, height: 480, fps: 30}}" \
  --task="<データ収集時と同じタスク説明を書く>" \
  --policy.path=${HF_USER}/<finetuned-model>
```

`--task` は**データセット記録時と同じ文言**にする必要がある。

低スペックなマシンで動かす場合は RTC オプションを検討する。

```bash
--inference.type=rtc
--inference.rtc.execution_horizon=10
--inference.rtc.max_guidance_weight=10.0
```

## 実行環境の記録

> **スペックと再現手順は詳しく、調達元は書かない。**

| 日付 | 用途 | GPU / VRAM | CPU / RAM | CUDA / Python / LeRobot | ステップ数 | 所要時間 |
|---|---|---|---|---|---|---|
| _(未記入)_ | | | | | | |

## 結果

_(実施後に記録)_

## 詰まったこと

_(実施後に記録)_

## 次

→ [99-coffee.md](99-coffee.md)（最終目標に向けて）
