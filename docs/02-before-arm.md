# 実機が届く前にやること

アームの到着を待つ間にソフト側を一周しておくと、届いた日に「組み立てて、データを録る」だけに集中できる。
**このページの内容は実機ゼロ・0 円でできる。**

---

## 到着前チェックリスト

| # | やること | 所要 | 状態 |
|---|---|---|---|
| 1 | [LeRobot の環境構築](#1-lerobot-の環境構築) | 1 時間 | 未 |
| 2 | [Hugging Face アカウントとトークン](#2-アカウント類) | 10 分 | 未 |
| 3 | [Weights & Biases アカウント](#2-アカウント類) | 10 分 | 未 |
| 4 | [SmolVLA を公開データセットでファインチューニング](#a-公開データセットで-smolvla-をファインチューニング) | 半日 | 未 |
| 5 | [gym-hil でテレオペ〜学習を一周](#b-gym-hil-でテレオペからデータ収集まで一周する) | 半日 | 未 |
| 6 | [撮影セットの設計](#3-撮影セットの設計) | 1 時間 | 未 |
| 7 | [工具と作業スペースの確保](#4-工具と作業スペース) | — | 未 |

---

## 役割分担

学習は借用した GPU インスタンスで回す。**毎回リセットされる前提**で組む。

| 場所 | 担当 |
|---|---|
| **手元の Mac** | gym-hil テレオペ、データセット記録・可視化、実機接続 |
| **借用 GPU インスタンス** | 学習のみ（SmolVLA / ACT） |
| **Hugging Face Hub** | データセットとチェックポイントの受け渡し |
| **W&B** | 学習ログ（インスタンスが消えても残る） |

**gym-hil のテレオペはクラウドに置けない。** MuJoCo の描画とキーボード/ゲームパッド入力が必要で、
ヘッドレスの GPU インスタンスとは相性が悪い。macOS では `mjpython` を使う。

リセットのコストは、リポジトリ直下の [`setup.sh`](../setup.sh) に閉じ込めてある。

```bash
# 素の Ubuntu コンテナから LeRobot 稼働まで
bash setup.sh

# 永続ボリュームがある場合（HF キャッシュを逃がして再ダウンロードを避ける）
PERSIST_DIR=/path/to/volume bash setup.sh
```

そもそも **LeRobot は計算機が使い捨てである前提で設計されている**。
データセットは `--dataset.repo_id` で Hub から引き、成果物は `push_to_hub` で Hub に戻す。
ローカルに残すべき状態が少ないので、リセットは実質的な障害にならない。

トークン（`HF_TOKEN` / `WANDB_API_KEY`）は環境変数で毎回渡す。
**イメージにもリポジトリにも焼かない。**

---

## 1. LeRobot の環境構築

`setup.sh` がやっていることの中身。手元の Mac に入れる場合はこちらを手で辿る。

公式手順: [LeRobot / Installation](https://huggingface.co/docs/lerobot/installation)

**Python 3.12 以上、PyTorch 2.10 以上**が要求される。システムの Python では足りないことが多いので conda（miniforge）を使う。

```bash
# miniforge のインストール（未導入の場合）
wget "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh

# 環境作成
conda create -y -n lerobot python=3.12
conda activate lerobot

# ffmpeg（TorchCodec の動画デコードに必要）
conda install ffmpeg -c conda-forge

# LeRobot 本体（ソースから）
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e ".[core_scripts,training,feetech,smolvla]"
```

### extras の選び方

base の `lerobot` は意図的に軽量で、必要なものは extras で足す設計になっている。

| extra | 中身 | 用途 |
|---|---|---|
| `dataset` | datasets, av, torchcodec, jsonlines | データセットの読み書き |
| `training` | dataset + accelerate, wandb | ポリシーの学習 |
| `hardware` | pynput, pyserial, deepdiff | 実機との接続 |
| `viz` | rerun-sdk | 記録・評価時の可視化 |
| **`core_scripts`** | dataset + hardware + viz | `lerobot-record` / `lerobot-replay` / `lerobot-calibrate` |
| `feetech` | Feetech SDK | **SO-101 のサーボ制御に必須** |
| `smolvla` | SmolVLA の依存 | SmolVLA を使う場合 |
| `pi` | π0 / π0.5 / π0-FAST の依存 | VLA を試す場合 |
| `hilserl` | gym-hil 等 | シミュレーション / HIL-SERL |
| `all` | 全部 | 迷ったらこれ |

面倒なら `pip install -e ".[all]"` でよい。

### ffmpeg の注意点

- **macOS Intel (x86_64) / Linux ARM / Windows + PyTorch < 2.8 では TorchCodec が使えず、自動的に `pyav` にフォールバックする。** その場合 ffmpeg のインストールは不要
- システム全体の ffmpeg（`brew install ffmpeg`）で済ませられるのは **PyTorch >= 2.10 の場合のみ**。それ以外は `conda install ffmpeg -c conda-forge` が必須
- `libsvtav1` 関連で詰まったら `conda install ffmpeg=7.1.1 -c conda-forge` に落とす

### 動作確認

```bash
conda activate lerobot
python -c "import lerobot; print(lerobot.__version__)"
lerobot-train --help
ffmpeg -encoders | grep svtav1
```

## 2. アカウント類

```bash
# Hugging Face（データセット・モデルの push/pull に必要）
huggingface-cli login    # 新しい環境では `hf auth login`

# Weights & Biases（学習曲線の可視化。任意だが強く推奨）
wandb login
```

> **トークンは絶対にリポジトリにコミットしない。** `.gitignore` で `.env` / `*.token` を除外済み。

## 3. 撮影セットの設計

これは「届く前にやっておくと効く」項目の筆頭。

**データセットを Hugging Face Hub に public で push すると、カメラ画像がそのまま公開される。**
50 エピソード分の背景（部屋、書類、モニタの中身）がすべて含まれる。

対策と、ついでの効能:

- **無地の背景紙を敷いた固定の撮影セット**を用意する。プライバシー対策になり、
  背景が固定されているほうが学習の観点でも素直（一石二鳥）
- 照明を固定する。時間帯で明るさが変わると、それ自体がノイズになる
- 物体の初期位置を**意図的にばらつかせる**設計をしておく（後述の 5 箇所 × 10 回）
- クランプで固定できる、端に余裕のある机を確保する

## 4. 工具と作業スペース

キットには**テーブルクランプ 4 個**が同梱されている（別途購入不要）。

別途あると詰まらないもの:

- **小さめのプラスドライバー** — 3D プリントパーツのサポート材除去に使う。
  公式も「小さいドライバーで下から剥がすのが楽」と書いている
- ニッパー
- USB ポートの空き。[リーダー・フォロワー・カメラで 3〜4 ポート必要](01-hardware.md#3-usb-ポートが足りない)

---

## A. 公開データセットで SmolVLA をファインチューニング

**ファインチューニングの体験そのものは、アームなしで完結する。**

[SmolVLA](https://huggingface.co/docs/lerobot/main/en/smolvla) は Hugging Face の軽量 VLA（450M）。
公式が公開データセットを使った手順を用意している。

```bash
pip install -e ".[smolvla]"

lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --dataset.repo_id=lerobot/svla_so100_pickplace \
  --batch_size=64 \
  --steps=20000 \
  --output_dir=outputs/train/my_smolvla \
  --job_name=my_smolvla_training \
  --policy.device=cuda \
  --wandb.enable=true
```

- ベースモデル: [`lerobot/smolvla_base`](https://hf.co/lerobot/smolvla_base)（450M）
- データセット: [`lerobot/svla_so100_pickplace`](https://huggingface.co/spaces/lerobot/visualize_dataset?path=%2Flerobot%2Fsvla_so100_pickplace%2Fepisode_0)
  — SmolVLA 論文で使われた実機 50 エピソード（5 箇所のキューブ位置 × 10 エピソード）
- 所要: **20k ステップで A100 単体約 4 時間**
- GPU がない場合: [公式 Colab ノートブック](https://colab.research.google.com/github/huggingface/notebooks/blob/main/lerobot/training-smolvla.ipynb)

> **Apple Silicon で回す場合**は `--policy.device=mps`。ただし 20k ステップは現実的な時間で終わらないので、
> 動作確認だけ手元で行い（`--steps=200` 程度）、本番は Colab に投げるのが素直。

### ここで得られる重要な数字

公式ドキュメントに、さらっとだが決定的なことが書いてある。

> We tried similar dataset with 25 episodes, and it was not enough leading to a bad performance.

**25 エピソードでは足りず、50 エピソードで成立した。**

1 エピソード 30 秒として、失敗のやり直しを含めれば **50 回のテレオペは半日仕事**。
アームの価格よりも、この作業量のほうが実質的なコストになる。

## B. gym-hil でテレオペからデータ収集まで一周する

[MuJoCo](https://mujoco.org) ベースの [gym-hil](https://github.com/huggingface/gym-hil) を使うと、
**実機と同じワークフロー**（テレオペ → データセット記録 → 学習 → 評価）をシミュレーション上で回せる。

Isaac Sim のような重量級は不要で、**MacBook（Apple Silicon）でも動く**。

```bash
pip install -e ".[hilserl]"
```

### 1. テレオペしてデータセットを録る

`env_config.json`:

```json
{
  "env": {
    "type": "gym_manipulator",
    "name": "gym_hil",
    "task": "PandaPickCubeKeyboard-v0",
    "fps": 10
  },
  "dataset": {
    "repo_id": "your_username/il_gym",
    "root": null,
    "task": "pick_cube",
    "num_episodes_to_record": 30,
    "replay_episode": null,
    "push_to_hub": true
  },
  "mode": "record",
  "device": "cuda"
}
```

- GPU がなければ `"device"` を `"mps"`（macOS）または `"cpu"` に
- ゲームパッド（Logicool F710 等）があれば `"task": "PandaPickCubeGamepad-v0"`

```bash
# Linux / NVIDIA GPU
python -m lerobot.rl.gym_manipulator --config_path path/to/env_config.json

# macOS（mjpython を使う。python だと描画が動かない）
mjpython -m lerobot.rl.gym_manipulator --config_path path/to/env_config.json
```

キーボード操作:

```
スペースキー           : 操作の有効化（押している間だけ動く）
矢印キー               : X-Y 平面の移動
Shift / Shift_R        : Z 軸の移動
Right Ctrl / Left Ctrl : グリッパーの開閉
ESC                    : 終了
```

ゲームパッドの場合は **`RB`（Human Take Over Pause Policy）を押している間だけ**操作が効く。

### 2. ACT を学習する

```bash
lerobot-train \
  --dataset.repo_id=${HF_USER}/il_gym \
  --policy.type=act \
  --output_dir=outputs/train/il_sim_test \
  --job_name=il_sim_test \
  --policy.device=cuda \
  --wandb.enable=true
```

デフォルト 100k ステップで **A100 約 1 時間**。

### 3. 評価する

```bash
python -m lerobot.rl.eval_policy --config_path=path/to/eval_config.json
```

参考: [Imitation Learning in Sim](https://huggingface.co/docs/lerobot/main/en/il_sim)

## C. SO-101 の MuJoCo モデル

SO-101 そのものをシミュレーション上で動かしたい場合、公式の MuJoCo モデルがある。

- [SO-ARM100/Simulation/SO101](https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation/SO101)
  — `so101_new_calib.xml`（新キャリブレーション、各関節の仮想ゼロが可動域の中央）
  / `so101_old_calib.xml`（旧、水平に伸ばしきった姿勢がゼロ）
- [so100-mujoco-sim](https://github.com/lachlanhurst/so100-mujoco-sim)
  — シミュレーションと実機を差し替え可能にする実装

---

## 実行環境の記録

再現性のため、学習を回した環境はここに追記していく。

### 開発機

| 項目 | 値 |
|---|---|
| 機種 | Apple M2 Pro |
| メモリ | 32 GB |
| OS | macOS 14.6.1 (23G93) / arm64 |
| ffmpeg | 8.1.2 (Homebrew) |
| アクセラレータ | MPS（Apple Silicon なので TorchCodec 対応） |

**Apple Silicon なので TorchCodec が使える**（macOS Intel だと pyav フォールバックになる）。
ただし本格的な学習を回すには非力なので、20k ステップ級は Colab か GPU マシンに投げる想定。

### 学習ログ

> **スペックと再現手順は詳しく、調達元は書かない。**
> GPU 型番・VRAM・所要時間は再現に必要なので残す。どこから借りたかは残さない。
> `nvidia-smi` の出力を貼るときはホスト名を落とし、**GPU 型番だけを転記する**。

| 日付 | 用途 | GPU / VRAM | CPU / RAM | CUDA / Python / LeRobot | ステップ数 | 所要時間 |
|---|---|---|---|---|---|---|
| _(未記入)_ | | | | | | |

---

## 次

→ [03-assembly.md](03-assembly.md)（組立の記録） / [90-references.md](90-references.md)（参考資料）
