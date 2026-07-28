# 組立・モーター ID 設定・キャリブレーション

**状態: 未着手（実機待ち）**

このドキュメントは実機到着後に埋めていく。以下は事前に把握した手順の下書き。

公式手順: [LeRobot / SO-101](https://huggingface.co/docs/lerobot/so101)（関節ごとの組立動画あり）

## 所要時間の見積もり

商品説明には「組立 20 分」とあるが、実際にはもっとかかると見ている。

| 工程 | 見積もり | 実績 |
|---|---|---|
| 3D パーツのサポート材除去 | 1 時間 | _(未記入)_ |
| 組立（リーダー＋フォロワー） | 半日 | _(未記入)_ |
| モーター ID 設定 | 数時間 | _(未記入)_ |
| キャリブレーション | 1 時間 | _(未記入)_ |

モーター ID 設定は **サーボを 1 個ずつケーブルを差し替えながら**行う必要があり、ここが地味に時間を食う想定。

## 手順の下書き

### 0. LeRobot と Feetech SDK のインストール

```bash
pip install -e ".[feetech]"
```

### 1. USB ポートの特定

```bash
lerobot-find-port
```

指示に従って USB ケーブルを抜くと、どのポートがどちらのアームか判別できる。

Linux ではポートへのアクセス権が必要な場合がある。

```bash
sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1
```

### 2. モーター ID とボーレートの設定

サーボは初期状態で全て ID=1 になっているため、1 個ずつ固有 ID を振る。
設定は EEPROM に書かれるので**一度だけ**でよい。

```bash
# フォロワー
lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem585A0076841

# リーダー
lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem575E0031751
```

`gripper` → `wrist_roll` → … の順に、**その 1 個だけを基板に繋いだ状態**で Enter を押していく。
デイジーチェーンは全部終わってから繋ぐ。

### リーダーアームのギア比（参考）

リーダーは自重を支えつつ軽い力で動かせるよう、関節ごとにギア比が違うサーボを使う。

| リーダーアーム軸 | モーター | ギア比 |
|---|---|---|
| Base / Shoulder Pan | 1 | 1 / 191 |
| Shoulder Lift | 2 | 1 / 345 |
| Elbow Flex | 3 | 1 / 191 |
| Wrist Flex | 4 | 1 / 147 |
| Wrist Roll | 5 | 1 / 147 |
| Gripper | 6 | 1 / 147 |

フォロワーは 6 個すべて 1/345。**組立時に取り違えると動かないので要注意。**

### 3. キャリブレーション

リーダーとフォロワーが同じ物理姿勢で同じ値を返すように揃える。
**この工程は、あるロボットで学習したネットワークを別のロボットで動かすために重要。**

```bash
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem58760431551 \
    --robot.id=my_awesome_follower_arm
```

全関節を可動域の中央に置いてから Enter、その後で各関節を可動域いっぱいに動かす。
リーダーも同様に実施。

## 詰まったこと

_(実機到着後に記録)_

## 次

→ [04-first-policy.md](04-first-policy.md)
