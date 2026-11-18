import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

st.set_page_config(
    page_title="L.U.C.A IA (BETA v1.4) — Lógica Unificada de Conhecimento e Ação",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)
banco_memoria.iniciar_banco()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "BETA • v1.4"

def obter_data_hora_atual():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias_semana[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! ✨ Eu sou a **L.U.C.A IA** (*Lógica Unificada de Conhecimento e Ação* — **BETA v1.4**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — estudos, ideias, textos, programação ou dúvidas gerais. Como posso ajudar hoje?"

if "conversas" not in st.session_state:
    id_inicial = str(uuid.uuid4())
    st.session_state.conversas = {id_inicial: {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}}
    st.session_state.conversa_atual = id_inicial

if "modo_tela" not in st.session_state:
    st.session_state.modo_tela = "chat"

def criar_nova_conversa():
    novo_id = str(uuid.uuid4())
    st.session_state.conversas[novo_id] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}
    st.session_state.conversa_atual = novo_id
    st.session_state.modo_tela = "chat"

def excluir_conversa(id_conv):
    if len(st.session_state.conversas) > 1:
        del st.session_state.conversas[id_conv]
        if st.session_state.conversa_atual == id_conv:
            st.session_state.conversa_atual = list(st.session_state.conversas.keys())[-1]
    else:
        st.session_state.conversas[id_conv] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}

# CSS ESTILO GEMINI / CHATGPT + BRILHO CIANO NEON NO HOVER DE TODOS OS BOTÕES
st.markdown("""
<style>
    @import url('https://googleapis.com');

    .stApp {
        background-color: #FFFFFF !important;
        color: #1F1F1F !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    section[data-testid="stSidebar"] {
        background-color: #F8FAFD !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #1F1F1F !important;
    }

    .gemini-header {
        padding: 1rem 0.5rem 0.8rem 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #E2E8F0;
    }
    .gemini-title {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1A73E8 0%, #00B4D8 40%, #9B72CB 75%, #D96570 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .gemini-sigla {
        font-size: 1.05rem;
        color: #5F6368;
        font-weight: 500;
        margin-left: 8px;
    }
    .badge-gemini {
        background-color: #E0F7FA;
        color: #00838F;
        border: 1px solid #00E5FF;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 3px 12px;
        border-radius: 999px;
        vertical-align: middle;
        margin-left: 10px;
    }
    .gemini-subtitle {
        color: #5F6368;
        font-size: 0.98rem;
        margin-top: 0.3rem;
    }

    /* TODOS OS BOTÕES COM BRILHO CIANO INTENSO AO PASSAR O MOUSE */
    .stButton > button {
        border-radius: 14px !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #F8FAFD !important;
        color: #1F1F1F !important;
        font-weight: 600 !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.25s ease-in-out !important;
    }
    .stButton > button:hover {
        background-color: #00E5FF !important;
        border-color: #00B8D4 !important;
        color: #002535 !important;
        box-shadow: 0 0 18px rgba(0, 229, 255, 0.85), 0 0 6px rgba(0, 229, 255, 0.6) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #D3E3FD !important;
        border: 1px solid #90CAF9 !important;
        color: #041E49 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #00E5FF !important;
        border-color: #00B8D4 !important;
        color: #002535 !important;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.9) !important;
    }

    /* Balões de conversa */
    [data-testid="stChatMessage"] {
        background-color: #F8FAFD !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 18px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.75rem !important;
        color: #1F1F1F !important;
    }

    /* Barra inferior de digitação visível e interativa */
    [data-testid="stBottom"] {
        background-color: #FFFFFF !important;
        border-top: 1px solid #E2E8F0 !important;
    }
    [data-testid="stChatInput"] {
        border-radius: 24px !important;
        border: 2px solid #CBD5E1 !important;
        background-color: #F8FAFD !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #00E5FF !important;
        box-shadow: 0 0 14px rgba(0, 229, 255, 0.45) !important;
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

# BARRA LATERAL
with st.sidebar:
    st.markdown("### ✨ L.U.C.A IA")
    st.caption("Lógica Unificada de Conhecimento e Ação")
    st.caption(f"🕒 {obter_data_hora_atual()}")
    
    if st.button("➕ Nova conversa", use_container_width=True, type="primary"):
        criar_nova_conversa()
        st.rerun()

    st.markdown("##### Recentes")
    for id_conv in reversed(list(st.session_state.conversas.keys())):
        dados_conv = st.session_state.conversas[id_conv]
        col_titulo, col_del = st.columns([0.82, 0.18])
        icone_chat = "💬" if id_conv == st.session_state.conversa_atual else "🗨️"
        with col_titulo:
            if st.button(f"{icone_chat} {dados_conv['titulo']}", key=f"btn_{id_conv}", use_container_width=True):
                st.session_state.conversa_atual = id_conv
                st.session_state.modo_tela = "chat"
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{id_conv}", help="Apagar conversa"):
                excluir_conversa(id_conv)
                st.rerun()

    st.divider()
    st.markdown("##### ⚙️ Painel do Sistema")
    if st.button("💬 Chat Público", use_container_width=True):
