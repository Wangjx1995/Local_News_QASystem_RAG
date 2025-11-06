# RAG-Demo for Janpan News

このプロジェクトは、`data/` に置いたデータ（例：日本ニュースの PDF/HTML/TXT）を**検索→（任意で再ランク）→生成**で回答するRAGの実装です。  
Windows ＋ Python 仮想環境で動作確認済み。

---

## 目次
- [1. 前提](#1-前提)
- [2. 仮想環境の構築](#2-仮想環境の構築)
- [3. データの差し替え](#3-データの差し替え)
- [4. インデックス作成](#4-インデックス作成)
- [5. API キーと .env 設定](#5-api-キーと-env-設定)
- [6. RAG への質問（実行例）](#6-rag-への質問実行例)
- [7. 基本機能と付加機能](#7-基本機能と付加機能)
- [8. よくあるエラーと対処](#8-よくあるエラーと対処)
- [9. セキュリティと運用の注意](#9-セキュリティと運用の注意)
- [10. ライセンス](#10-ライセンス)

---

## 1. 前提

- **Python** 3.11 を推奨（3.10/3.12 でも概ね可）
- OS: Windows 10/11（他 OS も可・コマンド例は一部差異あり）
- レポジトリ構成（抜粋）:
  ```text
  RAG/
  ├─ data/                  # 自分の資料（PDF/HTML/TXT など）
  ├─ storage/               # ベクトル索引（自動生成・配布不要）
  ├─ rag/
  │   ├─ embedding/         # Jina / OpenAI / Zhipu の埋め込み実装
  │   ├─ llm/               # OpenAI, InternLM2(互換API), NoLLM
  │   ├─ lexical/           # BM25（キーワード検索）
  │   ├─ rerank/            # Cross-Encoder 再ランク（任意）
  │   └─ vector_store.py
  └─ scripts/
      ├─ build_index.py     # 索引（埋め込み）を作成
      └─ ask.py             # 検索→（任意で再ランク）→生成で回答
  ```

---

## 2. 仮想環境の構築

### Windows（PowerShell）
```powershell
# プロジェクト直下で実行
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **注**: PowerShell の実行ポリシーで拒否されたら、そのシェル内だけ `Set-ExecutionPolicy -Scope Process Bypass` を実行してください。

### macOS / Linux
```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. データの差し替え

- 回答の根拠になる資料を **`data/`** に配置します（サブフォルダ OK）。
- 対応フォーマット：PDF / HTML / TXT（一般的な日本語文書を想定）。
- 例）月次ニュースを PDF で置く：
  ```text
  data/
  ├─ 2025年09月 日本ニュース・ダイジェスト.pdf
  ├─ 2025年10月 日本ニュース・ダイジェスト.pdf
  └─ ...（任意の資料）
  ```

---

## 4. インデックス作成

### Jina Embedding（推奨・高速）
`.env` に `JINA_API_KEY` を設定した上で：
```powershell
python -m scripts.build_index --data data --storage storage ^
  --chunk 600 --overlap 150 --chunker sent ^
  --embed-backend jina --embed-model jina-embeddings-v3
```

### OpenAI Embedding（将来切替したい場合の例）
```powershell
python -m scripts.build_index --data data --storage storage ^
  --chunk 600 --overlap 150 --chunker sent ^
  --embed-backend openai --embed-model text-embedding-3-small
```

- 主な引数
  - `--data`: 入力データのルートパス
  - `--storage`: 索引の出力先（既存があれば上書き）
  - `--chunk / --overlap`: 分割サイズとオーバーラップ
  - `--chunker`: `sent`（文単位）/ `fix`（固定長）等
  - `--embed-backend`: `jina` / `openai` / `zhipu`
  - `--embed-model`: 使用する埋め込みモデル名

---

## 5. API キーと .env 設定

プロジェクト直下に **`.env`** を作成し、必要な値を入れます。

```dotenv
# ===== Embedding（Jina） =====
JINA_API_KEY=your_jina_key
JINA_BASE_URL=https://api.jina.ai/v1

# ===== OpenAI（クラウド LLM）=====
OPENAI_API_KEY=sk-xxxx
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_TEMPERATURE=1        # 未設定ならデフォルトを使用（安全）

# ===== ローカル LLM（OpenAI 互換エンドポイント）=====
# 例: LM Studio（http://localhost:1234/v1） / Ollama（http://localhost:11434/v1）
INTERNLM2_BASE_URL=http://localhost:1234/v1
INTERNLM2_API_KEY=local
INTERNLM2_CHAT_MODEL=Qwen2.5-3B-Instruct
# INTERNLM2_TEMPERATURE=1     # 未設定なら送信しません（互換性のため）
```

> **注意**: `.env` は **Git 追跡対象外** にしてください（`.gitignore` に `.env` を入れる）。共有には `.`**env.example** を使いましょう。

---

## 6. RAG への質問（実行例）

### A. 証拠を表示する（LLM なし・検証用）
```powershell
python -m scripts.ask --storage storage --k 4 ^
  --llm-backend none --no-rerank --format full ^
  --q "高市早苗はいつ首相に指名された？"
```
- `--format full`: 命中文書の断片（ソース名 + スニペット）を一覧表示。

### B. 一行だけの簡潔回答（LLM なし・抽出）
```powershell
python -m scripts.ask --storage storage --k 4 ^
  --llm-backend none --format concise ^
  --q "東京都コアCPIは何%？"
```

### C. 自然文の完全回答（OpenAI を使用）
```powershell
python -m scripts.ask --storage storage --k 4 ^
  --llm-backend openai --llm-model gpt-5-mini ^
  --q "高市早苗はいつ首相に指名された？"
```

### D. 自然文の完全回答（ローカル LLM を使用）
**LM Studio** の Local Server を起動（例: `http://localhost:1234/v1`）後：
```powershell
python -m scripts.ask --storage storage --k 4 ^
  --llm-backend internlm2 --llm-model "Qwen2.5-3B-Instruct" ^
  --q "高市早苗はいつ首相に指名された？"
```
**Ollama** を使う場合（例: `http://localhost:11434/v1`）:
```powershell
python -m scripts.ask --storage storage --k 4 ^
  --llm-backend internlm2 --llm-model "qwen2.5:3b-instruct" ^
  --q "高市早苗はいつ首相に指名された？"
```

> LLM 互換 API は **未指定なら温度を送らない** 実装です（互換性のため）。温度を変えたい時は環境変数 `OPENAI_TEMPERATURE` / `INTERNLM2_TEMPERATURE` を設定してください。

---

## 7. 基本機能と付加機能

### 基本機能
- **自前データ**の取り込み（PDF/HTML/TXT）→ チャンク分割（`--chunk/--overlap`）
- **埋め込み**：Jina / OpenAI / Zhipu を切替可能（本 README では Jina 推奨）
- **ベクトル検索** + **BM25**（ハイブリッド検索）
- **RAG 生成**：OpenAI（クラウド） / 互換 API（LM Studio / Ollama） / NoLLM（抽出）

### 付加機能
- **Cross-Encoder 再ランク**（`sentence-transformers`）。`--no-rerank` で無効化可能。
- **表示モード**：
  - `--format full` … 証拠スニペットを列挙（検証向け）
  - `--format concise` … 一文回答（NoLLM 抽出向け）
- **BM25/ベクトルの重み調整**：`--vec-weight` / `--bm25-weight`
- **温度の安全化**：互換 API で 400 を避けるため、**デフォルトは temperature を送らない**（必要時のみ環境変数で指定）

> 将来の拡張案：`--strict`（証拠外情報は「情報不足」と回答）、`watch` による差分インデックス、評価スクリプト（RAGAS など）。

---

## 8. よくあるエラーと対処

- **`ModuleNotFoundError: dotenv`**  
  → `pip install python-dotenv`。`.venv` が有効か確認。

- **`JINA_API_KEY 未配置/未設定`**  
  → `.env` のキー名を確認し、`load_dotenv(find_dotenv(..., usecwd=True))` で読み込めているか確認。

- **Jina で `422`**（モデルタグ不一致）  
  → `jina-embeddings-v3` を使用。rerank も API の対応モデルへ。

- **OpenAI で `400 unsupported temperature`**  
  → 既定では temperature を送信しません。環境変数で明示したいときのみ設定。

- **`WinError 10061` / 接続拒否**（ローカル LLM）  
  → Local Server の起動と Base URL を確認。`GET /models` で疎通チェック。

- **PowerShell で venv が起動できない**  
  → `Set-ExecutionPolicy -Scope Process Bypass` を実行。

- **Hugging Face の symlink 警告（Windows）**  
  → 無視可。気になる場合は環境変数 `HF_HUB_DISABLE_SYMLINKS_WARNING=1`。

---

## 9. セキュリティと運用の注意
- `.env` は**絶対に** Git に入れない（`.gitignore` に登録）。
- 共有用には `.env.example` を配布（キー値は空欄・プレースホルダ）。
- 個人情報や秘匿情報は `data/` に入れない、もしくは暗号化・分離運用。

---

## 10. ライセンス
- このレポジトリ自体のライセンスに従います（`LICENSE` を参照）。
- 各 API / モデル（OpenAI, Jina, LM Studio/Ollama, HF モデル）は各提供元の利用規約に従ってください。

---

### 連絡
問題や改善提案は Issue へどうぞ。環境情報（OS/CPU/GPU、Python 版、エラー全文）を添付いただけると助かります。
