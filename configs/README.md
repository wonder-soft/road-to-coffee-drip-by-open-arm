# configs

`lerobot` に渡す設定ファイル置き場。

## gym-hil（シミュレーションでの模倣学習）

実機が届く前に、テレオペ → データセット記録 → 学習 → 評価というワークフローを
一周するためのもの。[docs/02-before-arm.md](../docs/02-before-arm.md) の B 節に対応する。

| ファイル | 用途 |
|---|---|
| `gym-hil-record.json` | テレオペしてデータセットを 30 エピソード記録する |
| `gym-hil-eval.json` | 学習したポリシーをシミュレーション上で評価する |

### 記録

```bash
source ~/.lerobot_env   # または conda activate lerobot

# macOS は mjpython を使う。python だと描画ウィンドウが出ない
mjpython -m lerobot.rl.gym_manipulator --config_path configs/gym-hil-record.json
```

**このコマンドは人間の操作を必要とする。** MuJoCo のウィンドウが開くので、
そこでロボットを動かして 30 エピソードぶんのデモを実演する。

```
スペースキー           : 操作の有効化（押している間だけ動く）
矢印キー               : X-Y 平面の移動
Shift / Shift_R        : Z 軸の移動
Right Ctrl / Left Ctrl : グリッパーの開閉
ESC                    : 終了
```

ゲームパッド（Logicool F710 等）があれば `task` を `PandaPickCubeGamepad-v0` に変えると
格段に楽になる。その場合は **`RB`（Human Take Over Pause Policy）を押している間だけ**操作が効く。

### 学習

記録したデータセットで ACT を学習する。GPU があるならそちらで回す。

```bash
lerobot-train \
  --dataset.repo_id=letusfly85/il_gym_pick_cube \
  --policy.type=act \
  --output_dir=outputs/train/il_sim \
  --job_name=il_sim \
  --policy.device=cuda \
  --policy.repo_id=letusfly85/il_gym_pick_cube_act \
  --save_checkpoint_to_hub=true \
  --save_freq=5000 \
  --wandb.enable=true
```

> `--save_freq` を明示すること。**デフォルトは 20,000** なので、
> それより短い学習だと最後に 1 回しか保存されない。
>
> `--output_dir` にプロバイダ特有のパスを渡さないこと
> （[理由](../docs/02-before-arm.md#やらかし-学習設定からプロバイダのパスが公開された)）。

### 評価

```bash
mjpython -m lerobot.rl.eval_policy --config_path configs/gym-hil-eval.json
```

## 設定スキーマの出どころ

推測ではなく `lerobot` v0.6.1 のソースで確認したもの。

- `env`: `HILSerlRobotEnvConfig`（`src/lerobot/envs/configs.py`、`gym_manipulator` として登録）。
  `task` と `fps` は基底の `EnvConfig` が持つ
- `dataset`: `DatasetConfig`（`src/lerobot/rl/gym_manipulator.py`）。
  `repo_id` と `task` が必須、`num_episodes_to_record` の既定は 5
- `mode`: `"record"` / `"replay"` / `null`

## 環境の動作確認

物理エンジン部分は描画なしでも動くので、ウィンドウを開く前にここまで確認できる。

```bash
python -c "
import gymnasium as gym, gym_hil
env = gym.make('gym_hil/PandaPickCube-v0')
obs, info = env.reset(seed=0)
print(list(obs.keys()), env.action_space)
env.close()"
```

確認済みの結果（2026-07-28, Apple M2 Pro / macOS 14.6.1）:

```
['agent_pos', 'environment_state'] Box([-1. -1. -1.  0.], [1. 1. 1. 2.], (4,), float32)
```

行動空間は 4 次元（X, Y, Z の移動とグリッパー）。

> **macOS で `MUJOCO_GL=osmesa` は使えない**（`RuntimeError: invalid value`）。
> 環境変数は設定せず既定のバックエンドに任せる。

利用できる環境は 10 種類。`PandaPickCube` 系のほかに `PandaArrangeBoxes` 系があり、
それぞれ `Base` / `Keyboard` / `Gamepad` / `Viewer` の派生を持つ。
