# 参考資料

このプロジェクトで実際に参照した資料を集めていく。
**「読んだ」ものだけを載せる。** 未読のものは末尾の「積読」に置く。

**最終更新: 2026-07-28**

---

## 一次情報（公式）

### LeRobot

| 資料 | 内容 | 使いどころ |
|---|---|---|
| [LeRobot 本体](https://github.com/huggingface/lerobot) | リポジトリ | すべての起点 |
| [Installation](https://huggingface.co/docs/lerobot/installation) | 環境構築 | **Python 3.12 / PyTorch 2.10 以上。extras の一覧が重要** |
| [SO-101](https://huggingface.co/docs/lerobot/so101) | 組立・モーター ID・キャリブレーション | 関節ごとの動画あり。組立時はこれを見る |
| [Imitation Learning on Real-World Robots](https://huggingface.co/docs/lerobot/en/il_robots) | 実機でのデータ収集と学習 | 実機到着後の本命 |
| [Imitation Learning in Sim](https://huggingface.co/docs/lerobot/main/en/il_sim) | gym-hil での模倣学習 | 実機なしで一周できる |
| [Train RL in Simulation (HIL-SERL)](https://huggingface.co/docs/lerobot/en/hilserl_sim) | シミュレーションでの強化学習 | il_sim の次 |
| [SmolVLA](https://huggingface.co/docs/lerobot/main/en/smolvla) | 450M の軽量 VLA のファインチューニング | **公開データセットで実機なしに試せる** |
| [Koch v1.1](https://huggingface.co/docs/lerobot/koch) | 別系統のアーム | 比較用 |
| [LeRobot Discord](https://discord.com/invite/s3KuuzsPFb) | コミュニティ | 詰まったとき |

### ハードウェア

| 資料 | 内容 |
|---|---|
| [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) | 本家。BOM・STL・組立手順 |
| [Simulation/SO101](https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation/SO101) | MuJoCo モデル（`so101_new_calib.xml`） |
| [Seeed Studio Wiki: SoArm in LeRobot](https://wiki.seeedstudio.com/lerobot_so100m/) | 販売元による手順。**カメラ設定の実例が具体的** |
| [SVRC: SO-101 Specs](https://www.roboticscenter.ai/hardware/so-101) | スペック。**可搬 400g の出典** |

### モデル・データセット

| 資料 | 内容 |
|---|---|
| [`lerobot/smolvla_base`](https://hf.co/lerobot/smolvla_base) | SmolVLA ベースモデル（450M） |
| [`lerobot/svla_so100_pickplace`](https://huggingface.co/spaces/lerobot/visualize_dataset?path=%2Flerobot%2Fsvla_so100_pickplace%2Fepisode_0) | 実機 50 エピソード。**5 位置 × 10 回の構成が参考になる** |
| [Dataset Visualizer](https://huggingface.co/spaces/lerobot/visualize_dataset) | repo_id を貼るだけでデータセットを可視化 |
| [SmolVLA 論文](https://arxiv.org/pdf/2506.01844) | データ量と性能の関係 |

### シミュレーション

| 資料 | 内容 |
|---|---|
| [gym-hil](https://github.com/huggingface/gym-hil) | MuJoCo ベース。**Apple Silicon で動く** |
| [MuJoCo](https://mujoco.org) | 物理エンジン本体 |
| [so100-mujoco-sim](https://github.com/lachlanhurst/so100-mujoco-sim) | シムと実機を差し替え可能にする実装 |

---

## 日本語の記事

| 資料 | 内容 | 評価 |
|---|---|---|
| [npaka: 2026年のフィジカルAIとロボットAI](https://note.com/npaka/n/ne4cb1c2e3cfa) | LeRobot v0.6.0 と VLA の動向 | **本プロジェクトのきっかけ**。[00-why.md](00-why.md) に要約 |
| [npaka: SO-101 導入 (1) キットの入手](https://note.com/npaka/n/nfaa9db0834e5) | 購入の実体験 | 入手経路の比較に |
| [oggata: SO-101とは](https://zenn.dev/oggata/articles/ab22362076d9e8) | SO-101 の概論（後述の有料本の第1章相当） | 無料。全体像の把握に |
| [豆蔵デベロッパーサイト: LeRobotとSO-101で環境構築ガイド](https://developer.mamezou-tech.com/robotics/lerobot/lerobot_introduction/) | 環境構築 | 丁寧 |
| [Seeed K.K.: SO-101を組み立てて動かしてみた](https://lab.seeed.co.jp/entry/2025/09/19/120000) | 組立レポート | 販売元による |
| [Zenn (fusic): ロボットアーム SO-101 Arms の作り方](https://zenn.dev/fusic/articles/a5b0c062bb063c) | 組立 | |
| [技ラボ: SO-101を使った少ないデータでの模倣学習に挑戦](https://wazalabo.com/so-101-imitation-learning.html) | 少データでの学習 | **データ量の議論の参考に** |
| [3Dプリントで作るAI学習ロボットアーム「SO-101」まとめ](https://smartphone-zine.com/ai-robotarm-3dprint-review/) | 入手経路と価格帯 | |

### 有料書籍

| 資料 | 内容 |
|---|---|
| [oggata: SO-101ロボットアーム 実践ガイド（Zenn Books）](https://zenn.dev/oggata/books/41ce1497ddde6a) | **全 22 章の有料本。** 組立から模倣学習・強化学習・シミュレーション・VLA 基盤モデルまで |

本プロジェクトの射程とほぼ完全に重なる内容で、章立てだけでも参考になる。

- 第 3 章 部品調達とキット選択
- 第 4 章 組み立て手順 — リーダーアームとフォロワーアーム
- 第 5 章 ソフトウェア環境のセットアップ（macOS + Conda）
- 第 6 章 モーター設定とキャリブレーション
- 第 8 章 データセット作成の実践
- 第 9 章 主要データセットのエピソード長とステップ数
- 第 11 章 ACT による模倣学習
- 第 12 章 ロボット学習の主要手法と HIL-SERL の実践
- 第 13 章 推論デプロイと評価・改善ループ
- 第 14〜17 章 Isaac Sim / Cosmos / Genesis / World Models
- 第 18〜19 章 π0 / GR00T / π0.5 のファインチューン
- 第 20 章 LeRobot v0.6.0

**本リポジトリには本書の内容は転記しない**（有料コンテンツのため）。
参照が必要な箇所には章番号だけを書く。

---

## 論文

| 論文 | 関連 |
|---|---|
| [SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics](https://arxiv.org/pdf/2506.01844) | 使用するベースモデル |
| [Explainable Hierarchical Imitation Learning for Robotic Drink Pouring](https://arxiv.org/pdf/2105.07348) | **注湯タスク。評価時に実際には液体を出していない**点が示唆的 |
| [Data Scaling Laws in Imitation Learning for Robotic Manipulation](https://arxiv.org/pdf/2410.18647) | 必要なデータ量の見積もり |
| [LIBERO: 生涯ロボット学習のベンチマーク](https://medium.com/@deepkarkada/libero-simulation-benchmark-for-the-study-of-lifelong-robot-learning-583b786a96f6) | LeRobot が評価に対応 |

---

## 比較検討したハードウェア

| 資料 | 内容 |
|---|---|
| [OpenELAB: LeRobot Hardware Buying Guide](https://openelab.io/de/blogs/learn/lerobot-hardware-buying-guide-so-arm101-vs-koch-v1-1-vs-openarm-vs-lekiwi-vs-xlerobot) | SO-ARM101 / Koch v1.1 / OpenArm / LeKiwi / XLeRobot の比較 |
| [phospho starter pack](https://robots.phospho.ai/starter-pack) | 組立済み・カメラ付き・VR 操作。€995 |
| [Hiwonder LeRobot SO-ARM101](https://www.hiwonder.com/products/lerobot-so-101) | 組立済みグレード 4 種 |
| [AM-ARM](https://github.com/liyiteng/AM-ARM) | LeRobot 互換の別系統 |

---

## 購入先

| 店 | 商品 |
|---|---|
| [秋月電子 131169](https://akizukidenshi.com/catalog/g/g131169/) | SO-101 キット AC アダプター付 ¥46,280 |
| [秋月電子 131222](https://akizukidenshi.com/catalog/g/g131222/) | 3D プリントパーツ ¥7,280 |
| [秋月電子 131228](https://akizukidenshi.com/catalog/g/g131228/) | Pro 版 ¥50,200 |
| [Seeed Studio 日本](https://jp.seeedstudio.com/SO-ARM101-Low-Cost-AI-Arm-Kit-p-6426.html) | SO-ARM101 キット |

---

## 積読（未読）

まだ読んでいないが、後で当たる予定のもの。読んだら上のセクションに移す。

- [Isaac Teleop: Supported Teleop devices](https://nvidia.github.io/IsaacTeleop/main/getting_started/lerobot/devices.html) — テレオペデバイスの選択肢
- [leslider](https://github.com/pham-tuan-binh/leslider) — SO-101 用のスライダー拡張。可動範囲を広げる話
- [Training an SO-101 RL Agent to Grasp and Lift in MuJoCo](https://ggando.com/blog/so101-rl-lift/) — シミュレーションでの強化学習
- [Tiny struggles: Robotics Gyms & Experiments](https://www.tinystruggles.com/posts/robotics_gyms_and_experiments/) — シミュレータ選定の実体験
- LIBERO / Meta-World の実際の使い方（LeRobot 経由）
