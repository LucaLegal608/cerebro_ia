import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

st.set_page_config(page_title="L.U.C.A IA (BETA v1.0) — Lógica Unificada de Conhecimento e Ação", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")
banco_memoria.iniciar_banco()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "BETA • v1.0"

def obter_data_hora_atual():
    fuso_brasilia = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_brasilia)
    dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    dia_sem = dias_semana[agora.weekday()]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dia_sem})")

MENSAGEM_INICIAL = "Olá! 🤖 Eu sou a **L.U.C.A IA** (*Lógica Unificada de Conhecimento e Ação* — **BETA v1.0**). Fui feita para te ajudar com **qualquer coisa do dia a dia** — desde tirar dúvidas de estudos, escrever mensagens, organizar ideias e aprender coisas novas até bater um papo sobre qualquer assunto. O que você precisa resolver hoje? ⚡"

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

st.markdown("""
<style>
    .hero-banner { background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #0284C7 100%); padding: 1.8rem; border-radius: 16px; color: white; margin-bottom: 1.5rem; border: 1px solid rgba(56, 189, 248, 0.3); box-shadow: 0 8px 25px rgba(2, 132, 199, 0.2); }
    .hero-banner h1 { margin: 0; font-size: 1.9rem; font-weight: 800; letter-spacing: 0.5px; line-height: 1.3; }
    .hero-banner .sigla-lado { font-size: 1.1rem; color: #38BDF8; font-weight: 600; }
    .badge-beta { background-color: rgba(56, 189, 248, 0.2); border: 1px solid #38BDF8; color: #E0F2FE; font-size: 0.78rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; vertical-align: middle; margin-left: 8px; letter-spacing: 0.8px; }
    .hero-banner p { margin: 0.6rem 0 0 0; font-size: 1rem; opacity: 0.92; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0px 0px; padding: 10px 20px; font-weight: 600; }
    [data-testid="stChatMessage"] { border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
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
    mensagens_formatadas = [{"role": "system", "content": instrucao_sistema}]
    for item in historico[-10:]:
        mensagens_formatadas.append({"role": item["role"], "content": item["content"]})
    mensagem_com_relogio = f"[Relógio do Sistema Agora: {tempo_exato}]\nMensagem do usuário: {mensagem}"
    mensagens_formatadas.append({"role": "user", "content": mensagem_com_relogio})

    modelos_disponiveis = []
    try:
        lista_modelos = client.models.list()
        for m in lista_modelos.data:
            nome = m.id
            if not any(x in nome.lower() for x in ["whisper", "guard", "tts", "vision"]):
                modelos_disponiveis.append(nome)
    except Exception as e:
        return f"⚠️ Erro de conexão com a chave da API: verifique sua chave no Secrets do Streamlit. ({e})"

    modelos_disponiveis.sort(key=lambda x: ("70b" not in x and "large" not in x, x))

    for modelo in modelos_disponiveis:
        try:
            resposta = client.chat.completions.create(model=modelo, messages=mensagens_formatadas, temperature=temperatura)
            return resposta.choices[0].message.content
        except Exception:
            time.sleep(1.5)
            continue

    return "⚠️ Muitas mensagens enviadas ao mesmo tempo! Aguarde 10 segundos e tente novamente."

data_hora_agora = obter_data_hora_atual()

with st.sidebar:
    st.markdown(f"## 🤖 L.U.C.A IA `{VERSAO_IA}`")
    st.caption("Lógica Unificada de Conhecimento e Ação")
    st.caption(f"🕒 {data_hora_agora}")
    
    if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
        criar_nova_conversa()
        st.rerun()

    st.markdown("### 💬 Suas Conversas")
    
    for id_conv in reversed(list(st.session_state.conversas.keys())):
        dados_conv = st.session_state.conversas[id_conv]
        col_titulo, col_del = st.columns([0.82, 0.18])
        eh_atual = (id_conv == st.session_state.conversa_atual)
        icone_chat = "🔵" if eh_atual else "💬"
        
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
    st.caption("⚠️ Esta IA está em fase de desenvolvimento.")

st.markdown(f"""
<div class="hero-banner">
    <h1>🤖 L.U.C.A IA <span class="sigla-lado">— Lógica Unificada de Conhecimento e Ação</span> <span class="badge-beta">{VERSAO_IA}</span></h1>
    <p>Sua assistente inteligente para ajudar com qualquer coisa do dia a dia — estudos, trabalho, ideias, dúvidas gerais e muito mais!</p>
</div>
""", unsafe_allow_html=True)

aba_publica, aba_criador, aba_memoria = st.tabs(["💬 Chat Aberto (Público)", "🎬 Núcleo do Criador (Restrito)", "💾 Banco de Dados (Restrito)"])

with aba_publica:
    conv_ativa = st.session_state.conversas[st.session_state.conversa_atual]
    for msg in conv_ativa["mensagens"]:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt_pub := st.chat_input("Pergunte ou peça ajuda com qualquer coisa...", key="in_pub"):
        if conv_ativa["titulo"] == "Nova conversa":
            conv_ativa["titulo"] = prompt_pub[:28] + ("..." if len(prompt_pub) > 28 else "")

        conv_ativa["mensagens"].append({"role": "user", "content": prompt_pub})
        dna = ler_dna_criador()
        memorias = banco_memoria.buscar_todas_notas()
        instrucao_pub = f"Você é a 'L.U.C.A IA' (Lógica Unificada de Conhecimento e Ação), versão {VERSAO_IA} (em fase de desenvolvimento), criada por Luca de Brito Ferreira. REGRA DE DATA E HORA: Cada mensagem vem acompanhada de '[Relógio do Sistema Agora: ...]'. Sempre que perguntarem a data, dia da semana ou hora atual, responda EXATAMENTE com os números informados nesse relógio! CONTEXTO DO CRIADOR (use apenas se perguntarem sobre o canal Luca Legal): {dna}. ATUALIZAÇÕES SALVAS: {memorias}. DIRETRIZES: 1) Ajude com absolutamente qualquer assunto do dia a dia (estudos, código, receitas, trabalho, curiosidades). 2) Não force assuntos específicos se não perguntarem. 3) Nunca trate o visitante como dono do sistema. 4) Seja clara, educada, ágil e bem-humorada (para todas as idades)."
        
        resp = gerar_resposta(prompt_pub, conv_ativa["mensagens"][:-1], instrucao_pub, 0.7)
        conv_ativa["mensagens"].append({"role": "assistant", "content": resp})
        st.rerun()

with aba_criador:
    senha_digitada = st.text_input("🔑 Código de acesso do criador:", type="password", key="pwd_est")
    if senha_digitada == SENHA_CRIADOR:
        st.success(f"Identidade confirmada, Luca! Modo estrategista de YouTube ativado ({VERSAO_IA}).")
        if "hist_copiloto" not in st.session_state:
            st.session_state.hist_copiloto = []

        for msg in st.session_state.hist_copiloto:
            avatar = "🎬" if msg["role"] == "assistant" else "🦸‍♂️"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        if prompt_yt := st.chat_input("Peça uma ideia de vídeo, título ou roteiro...", key="in_yt"):
            st.session_state.hist_copiloto.append({"role": "user", "content": prompt_yt})
            dna = ler_dna_criador()
            memorias = banco_memoria.buscar_todas_notas()
            instrucao_yt = f"Você é a L.U.C.A IA ({VERSAO_IA}) operando em modo privado para o criador Luca Legal nos bastidores. Ajude a criar títulos de alto CTR, ganchos de 15s, roteiros virais e estratégias de engajamento. SEU DNA: {dna}. MEMÓRIAS SALVAS: {memorias}"
            resp = gerar_resposta(prompt_yt, st.session_state.hist_copiloto[:-1], instrucao_yt, 0.8)
            st.session_state.hist_copiloto.append({"role": "assistant", "content": resp})
            st.rerun()
    elif senha_digitada:
        st.error("Acesso negado. Código incorreto.")

with aba_memoria:
    senha_mem = st.text_input("🔑 Código de acesso para atualizar memória:", type="password", key="pwd_mem")
    if senha_mem == SENHA_CRIADOR:
