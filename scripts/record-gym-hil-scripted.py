#!/usr/bin/env python3
"""gym-hil の PandaPickCube を台本制御で解き、LeRobotDataset として記録する。

**なぜ台本なのか。** 本来この工程は人間がテレオペしてデモを作る
（`configs/gym-hil-record.json` の手順）。ただしそれは MuJoCo のウィンドウを開いて
キーボードを叩き続ける作業で、自動化できない。

一方このタスクの正解は単純で、キューブの真上に寄る → 降りる → 掴む → 持ち上げる、
の 4 段階しかない。台本で解けるなら、**人手を待たずにパイプラインを一周できる。**

制御器はシミュレータ内部の真値（キューブ位置・TCP 位置）を読む。
これは台本側だけの特権情報で、**記録されるデータセットには入らない**。
学習するポリシーはカメラ画像と関節状態から推論する必要がある。
デモをブートストラップする常套手段。

## 人間のデモとの違い

台本のデモは滑らかで一貫しており、失敗も逡巡も含まない。人間のデモとは分布が違う。

- パイプラインの検証には十分
- **「少ないデモから学べるか」の検証としては楽すぎる**。実機 (#22) の難しさは再現しない

使い方:
    python scripts/record-gym-hil-scripted.py --repo-id <user>/<name> --episodes 30
    python scripts/record-gym-hil-scripted.py --repo-id <user>/<name> --dry-run   # 成功率だけ見る
"""

import argparse
import sys

import numpy as np

# グリッパーの行動は [0, 2]。ラッパが [-1, 1] に直し、現在の開度への差分として加算される
# (`hil_wrappers.py`: `action[-1] - 1.0` → `clip(g + grasp_command, 0, 1)`)。
# 向きはドキュメントに書かれていないので実測で決めた。2 が閉じる側で 10/10 成功、
# 0 だと 0/10 だった。
GRIPPER_CLOSE = 2.0
GRIPPER_OPEN = 0.0

APPROACH_HEIGHT = 0.06  # キューブ上方この高さで planar を合わせる [m]
PLANAR_TOL = 0.02       # 真上と見なす水平距離 [m]
DESCEND_TOL = 0.005     # 掴める高さと見なす垂直距離 [m]
GAIN = 12.0             # 位置誤差 -> 正規化行動 の比例ゲイン
GRASP_HOLD = 3          # 掴んでから持ち上げるまで保持するステップ数


def scripted_action(env, grasped: bool, held: int):
    """真値から次の行動を決める。戻り値は (action, grasped, held)。"""
    u = env.unwrapped
    tcp = np.asarray(u._data.sensor("2f85/pinch_pos").data, dtype=np.float64)
    block = np.asarray(u._data.sensor("block_pos").data, dtype=np.float64)
    delta = block - tcp

    if grasped:
        target, grip = np.array([0.0, 0.0, 1.0]), GRIPPER_CLOSE
    elif np.linalg.norm(delta[:2]) > PLANAR_TOL:
        # 水平を合わせる。降りすぎないよう z はキューブ上方に留める
        clearance = APPROACH_HEIGHT - (tcp[2] - block[2])
        target = np.array([delta[0], delta[1], max(clearance, -0.02)])
        grip = GRIPPER_OPEN
    elif tcp[2] - block[2] > DESCEND_TOL:
        target, grip = delta, GRIPPER_OPEN
    else:
        target, grip = np.zeros(3), GRIPPER_CLOSE
        held += 1
        if held > GRASP_HOLD:
            grasped = True

    action = np.concatenate([np.clip(target * GAIN, -1.0, 1.0), [grip]])
    return action.astype(np.float32), grasped, held


def run_episode(env, seed: int, max_steps: int = 100):
    """1 エピソード実行し、(成功したか, フレーム列) を返す。"""
    obs, _ = env.reset(seed=seed)
    frames, grasped, held = [], False, 0

    for _ in range(max_steps):
        action, grasped, held = scripted_action(env, grasped, held)
        frames.append((obs, action))
        obs, _reward, terminated, truncated, _info = env.step(action)
        if env.unwrapped._is_success():
            return True, frames
        if terminated or truncated:
            break
    return False, frames


def build_features(sample_obs, action_dim: int) -> dict:
    features = {
        "action": {"dtype": "float32", "shape": (action_dim,), "names": ["dx", "dy", "dz", "gripper"]},
        "observation.state": {
            "dtype": "float32",
            "shape": tuple(np.shape(sample_obs["agent_pos"])),
            "names": None,
        },
    }
    for camera, frame in sample_obs.get("pixels", {}).items():
        features[f"observation.images.{camera}"] = {
            "dtype": "video",
            "shape": tuple(np.shape(frame)),
            "names": ["height", "width", "channel"],
        }
    return features


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-id", help="記録先の LeRobotDataset (<user>/<name>)")
    ap.add_argument("--episodes", type=int, default=30)
    ap.add_argument("--fps", type=int, default=10)
    ap.add_argument("--task", default="pick up the cube")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--push-to-hub", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="記録せず成功率だけ測る")
    args = ap.parse_args()

    if not args.dry_run and not args.repo_id:
        print("--repo-id が要る（--dry-run なら不要）", file=sys.stderr)
        return 2

    import gym_hil  # noqa: F401  gym への環境登録のために要る
    import gymnasium as gym

    # 実機の構成に寄せて 2 カメラ。位置をばらけさせないと全エピソードが同一になる。
    env = gym.make("gym_hil/PandaPickCube-v0", image_obs=True, random_block_position=True)

    if args.dry_run:
        wins = sum(run_episode(env, args.seed + i)[0] for i in range(args.episodes))
        print(f"成功 {wins}/{args.episodes}")
        env.close()
        return 0 if wins == args.episodes else 1

    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    sample_obs, _ = env.reset(seed=args.seed)
    dataset = LeRobotDataset.create(
        repo_id=args.repo_id,
        fps=args.fps,
        features=build_features(sample_obs, env.action_space.shape[0]),
        robot_type="panda_sim",
        use_videos=True,
    )

    recorded = failed = 0
    for i in range(args.episodes):
        # 失敗したエピソードは捨てて次の種を引く。台本が解けない配置が稀に出る。
        for attempt in range(5):
            success, frames = run_episode(env, args.seed + i * 100 + attempt)
            if success:
                break
        if not success:
            failed += 1
            print(f"  ep{i}: 5 回試して解けなかった。飛ばす")
            continue

        for obs, action in frames:
            frame = {
                "action": action,
                "observation.state": np.asarray(obs["agent_pos"], dtype=np.float32),
                "task": args.task,
            }
            for camera, image in obs.get("pixels", {}).items():
                frame[f"observation.images.{camera}"] = np.asarray(image)
            dataset.add_frame(frame)
        dataset.save_episode()
        recorded += 1
        print(f"  ep{i}: {len(frames)} フレーム記録")

    env.close()
    print(f"\n{recorded} エピソード記録（{failed} 件は解けずに除外）")

    if args.push_to_hub:
        dataset.push_to_hub()
        print(f"push した: {args.repo_id}")
        print("**public で作られる。背景に写るものが無いか確認すること。**")
    return 0


if __name__ == "__main__":
    sys.exit(main())
