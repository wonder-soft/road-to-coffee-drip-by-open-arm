#!/usr/bin/env python3
"""学習したポリシーを gym-hil 上で走らせ、成功率を測る。

`lerobot.rl.eval_policy` は MuJoCo のウィンドウを開いて目で見るためのもので、
数値が欲しいときには向かない。こちらは描画せずに N エピソード回して成功率を出す。

判定は環境自身の `_is_success()` を使う。
（`gym_hil` の PandaPickCube では TCP とキューブの距離 < 0.05m かつ持ち上げ > 0.1m）

使い方:
    python scripts/eval-gym-hil-policy.py --policy <user>/<model> --episodes 50
    python scripts/eval-gym-hil-policy.py --policy outputs/train/x/checkpoints/last/pretrained_model
"""

import argparse
import sys

import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", required=True, help="Hub の repo id、またはローカルの pretrained_model ディレクトリ")
    ap.add_argument("--episodes", type=int, default=50)
    ap.add_argument("--device", default="mps", choices=["cpu", "mps", "cuda"])
    ap.add_argument("--max-steps", type=int, default=100)
    ap.add_argument("--seed", type=int, default=10_000, help="記録時と重ならない範囲を使う")
    args = ap.parse_args()

    import gym_hil  # noqa: F401  gym への環境登録のために要る
    import gymnasium as gym
    import torch
    from lerobot.configs.policies import PreTrainedConfig
    from lerobot.policies.factory import get_policy_class, make_pre_post_processors

    # 正規化統計はチェックポイント側の preprocessor に入っているので、
    # データセットを持ち出さずに評価できる。
    policy_cfg = PreTrainedConfig.from_pretrained(args.policy)
    policy = get_policy_class(policy_cfg.type).from_pretrained(args.policy)
    policy.to(args.device)
    policy.eval()

    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=policy_cfg,
        pretrained_path=args.policy,
    )

    # 記録時と同じ設定でなければ観測の形が合わない
    env = gym.make("gym_hil/PandaPickCube-v0", image_obs=True, random_block_position=True)

    successes, lengths = 0, []
    for episode in range(args.episodes):
        obs, _ = env.reset(seed=args.seed + episode)
        policy.reset()
        solved = False

        for step in range(args.max_steps):
            # 正規化はプロセッサに任せる。生の観測をデータセットと同じキーで渡す。
            batch = {
                "observation.state": torch.from_numpy(
                    np.asarray(obs["agent_pos"], dtype=np.float32)
                ).unsqueeze(0),
            }
            for camera, image in obs.get("pixels", {}).items():
                # HWC uint8 -> BCHW float32 [0,1]
                tensor = torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0)
                batch[f"observation.images.{camera}"] = tensor.permute(2, 0, 1).unsqueeze(0)

            with torch.inference_mode():
                action = postprocessor(policy.select_action(preprocessor(batch)))

            obs, _reward, terminated, truncated, _info = env.step(
                np.asarray(action, dtype=np.float32).reshape(-1)
            )
            if env.unwrapped._is_success():
                solved, lengths = True, [*lengths, step + 1]
                break
            if terminated or truncated:
                break

        successes += solved
        print(f"  ep{episode:>3}: {'成功' if solved else '失敗'}")

    env.close()
    rate = successes / args.episodes
    print(f"\n成功率: {successes}/{args.episodes} = {rate:.1%}")
    if lengths:
        print(f"成功時の平均ステップ数: {np.mean(lengths):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
