#!/usr/bin/env bash
#
# 素の Ubuntu コンテナ / Linux マシンから、LeRobot が動く状態までを一発で作る。
#
# 借用した GPU インスタンスは毎回リセットされる前提なので、
# 「立ち上げ直すコスト」をこのスクリプトに閉じ込める。
#
# 特定の事業者に依存しない。永続ボリュームがある場合は PERSIST_DIR で渡す。
#
#   使い方:
#     bash setup.sh                        # ホームディレクトリに構築
#     PERSIST_DIR=/mnt/vol bash setup.sh   # 永続ボリュームに HF キャッシュを置く
#     EXTRAS="all" bash setup.sh           # extras を変える
#
#   実行後は毎回:
#     source ~/.lerobot_env
#
set -euo pipefail

# --- 設定（環境変数で上書き可能） -------------------------------------------
PY_VERSION="${PY_VERSION:-3.12}"
ENV_NAME="${ENV_NAME:-lerobot}"
LEROBOT_DIR="${LEROBOT_DIR:-$HOME/lerobot}"
CONDA_DIR="${CONDA_DIR:-$HOME/miniforge3}"
EXTRAS="${EXTRAS:-core_scripts,training,feetech,smolvla,hilserl}"

# 永続ボリュームがあれば HF のキャッシュをそこに置く。
# 450M のベースモデルやデータセットを毎回落とし直さずに済む。
# 空なら通常のホーム配下（= インスタンスと一緒に消える）。
PERSIST_DIR="${PERSIST_DIR:-}"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }

# --- 1. システム依存 --------------------------------------------------------
log "システムパッケージを入れる"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    git curl wget ca-certificates build-essential cmake pkg-config \
    python3-dev libgl1 libglib2.0-0
else
  warn "apt-get が無い。システム依存の導入はスキップする"
fi

# --- 2. miniforge -----------------------------------------------------------
if [ ! -d "$CONDA_DIR" ]; then
  log "miniforge を入れる -> $CONDA_DIR"
  MF_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
  curl -fsSL "$MF_URL" -o /tmp/miniforge.sh
  bash /tmp/miniforge.sh -b -p "$CONDA_DIR"
  rm -f /tmp/miniforge.sh
else
  log "miniforge は既にある -> $CONDA_DIR"
fi

# shellcheck disable=SC1091
source "$CONDA_DIR/etc/profile.d/conda.sh"

# --- 3. conda 環境 ----------------------------------------------------------
if ! conda env list | grep -qE "^${ENV_NAME}\s"; then
  log "conda 環境を作る (python ${PY_VERSION})"
  conda create -y -n "$ENV_NAME" "python=${PY_VERSION}"
else
  log "conda 環境は既にある -> ${ENV_NAME}"
fi
conda activate "$ENV_NAME"

# --- 4. ffmpeg --------------------------------------------------------------
# TorchCodec の動画デコードに必要。
# PyTorch < 2.10 ではシステムの ffmpeg にリンクできないので conda 経由で入れる。
log "ffmpeg を入れる (conda-forge)"
conda install -y -q ffmpeg -c conda-forge

# --- 5. LeRobot -------------------------------------------------------------
if [ ! -d "$LEROBOT_DIR/.git" ]; then
  log "LeRobot を clone する -> $LEROBOT_DIR"
  git clone --depth 1 https://github.com/huggingface/lerobot.git "$LEROBOT_DIR"
else
  log "LeRobot は既にある。更新する"
  git -C "$LEROBOT_DIR" pull --ff-only || warn "pull に失敗した。既存のまま進む"
fi

log "LeRobot を入れる (extras: ${EXTRAS})"
pip install --upgrade pip -q
pip install -e "${LEROBOT_DIR}[${EXTRAS}]"

# --- 6. キャッシュの永続化 --------------------------------------------------
if [ -n "$PERSIST_DIR" ]; then
  log "HF キャッシュを永続ボリュームに向ける -> $PERSIST_DIR"
  mkdir -p "$PERSIST_DIR/hf" "$PERSIST_DIR/outputs"
  export HF_HOME="$PERSIST_DIR/hf"
else
  warn "PERSIST_DIR 未指定。キャッシュはインスタンスと一緒に消える"
  export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
fi

# --- 7. 毎回読み込む環境ファイル --------------------------------------------
cat > "$HOME/.lerobot_env" <<EOF
# setup.sh が生成。シェルを開くたびに source する。
source "${CONDA_DIR}/etc/profile.d/conda.sh"
conda activate ${ENV_NAME}
export HF_HOME="${HF_HOME}"
export LEROBOT_DIR="${LEROBOT_DIR}"
EOF
log "環境ファイルを書いた -> ~/.lerobot_env"

# --- 8. 認証 ----------------------------------------------------------------
# トークンは環境変数で渡す。イメージにもリポジトリにも焼かない。
log "認証状態を確認する"
if [ -n "${HF_TOKEN:-}" ]; then
  huggingface-cli login --token "$HF_TOKEN" --add-to-git-credential 2>/dev/null \
    || hf auth login --token "$HF_TOKEN" 2>/dev/null \
    || warn "HF へのログインに失敗した。手動で実行すること"
else
  warn "HF_TOKEN 未設定。データセット/モデルの push には 'huggingface-cli login' が必要"
fi

if [ -n "${WANDB_API_KEY:-}" ]; then
  wandb login "$WANDB_API_KEY" >/dev/null 2>&1 || warn "W&B へのログインに失敗した"
else
  warn "WANDB_API_KEY 未設定。学習ログを残すなら 'wandb login' を実行すること"
fi

# --- 9. 動作確認 ------------------------------------------------------------
log "動作確認"
python - <<'PY'
import torch, lerobot
print(f"lerobot     : {getattr(lerobot, '__version__', 'unknown')}")
print(f"torch       : {torch.__version__}")
print(f"cuda        : {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"gpu         : {torch.cuda.get_device_name(0)}")
    print(f"vram        : {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GiB")
PY

lerobot-train --help >/dev/null 2>&1 && echo "lerobot-train : ok" || warn "lerobot-train が動かない"

cat <<'EOF'

----------------------------------------------------------------------
セットアップ完了。

  次のシェルからは:
      source ~/.lerobot_env

  動作確認（短いステップ数で回してみる）:
      lerobot-train \
        --policy.path=lerobot/smolvla_base \
        --dataset.repo_id=lerobot/svla_so100_pickplace \
        --batch_size=8 --steps=100 \
        --output_dir=outputs/train/smoke \
        --policy.device=cuda

  本番の学習では、インスタンスが消えても続きから再開できるように
  チェックポイントを Hub に送っておく:
      --policy.repo_id=<user>/<name> --save_checkpoint_to_hub=true

  別インスタンスでの再開:
      lerobot-train --resume=true --config_path=<user>/<name>

  実行環境は docs/02-before-arm.md の「学習ログ」表に記録すること。
  GPU 型番・VRAM・所要時間は書く。調達元は書かない。
----------------------------------------------------------------------
EOF
