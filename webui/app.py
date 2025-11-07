import os
from dotenv import load_dotenv
import streamlit as st
from rag_client import ask_with_evidence

# .env を読み込む（API キー、OpenAI/Jina/ローカル LLM の設定など）
load_dotenv()

st.set_page_config(page_title="RAG Chat", page_icon="🗂️", layout="wide")

# ---- Sidebar: パラメータ ----
st.sidebar.header("設定")
storage = st.sidebar.text_input("インデックス保存先 (storage)", value="storage")
k = st.sidebar.slider("Top-K（取得する文書数）", min_value=1, max_value=12, value=4, step=1)
llm_backend = st.sidebar.selectbox(
    "LLM バックエンド", options=["openai", "internlm2", "none"], index=0,
    help="openai=クラウド / internlm2=OpenAI 互換のローカル・プライベート（LM Studio・Ollama 等）/ none=抽出のみ（生成なし）"
)
llm_model = st.sidebar.text_input(
    "LLM モデル名", value="gpt-5-mini",
    help="バックエンドが none の場合は無視されます。internlm2 はローカル/私有エンドポイント側のモデル名に合わせてください。"
)
rerank = st.sidebar.checkbox("Cross-Encoder 再ランク付けを有効化", value=True,
                             help="オフにすると --no-rerank を付与します。")

st.sidebar.markdown("---")
if st.sidebar.button("会話をクリア", use_container_width=True):
    st.session_state.messages = []

# ---- Main: チャット UI ----
st.title("RAG Chat For Japan News(Streamlit)")
st.caption("ChatGPT 風にコーパスへ質問。OpenAI / 互換 API / 抽出のみ（生成なし）に対応。")

if "messages" not in st.session_state:
    st.session_state.messages = []

# これまでのメッセージを描画
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("evidence"):
            with st.expander("📎 根拠を見る（ヒットした断片）", expanded=False):
                st.code(m["evidence"])

# 入力欄
user_input = st.chat_input("質問を入力して Enter …")
if user_input:
    # ユーザー発言を表示
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # RAG を呼び出し
    with st.chat_message("assistant"):
        with st.spinner("検索と生成中…"):
            answer, evidence = ask_with_evidence(
                user_input, storage=storage, k=k,
                llm_backend=llm_backend, llm_model=llm_model, rerank=rerank
            )
            st.markdown(answer if answer else "_（結果なし／失敗）_")
            if evidence:
                with st.expander("📎 根拠を見る（ヒットした断片）", expanded=False):
                    st.code(evidence)

    # アシスタント出力を履歴に保存
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer if answer else "_（結果なし／失敗）_",
        "evidence": evidence
    })
