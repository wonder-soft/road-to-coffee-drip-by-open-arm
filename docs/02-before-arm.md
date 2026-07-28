# 実機が届く前にやること

アームの到着を待つ間にソフト側を一周しておくと、届いた日に「組み立てて、データを録る」だけに集中できる。
**このページの内容は実機ゼロ・0 円でできる。**

---

## 到着前チェックリスト

| # | やること | 所要 | 状態 |
|---|---|---|---|
| 1 | [LeRobot の環境構築](#1-lerobot-の環境構築) | 1 時間 | **✅ 完了**（手元 Mac、2026-07-28） |
| 2 | [Hugging Face アカウントとトークン](#2-アカウントとトークンの運用) | 10 分 | 未 |
| 3 | [Weights & Biases アカウント](#2-アカウントとトークンの運用) | 10 分 | 未 |
| 4 | [SmolVLA を公開データセットでファインチューニング](#a-公開データセットで-smolvla-をファインチューニング) | 半日 | **🟡 スモークテスト完了**／本番は GPU 待ち |
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

#### 検証済み（2026-07-28）

**素の Ubuntu 22.04.5 LTS コンテナで完走することを確認した。**

| 項目 | 検証環境 | 結果 |
|---|---|---|
| ベース OS | Ubuntu 22.04.5 LTS | — |
| システム Python | 3.11.10 | **miniforge で 3.12 を用意して解決** |
| GPU | NVIDIA A100-SXM4-80GB / driver 580.159.04 | 認識 OK |
| インストール後 | LeRobot 0.6.1 / PyTorch **2.11.0+cu130** | `torch.cuda.is_available() == True` |
| VRAM 認識 | 79.2 GiB | OK |
| `HF_HOME` | `PERSIST_DIR=<永続ボリュームのマウント先>` を指定 | `$PERSIST_DIR/hf` に設定され `~/.lerobot_env` に記録された |

**システム Python が 3.11 の環境で `requires-python >= 3.12` をどう解決するか**が
このスクリプトの一番の勘所だが、miniforge 経由で問題なく通った。

#### Linux でだけ落ちるバグを 2 つ潰した

**Mac では通ったのに Linux で落ちた。** 素の Ubuntu で検証した価値が出た箇所。
どちらも「セットアップは成功したように見えて、学習がデータ読み込み直前で死ぬ」ため、
**GPU を確保してから気づく**タイプの不具合だった。

##### バグ 1: ffmpeg 8.x と torchcodec が噛み合わない

```
OSError: libavutil.so.60: cannot open shared object file: No such file or directory
OSError: Could not load this library: .../torchcodec/libtorchcodec_core8.so
[end of libtorchcodec loading traceback].
```

`conda install ffmpeg` は最新の 8.x を入れるが、torchcodec 0.11.1 が同梱する
各 `libtorchcodec_coreN.so` はどれもロードできず全滅する。

macOS で気づけなかったのは、`av` パッケージが同梱する ffmpeg 7 系の `.dylib` を
dyld が拾っていたため。Linux では同梱 `.so` が検索パスに載らないので露呈した。

→ **`ffmpeg=7.1.1` に固定した。** 公式 Installation ガイドも
「`libsvtav1` が無い、または torchcodec とバージョン不整合が出たら 7.1.1 に落とせ」としている。

##### バグ 2: システムの `libstdc++` が古くて `dlopen` が失敗する

7.1.1 に落としてもまだ落ちた。真因はこちら。

```
OSError: /lib/x86_64-linux-gnu/libstdc++.so.6: version `CXXABI_1.3.15' not found
         (required by .../lib/././libopenvino.so.2520)
```

conda の ffmpeg が引き込む `libopenvino` が新しい `libstdc++` を要求するのに対し、
`dlopen` が **Ubuntu 22.04 のシステム側の古い `libstdc++` を掴んでしまう**。
conda 環境には `libstdc++.so.6.0.34`（`CXXABI_1.3.15` を含む）があるので、
そちらを優先させれば解決する。

→ `~/.lerobot_env` に以下を追加した。

```bash
export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
```

##### 検証ステップを追加した

同じことを繰り返さないよう、`setup.sh` の最後で `torchcodec` のロードを確認するようにした。
失敗したら対処法を出して終わる。**セットアップ時点で気づければ、GPU 時間を無駄にしない。**

```bash
python -c "from torchcodec.decoders import VideoDecoder"
```

その他、`perl: Setting locale failed` が出るが無害。

そもそも **LeRobot は計算機が使い捨てである前提で設計されている**。
データセットは `--dataset.repo_id` で Hub から引き、成果物は `push_to_hub` で Hub に戻す。
ローカルに残すべき状態が少ないので、リセットは実質的な障害にならない。

トークン（`HF_TOKEN` / `WANDB_API_KEY`）は環境変数で毎回渡す。
**イメージにもリポジトリにも焼かない。**

### リセットを越えて学習を続ける

**LeRobot v0.6.1 は Hub のリポジトリ ID から直接学習を再開できる。**
インスタンスが消えてもローカルの run ディレクトリを必要としない。ソースで確認済み
（`src/lerobot/configs/train.py` / `src/lerobot/common/train_utils.py`）。

#### 1. 学習時にチェックポイントを Hub へ送る

```bash
lerobot-train \
  --policy.path=lerobot/smolvla_base \
  --policy.repo_id=${HF_USER}/my_smolvla \
  --save_checkpoint_to_hub=true \
  --dataset.repo_id=lerobot/svla_so100_pickplace \
  --steps=20000 \
  --output_dir=outputs/train/my_smolvla \
  --policy.device=cuda
```

- `--save_checkpoint_to_hub` は **デフォルト `false`**。明示的に有効にする必要がある
- **`--policy.repo_id` が必須**。指定しないと
  `save_checkpoint_to_hub requires --policy.repo_id.` で弾かれる
- 送り先は model リポジトリの `checkpoints/<step>/{pretrained_model,training_state}`

#### 2. 別のインスタンスで再開する

```bash
lerobot-train --resume=true --config_path=${HF_USER}/my_smolvla
```

- `--config_path` には**ローカルの `train_config.json` か、Hub のリポジトリ ID** を渡せる
- Hub リポジトリを渡すと、**最大ステップ数のチェックポイントが自動でダウンロードされる**
- 再開時の設定は**チェックポイント側のものが優先**される。
  ただし CLI の `--*` フラグは引き続き上書きできる
- 元の run ディレクトリが無いので、`outputs/train/<日付>/<時刻>_resume` に新しく展開される。
  場所を固定したければ `--output_dir` を明示する

Hub に push していないと
`No checkpoint found in '<repo>' under 'checkpoints/'. Was the run trained with --save_checkpoint_to_hub?`
というエラーになる。**`--save_checkpoint_to_hub=true` の付け忘れが唯一の落とし穴。**

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

## 2. アカウントとトークンの運用

```bash
# Hugging Face（データセット・モデルの push/pull に必要）
huggingface-cli login    # 新しい環境では `hf auth login`

# Weights & Biases（学習曲線の可視化）
wandb login
```

### 実験管理は W&B 一択

LeRobot に **TensorBoard も MLflow も入口がない**。`src/lerobot/configs/default.py` に
`WandBConfig` があるだけで、それ以外のトラッカーは実装されていない。

使い捨てインスタンスで回す以上、**ログをインスタンスの外に出す手段は実質これしかない**。
`--wandb.enable=true` と `WANDB_API_KEY` だけで動き、依存は `training` extra に含まれている。

> **W&B プロジェクトは private にし、repo には数値だけ転記する。**
> W&B はホスト名・GPU 情報・環境変数の一部を自動で収集する。
> プロジェクトを public にして repo からリンクすると、**そこから調達元が読める**。
> `--output_dir` にプロバイダ特有のパスを渡さないことにも注意する。

### 使い捨てインスタンスでの渡し方

対話ログインは毎回やっていられないので、**環境変数で渡す**。
`setup.sh` は `HF_TOKEN` / `WANDB_API_KEY` があれば自動でログインし、無ければ警告して続行する。

```bash
export HF_TOKEN=hf_xxxxxxxx
export WANDB_API_KEY=xxxxxxxx
bash setup.sh
```

> **トークンはリポジトリにもコンテナイメージにも焼かない。**
> `.gitignore` で `.env` / `*.token` / `*.key` を除外済み。
> HF トークンは push が必要なので **write 権限**、W&B は API key をそのまま使う。

### キャッシュを永続ボリュームに逃がす

`HF_HOME` を永続ボリュームに向けておくと、SmolVLA のベースモデル（450M）と
データセットをリセットのたびに落とし直さずに済む。

```bash
PERSIST_DIR=/path/to/volume bash setup.sh
# → HF_HOME=$PERSIST_DIR/hf に設定され、~/.lerobot_env に記録される
```

`PERSIST_DIR` を指定しない場合は `~/.cache/huggingface` になり、**インスタンスと一緒に消える**。
スモークテスト程度ならそれで構わないが、本番の学習では指定する。

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
  --policy.repo_id=${HF_USER}/my_smolvla \
  --save_checkpoint_to_hub=true \
  --dataset.repo_id=lerobot/svla_so100_pickplace \
  --batch_size=64 \
  --steps=20000 \
  --output_dir=outputs/train/my_smolvla \
  --job_name=my_smolvla_training \
  --policy.device=cuda \
  --wandb.enable=true
```

### 公式ドキュメントのコマンドは、そのままでは 2 回落ちる

v0.6.1 で実際に確認した。**GPU を借りる前に手元で潰しておくべき 2 つ。**

#### 落とし穴 1: `repo_id` が無いと起動しない

```
ValueError: 'repo_id' argument missing. Please specify it to push the model to the hub.
```

`--policy.path=lerobot/smolvla_base` はベースモデルの設定ごと読み込むが、
その設定には `push_to_hub=true` が入っている。一方 `repo_id` は空なので `validate()` で弾かれる
（`src/lerobot/configs/train.py:277-282`）。

- **Hub に上げる場合**: `--policy.repo_id=<user>/<name>` を渡す（上のコマンド）
- **手元で試すだけの場合**: `--policy.push_to_hub=false` を渡す

#### 落とし穴 2: カメラのキー名が合わない

```
ValueError: Feature mismatch between dataset/environment and policy config.
- Missing features: ['observation.images.camera1', 'observation.images.camera2', 'observation.images.camera3']
- Extra features: ['observation.images.top', 'observation.images.wrist']
```

`smolvla_base` は `camera1` / `camera2` / `camera3` を想定しているが、
`lerobot/svla_so100_pickplace` のキーは `top` / `wrist`。**公式が案内している組み合わせなのに噛み合わない。**

`--rename_map` で解決する。

```bash
--rename_map='{"observation.images.top": "observation.images.camera1", "observation.images.wrist": "observation.images.camera2"}'
```

**3 台ぶん埋める必要はない。** 検証ロジック（`src/lerobot/policies/utils.py:226-250`）は

- ポリシーの想定カメラ ⊆ データセットのカメラ、**または**
- データセットのカメラ ⊆ ポリシーの想定カメラ

のどちらかを満たせば通る。リネーム後は `{camera1, camera2} ⊆ {camera1, camera2, camera3}` となり後者が成立する。

なお `--rename_map` は**事前学習済みチェックポイントがある場合のみ**使える
（`--policy.path` または `--policy.pretrained_path` が必要）。

> 自分で録ったデータセットを使うときは、**収録時のカメラ名を `camera1` / `camera2` にしておく**ほうが
> 後々の取り回しが楽かもしれない。→ [04-first-policy.md](04-first-policy.md)

---

借用インスタンスで回すなら `--policy.repo_id` は必須。
ついでに `--save_checkpoint_to_hub=true` も付けておくと、
インスタンスが落ちても[続きから再開できる](#リセットを越えて学習を続ける)。

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

### 開発機（構築済み: 2026-07-28）

| 項目 | 値 |
|---|---|
| 機種 | Apple M2 Pro |
| メモリ | 32 GB |
| OS | macOS 14.6.1 (23G93) / arm64 |
| conda | miniforge 26.3.2 |
| Python | 3.12.13 |
| LeRobot | 0.6.1 |
| PyTorch | 2.11.0（MPS 利用可） |
| TorchCodec | 0.11.1 |
| ffmpeg | 8.1.2 (conda-forge, `libsvtav1` 有効) |
| MuJoCo | 3.8.1 |
| gym-hil | 0.1.14 |
| transformers | 5.5.4 |
| extras | `core_scripts,training,feetech,smolvla,hilserl` |

**Apple Silicon なので TorchCodec が使える**（macOS Intel だと pyav フォールバックになる）。
ただし本格的な学習を回すには非力なので、20k ステップ級は借用 GPU に投げる想定。

CLI は `lerobot-train` / `lerobot-record` / `lerobot-calibrate` / `lerobot-find-port` /
`lerobot-teleoperate` / `lerobot-rollout` / `mjpython` がすべて通ることを確認済み。

#### 構築時に分かったこと

- **`requires-python = ">=3.12"`**。システムの Python 3.11 では入らないので miniforge が要る
- **PyTorch は 2.11.0 が入った**。2.10 以上なのでシステム全体の ffmpeg でもよかったが、
  conda-forge 版のほうが `libsvtav1` の有無で悩まずに済む
- `opencv-python-headless` が入る。**GUI 表示が必要な場面では注意**（描画は rerun-sdk 側が担当）
- `feetech-servo-sdk` / `pyserial` / `hidapi` も同時に入るので、実機接続の準備は済んでいる

### 学習ログ

> **スペックと再現手順は詳しく、調達元は書かない。**
> GPU 型番・VRAM・所要時間は再現に必要なので残す。どこから借りたかは残さない。
> `nvidia-smi` の出力を貼るときはホスト名を落とし、**GPU 型番だけを転記する**。

| 日付 | 用途 | アクセラレータ | CPU / RAM | Python / LeRobot | batch | steps | 所要時間 |
|---|---|---|---|---|---|---|---|
| 2026-07-28 | SmolVLA スモークテスト | MPS (Apple M2 Pro) | M2 Pro / 32 GB | 3.12.13 / 0.6.1 | 2 | 2 | 約 1 分（うち学習 29 秒） |

#### スモークテストの結果（2026-07-28）

**完走した（exit 0）。** 学習ループ・チェックポイント保存まで手元の Mac で通ることを確認。

| 項目 | 実測 |
|---|---|
| 速度 | **約 11〜15 秒 / step**（MPS, batch_size=2） |
| チェックポイント | **1 ステップあたり 1.2 GB** |
| データセット | 448 MiB（`lerobot/svla_so100_pickplace`, 9 ファイル） |
| VLM バックボーン | `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`（489 weights） |

生成されたディレクトリ構造は、[Hub からの再開](#リセットを越えて学習を続ける)が期待する形と一致していた。

```
checkpoints/
├── last -> 000002
└── 000002/
    ├── pretrained_model/   # model.safetensors, config.json, train_config.json ...
    └── training_state/     # optimizer_state, scheduler_state, training_step, rng_state
```

**この速度では本番の 20k ステップは MPS では終わらない。** 借用 GPU が必須。
一方で、**パイプラインが通ることの確認は手元で完結する**ので、GPU を借りる前に必ずここまでやる。

チェックポイントが 1.2 GB/回 なので、`--save_checkpoint_to_hub` を使う場合は
保存間隔と永続ボリュームの容量に注意する。

#### 無害だが目立つ警告

macOS で以下が大量に出るが、動作には影響しない。

```
objc[…]: Class AVFFrameReceiver is implemented in both …/cv2/.dylibs/libavdevice… and …/av/.dylibs/libavdevice…
One of the two will be used. Which one is undefined.
```

`opencv-python-headless` と `av`、さらに Homebrew の ffmpeg が
それぞれ `libavdevice` を抱えているため。ログを読むときのノイズになるので、
`grep -v objc` などで落とすとよい。

---

## 次

→ [03-assembly.md](03-assembly.md)（組立の記録） / [90-references.md](90-references.md)（参考資料）
