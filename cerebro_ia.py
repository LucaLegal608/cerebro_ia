import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

st.set_page_config(
    page_title="L.U.C.A IA (BETA v1.3) — Lógica Unificada de Conhecimento e Ação",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)
banco_memoria.iniciar_banco()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "BETA • v1.3"

def obter_data_hora_atual():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias_semana[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! ✨ Eu sou a **L.U.C.A IA** (*Lógica Unificada de Conhecimento e Ação* — **BETA v1.3**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — estudos, ideias, textos, programação ou dúvidas gerais. Como posso ajudar hoje?"

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

# CSS AVANÇADO: ESTILO GEMINI / CHATGPT MINIMALISTA CLARO
st.markdown("""
<style>
    @import url('https://googleapis.com');

    /* Fundo principal claro e limpo */
    .stApp {
        background-color: #FFFFFF !important;
        color: #1F1F1F !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Esconde menus técnicos do Streamlit */
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Barra lateral suave estilo Gemini */
    section[data-testid="stSidebar"] {
        background-color: #F8FAFD !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #1F1F1F !important;
    }

    /* Cabeçalho Minimalista Estilo Gemini */
    .gemini-header {
        padding: 1.2rem 0.5rem 1rem 0.5rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #F1F5F9;
    }
    .gemini-title {
        font-size: 2.1rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1A73E8 0%, #8AB4F8 35%, #9B72CB 70%, #D96570 100%);
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
        background-color: #E8F0FE;
        color: #1967D2;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 999px;
        vertical-align: middle;
        margin-left: 10px;
    }
    .gemini-subtitle {
        color: #5F6368;
        font-size: 1rem;
        margin-top: 0.35rem;
    }

    /* Botões estilo pílula/cartão limpo */
    .stButton > button {
        border-radius: 14px !important;
        border: 1px solid #E2E8F0 !important;
        background-color: #F8FAFD !important;
        color: #1F1F1F !important;
        font-weight: 500 !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background-color: #EEF3FC !important;
        border-color: #D2E3FC !important;
        color: #1967D2 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #D3E3FD !important;
        border: none !important;
        color: #041E49 !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #C2D7FA !important;
    }

    /* Mensagens do Chat estilo Gemini */
    [data-testid="stChatMessage"] {
        background-color: #F8FAFD !important;
        border: 1px solid #EDF2F7 !important;
        border-radius: 18px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.75rem !important;
        color: #1F1F1F !important;
    }

    /* Caixa de texto inferior arredondada */
    [data-testid="stChatInput"] {
        border-radius: 24px !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #F0F4F9 !important;
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

# BARRA LATERAL LIMPA ESTILO GEMINI
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
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{id_conv}", help="Apagar conversa"):
                excluir_conversa(id_conv)
                st.rerun()

    st.divider()
    st.caption(f"Status: 🟢 Online • {VERSAO_IA}")
    st.caption("Criado por Luca de Brito Ferreira")
    st.caption("Esta IA está em fase de desenvolvimento.")

# CABEÇALHO PRINCIPAL ESTILO GEMINI
st.markdown(f"""
<div class="gemini-header">
    <div>
        <span class="gemini-title">✨ L.U.C.A IA</span>
        <span class="gemini-sigla">— Lógica Unificada de Conhecimento e Ação</span>
        <span class="badge-gemini">{VERSAO_IA}</span>
    </div>
    <div class="gemini-subtitle">Sua assistente inteligente para ajudar com qualquer coisa do dia a dia.</div>
</div>
""", unsafe_allow_html=True)

aba_publica, aba_criador, aba_memoria = st.tabs(["💬 Chat", "🎬 Estúdio do Criador", "💾 Banco de Dados"])

