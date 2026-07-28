# 実機が届く前にやること

アームの到着を待つ間にソフト側のループを一周しておくと、
届いた日に「データを録る」だけに集中できる。**どちらも実機ゼロ・0 円でできる。**

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

### ここで得られる重要な数字

公式ドキュメントに、さらっとだが決定的なことが書いてある。

> We tried similar dataset with 25 episodes, and it was not enough leading to a bad performance.

**25 エピソードでは足りず、50 エピソードで成立した。**

1 エピソード 30 秒として、失敗のやり直しを含めれば **50 回のテレオペは半日仕事**。
アームの価格よりも、この作業量のほうが実質的なコストになる。
撮影セットアップ（背景、照明、物体の初期位置のばらつかせ方）を先に設計しておく価値がある。

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

# macOS
mjpython -m lerobot.rl.gym_manipulator --config_path path/to/env_config.json
```

キーボード操作:

```
スペースキー      : 操作の有効化（押している間だけ動く）
矢印キー          : X-Y 平面の移動
Shift / Shift_R   : Z 軸の移動
Right Ctrl / Left Ctrl : グリッパーの開閉
ESC               : 終了
```

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
- [so100-mujoco-sim](https://github.com/lachlanhurst/so100-mujoco-sim)
  — シミュレーションと実機を差し替え可能にする実装

## 実行環境の記録

再現性のため、学習を回した環境はここに追記していく。

| 日付 | 用途 | CPU / GPU / VRAM / RAM | OS / Python / LeRobot | 所要時間 |
|---|---|---|---|---|
| _(未記入)_ | | | | |

## 次

→ [03-assembly.md](03-assembly.md)（組立の記録）
