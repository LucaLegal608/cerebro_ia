import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

st.set_page_config(
    page_title="L.U.C.A IA (BETA v1.2) — Lógica Unificada de Conhecimento e Ação",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
banco_memoria.iniciar_banco()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "BETA • v1.2"

def obter_data_hora_atual():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias_semana[agora.weekday()]})")

MENSAGEM_INICIAL = "Sistemas inicializados! 🤖⚡ Eu sou a **L.U.C.A IA** (*Lógica Unificada de Conhecimento e Ação* — **BETA v1.2**). Estou online para ajudar com **qualquer tarefa do seu dia a dia** — estudos, programação, ideias criativas, receitas ou qualquer dúvida. Como posso ajudar agora?"

if "conversas" not in st.session_state:
    id_inicial = str(uuid.uuid4())
    st.session_state.conversas = {id_inicial: {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}}
    st.session_state.conversa_atual = id_inicial

def criar_nova_conversa():
    novo_id = str(uuid.uuid4())
    st.session_state.conversas[novo_id] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}
    st.session_state.conversa_atual = novo_id

def excluir_conversa(id_conv):
    if len(st.session_state.conversas) > 1:
        del st.session_state.conversas[id_conv]
        if st.session_state.conversa_atual == id_conv:
            st.session_state.conversa_atual = list(st.session_state.conversas.keys())[-1]
    else:
        st.session_state.conversas[id_conv] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}

# CSS AVANÇADO: TEMA FUTURISTA / CYBERPUNK NEON
st.markdown("""
<style>
    @import url('https://googleapis.com');

    /* Fundo principal estilo espaço profundo */
    .stApp {
        background: radial-gradient(circle at top right, #0B192C 0%, #050811 60%, #020408 100%);
        color: #E2E8F0;
        font-family: 'Inter', sans-serif;
    }

    /* Esconde barra superior padrão do Streamlit */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Barra lateral futurista */
    section[data-testid="stSidebar"] {
        background-color: rgba(8, 14, 28, 0.92) !important;
        border-right: 1px solid rgba(0, 243, 255, 0.25);
        box-shadow: 4px 0 25px rgba(0, 243, 255, 0.05);
    }

    /* Banner Principal Cyberpunk */
    .cyber-banner {
        background: linear-gradient(135deg, rgba(13, 25, 48, 0.85) 0%, rgba(28, 16, 56, 0.85) 100%);
        backdrop-filter: blur(12px);
        padding: 1.8rem 2rem;
        border-radius: 16px;
        border: 1px solid rgba(0, 243, 255, 0.45);
        box-shadow: 0 0 25px rgba(0, 243, 255, 0.15), inset 0 0 15px rgba(157, 78, 221, 0.15);
        margin-bottom: 1.5rem;
    }
    .cyber-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00F3FF 0%, #7B2CBF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: 1px;
    }
    .cyber-sub {
        color: #38BDF8;
        font-size: 1rem;
        font-weight: 600;
        margin-top: 4px;
        letter-spacing: 0.5px;
    }
    .badge-neon {
        display: inline-block;
        background: rgba(0, 243, 255, 0.12);
        border: 1px solid #00F3FF;
        color: #00F3FF;
        font-family: 'Orbitron', sans-serif;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
        box-shadow: 0 0 10px rgba(0, 243, 255, 0.4);
        margin-left: 10px;
        vertical-align: middle;
    }
    .cyber-desc {
        color: #CBD5E1;
        margin-top: 0.7rem;
        font-size: 0.98rem;
    }

    /* Botões Neon */
    .stButton > button {
        border-radius: 10px !important;
        border: 1px solid rgba(0, 243, 255, 0.35) !important;
        background: rgba(15, 23, 42, 0.75) !important;
        color: #E0F2FE !important;
        transition: all 0.25s ease !important;
    }
    .stButton > button:hover {
        border-color: #00F3FF !important;
        box-shadow: 0 0 15px rgba(0, 243, 255, 0.45) !important;
        transform: translateY(-1px);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0284C7 0%, #7C3AED 100%) !important;
        border: 1px solid #00F3FF !important;
        color: white !important;
        font-weight: 700 !important;
    }

    /* Balões do Chat estilo Holograma */
    [data-testid="stChatMessage"] {
        background: rgba(15, 23, 42, 0.65) !important;
        border: 1px solid rgba(56, 189, 248, 0.22) !important;
        border-radius: 14px !important;
        padding: 1rem !important;
        margin-bottom: 0.7rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }

    /* Caixa de digitação inferior */
    [data-testid="stChatInput"] {
        border-radius: 14px !important;
        border: 1px solid rgba(0, 243, 255, 0.4) !important;
        background-color: rgba(10, 18, 36, 0.9) !important;
    }
</style>
""", unsafe_allow_html=True)

def ler_dna_criador():
    try:
        with open("perfil_cerebro.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Projeto criado por Luca de Brito Ferreira."

def gerar_resposta(mensagem, historico, instrucao_sistema, temperatura):
    tempo_exato = obter_data_hora_atual()
    sistema_completo = f"{instrucao_sistema}\n\n[DADO INTERNO SILENCIOSO - DATA E HORA ATUAL EM BRASÍLIA: {tempo_exato}. NUNCA imprima esse colchete na resposta. Use essa informação apenas se o usuário perguntar que dia é hoje ou que horas são.]"
    mensagens_formatadas = [{"role": "system", "content": sistema_completo}]
    for item in historico[-10:]:
        mensagens_formatadas.append({"role": item["role"], "content": item["content"]})
    mensagens_formatadas.append({"role": "user", "content": mensagem})

    modelos_disponiveis = []
    try:
        for m in client.models.list().data:
            if not any(x in m.id.lower() for x in ["whisper", "guard", "tts", "vision"]):
                modelos_disponiveis.append(m.id)
    except Exception as e:
        return f"⚠️ Erro na chave da API: {e}"

    modelos_disponiveis.sort(key=lambda x: ("llama-3.3" not in x and "70b" not in x and "120b" not in x, x))

    ultimo_erro = ""
    for modelo in modelos_disponiveis:
        try:
            resposta = client.chat.completions.create(model=modelo, messages=mensagens_formatadas, temperature=temperatura)
            return resposta.choices.message.content
        except Exception as erro:
            ultimo_erro = str(erro)
            time.sleep(1)
            continue

    return f"⚠️ Não foi possível responder agora. Detalhe técnico: {ultimo_erro}"

def processar_envio_publico(texto_usuario):
    conv_ativa = st.session_state.conversas[st.session_state.conversa_atual]
    if conv_ativa["titulo"] == "Nova conversa":
        conv_ativa["titulo"] = texto_usuario[:26] + ("..." if len(texto_usuario) > 26 else "")
    conv_ativa["mensagens"].append({"role": "user", "content": texto_usuario})
    instrucao_pub = f"Você é a 'L.U.C.A IA' (Lógica Unificada de Conhecimento e Ação), versão {VERSAO_IA} (em fase de desenvolvimento), criada por Luca de Brito Ferreira. IDIOMA OBRIGATÓRIO: Fale EXCLUSIVAMENTE em Português do Brasil natural, fluido e amigável (nunca use português de Portugal como 'oiça'). CONTEXTO DO CRIADOR (use apenas se perguntarem sobre o canal Luca Legal): {ler_dna_criador()}. ATUALIZAÇÕES SALVAS: {banco_memoria.buscar_todas_notas()}. DIRETRIZES: 1) Ajude com absolutamente qualquer assunto do dia a dia de forma leve, direta e inteligente. 2) Nunca trate o visitante como dono do sistema. 3) Converse de forma humana e natural."
    resp = gerar_resposta(texto_usuario, conv_ativa["mensagens"][:-1], instrucao_pub, 0.7)
    conv_ativa["mensagens"].append({"role": "assistant", "content": resp})

# BARRA LATERAL FUTURISTA
with st.sidebar:
    st.markdown(f"<div style='font-family:Orbitron; font-size:1.35rem; font-weight:800; color:#00F3FF;'>🤖 L.U.C.A IA</div>", unsafe_allow_html=True)
    st.caption(f"Lógica Unificada de Conhecimento e Ação")
    st.caption(f"🕒 {obter_data_hora_atual()}")
    
    if st.button("➕ Nova Sessão Neural", use_container_width=True, type="primary"):
        criar_nova_conversa()
        st.rerun()

    st.markdown("### 📡 Histórico de Sessões")
    for id_conv in reversed(list(st.session_state.conversas.keys())):
        dados_conv = st.session_state.conversas[id_conv]
        col_titulo, col_del = st.columns([0.82, 0.18])
        icone_chat = "💠" if id_conv == st.session_state.conversa_atual else "💬"
        with col_titulo:
            if st.button(f"{icone_chat} {dados_conv['titulo']}", key=f"btn_{id_conv}", use_container_width=True):
                st.session_state.conversa_atual = id_conv
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{id_conv}", help="Apagar conversa"):
                excluir_conversa(id_conv)
                st.rerun()

    st.divider()
    st.caption(f"Núcleo: 🟢 Online • `{VERSAO_IA}`")
    st.caption("Criado por Luca de Brito Ferreira")
    st.caption("⚠️ Esta IA está em fase de desenvolvimento.")

