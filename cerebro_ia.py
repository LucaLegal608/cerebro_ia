import os
import re
import time
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

st.set_page_config(page_title="L.U.C.AI (v2.0) — Lógica Unificada de Conhecimento e Ação Inteligente", page_icon=":material/memory:", layout="wide", initial_sidebar_state="expanded")
banco_memoria.iniciar_banco()

def iniciar_tabelas_v2():
    conn = sqlite3.connect("memoria.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, nome TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS feedbacks (id INTEGER PRIMARY KEY AUTOINCREMENT, autor TEXT, mensagem TEXT, data TEXT)")
    conn.commit()
    conn.close()

iniciar_tabelas_v2()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "v2.0"

def obter_data_hora_atual():
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.AI** (*Lógica Unificada de Conhecimento e Ação Inteligente* — **v2.0**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — estudos, ideias, textos, programação ou dúvidas gerais. Como posso ajudar hoje?"

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
    if "sessao" in st.query_params:
        usr_salvo = st.query_params["sessao"]
        conn = sqlite3.connect("memoria.db")
        dados_usr = conn.execute("SELECT usuario, nome FROM usuarios WHERE usuario=?", (usr_salvo,)).fetchone()
        conn.close()
        if dados_usr:
            st.session_state.usuario_logado = {"usuario": dados_usr, "nome": dados_usr}

if "conversas" not in st.session_state:
    id_ini = str(uuid.uuid4())
    st.session_state.conversas = {id_ini: {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}}
    st.session_state.conversa_atual = id_ini

if "modo_tela" not in st.session_state:
    st.session_state.modo_tela = "chat"

def criar_nova_conversa():
    nid = str(uuid.uuid4())
    st.session_state.conversas[nid] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}
    st.session_state.conversa_atual = nid
    st.session_state.modo_tela = "chat"

def excluir_conversa(id_conv):
    if len(st.session_state.conversas) > 1:
        del st.session_state.conversas[id_conv]
        if st.session_state.conversa_atual == id_conv:
            st.session_state.conversa_atual = list(st.session_state.conversas.keys())[-1]
    else:
        st.session_state.conversas[id_conv] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}

st.markdown("""
<style>
    @import url('https://googleapis.com');
    .stApp { background-color: #FFFFFF; color: #1F1F1F; font-family: 'Plus Jakarta Sans', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #F8FAFD; border-right: 1px solid #E2E8F0; }
    .gemini-header { display: flex; align-items: center; gap: 16px; padding: 0.6rem 0.5rem 1rem 0.5rem; margin-bottom: 1rem; border-bottom: 1px solid #E2E8F0; }
    .chip-emblem { width: 52px; height: 52px; border-radius: 16px; background: linear-gradient(135deg, #0F172A 0%, #0284C7 55%, #7C3AED 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 16px rgba(0, 229, 255, 0.35); flex-shrink: 0; }
    .gemini-title { font-size: 2.1rem; font-weight: 700; background: linear-gradient(90deg, #0F172A 0%, #00B4D8 55%, #7C3AED 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; margin: 0; line-height: 1.2; }
    .gemini-sigla { font-size: 1.02rem; color: #5F6368; font-weight: 500; margin-left: 8px; }
    .badge-v2 { background-color: #E0F7FA; color: #00838F; border: 1px solid #00E5FF; font-size: 0.78rem; font-weight: 700; padding: 3px 12px; border-radius: 999px; vertical-align: middle; margin-left: 10px; }
    .gemini-subtitle { color: #5F6368; font-size: 0.96rem; margin-top: 0.2rem; }
    .stButton > button, [data-testid="stFormSubmitButton"] > button { border-radius: 14px !important; border: 1px solid #CBD5E1 !important; background-color: #F8FAFD !important; color: #1F1F1F !important; font-weight: 600 !important; transition: all 0.2s ease-in-out !important; }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { background-color: #00E5FF !important; border-color: #00B8D4 !important; color: #002535 !important; box-shadow: 0 0 18px rgba(0, 229, 255, 0.85), 0 0 6px rgba(0, 229, 255, 0.6) !important; transform: translateY(-1px) !important; }
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] { background-color: #D3E3FD !important; border: 1px solid #90CAF9 !important; color: #041E49 !important; }
    .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover { background-color: #00E5FF !important; border-color: #00B8D4 !important; color: #002535 !important; box-shadow: 0 0 20px rgba(0, 229, 255, 0.9) !important; }
    [data-testid="stChatMessage"] { background-color: #F8FAFD; border: 1px solid #E2E8F0; border-radius: 18px; padding: 1rem 1.2rem; margin-bottom: 0.75rem; }
</style>
""", unsafe_allow_html=True)

def ler_dna_criador():
    try:
        with open("perfil_cerebro.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Projeto criado por Luca de Brito Ferreira."

def gerar_resposta(mensagem, historico, instrucao_sistema, temperatura):
    sistema_completo = f"{instrucao_sistema}\n\n[DADO INTERNO SILENCIOSO - DATA E HORA ATUAL EM BRASÍLIA: {obter_data_hora_atual()}. NUNCA imprima esse colchete na resposta. Use apenas se perguntarem a data ou hora.]"
    mensagens_formatadas = [{"role": "system", "content": sistema_completo}]
    limite_hist = 12 if st.session_state.usuario_logado else 4
    for item in historico[-limite_hist:]:
        mensagens_formatadas.append({"role": item["role"], "content": item["content"]})
    mensagens_formatadas.append({"role": "user", "content": mensagem})

    modelos = []
    try:
        for m in client.models.list().data:
            if not any(x in m.id.lower() for x in ["whisper", "guard", "tts", "vision"]):
                modelos.append(m.id)
    except Exception as e:
        return f"Erro na chave da API: {e}"

    modelos.sort(key=lambda x: ("llama-3.3" not in x and "70b" not in x and "120b" not in x, x))
    ultimo_erro = ""
    for modelo in modelos:
        try:
            resposta = client.chat.completions.create(model=modelo, messages=mensagens_formatadas, temperature=temperatura)
            return resposta.choices.message.content
        except Exception as erro:
            ultimo_erro = str(erro)
            time.sleep(1)
    return f"Não foi possível responder agora. Detalhe: {ultimo_erro}"

def processar_envio_publico(texto_usuario):
    conv = st.session_state.conversas[st.session_state.conversa_atual]
    if conv["titulo"] == "Nova conversa":
        conv["titulo"] = texto_usuario[:26] + ("..." if len(texto_usuario) > 26 else "")
    conv["mensagens"].append({"role": "user", "content": texto_usuario})
    nome_usr = st.session_state.usuario_logado["nome"] if st.session_state.usuario_logado else "Visitante"
    inst = f"Você é a 'L.U.C.AI' (Lógica Unificada de Conhecimento e Ação Inteligente), versão {VERSAO_IA}, criada por Luca de Brito Ferreira. Você está conversando com {nome_usr}. Fale EXCLUSIVAMENTE em Português do Brasil natural (nunca use português de Portugal). CONTEXTO DO CRIADOR (use só se perguntarem sobre o canal Luca Legal): {ler_dna_criador()}. MEMÓRIAS: {banco_memoria.buscar_todas_notas()}. Ajude com qualquer assunto do dia a dia de forma amigável e inteligente."
    conv["mensagens"].append({"role": "assistant", "content": gerar_resposta(texto_usuario, conv["mensagens"][:-1], inst, 0.7)})

with st.sidebar:
    st.markdown("### :material/memory: L.U.C.AI")
    st.caption("Lógica Unificada de Conhecimento e Ação Inteligente")
    st.caption(f":material/schedule: {obter_data_hora_atual()}")

    if st.session_state.usuario_logado:
        st.success(f"Conectado: **{st.session_state.usuario_logado['nome']}**")
        if st.button("Nova conversa", icon=":material/add_comment:", use_container_width=True, type="primary"):
            criar_nova_conversa()
            st.rerun()
        st.markdown("##### Recentes")
        for id_conv in reversed(list(st.session_state.conversas.keys())):
            dados = st.session_state.conversas[id_conv]
            c_tit, c_del = st.columns([0.80, 0.20])
            icone_chat = ":material/chat:" if id_conv == st.session_state.conversa_atual else ":material/chat_bubble_outline:"
            if c_tit.button(dados["titulo"], icon=icone_chat, key=f"btn_{id_conv}", use_container_width=True):
                st.session_state.conversa_atual = id_conv
                st.session_state.modo_tela = "chat"
                st.rerun()
            if c_del.button("", icon=":material/delete:", key=f"del_{id_conv}"):
                excluir_conversa(id_conv)
                st.rerun()
    else:
        st.info("Modo Visitante (Simplificado)")
        if st.button("Entrar / Criar Conta", icon=":material/login:", use_container_width=True, type="primary"):
            st.session_state.modo_tela = "contas"
            st.rerun()

    st.divider()
    with st.expander("⋮ Mais opções (Contas, Feedback e Criador)"):
        if st.button("Chat Principal", icon=":material/chat:", use_container_width=True):
            st.session_state.modo_tela = "chat"
            st.rerun()
        if st.button("Contas (Login)", icon=":material/account_circle:", use_container_width=True):
            st.session_state.modo_tela = "contas"
            st.rerun()
        if st.button("Enviar Feedback", icon=":material/rate_review:", use_container_width=True):
            st.session_state.modo_tela = "feedback"
            st.rerun()
        st.divider()
        st.caption("Área Restrita (Criador)")
        if st.button("Estúdio do Criador", icon=":material/movie_edit:", use_container_width=True):
            st.session_state.modo_tela = "estudio"
            st.rerun()
        if st.button("Banco de Dados", icon=":material/database:", use_container_width=True):
            st.session_state.modo_tela = "memoria"
            st.rerun()
        if st.button("Ler Feedbacks", icon=":material/inbox:", use_container_width=True):
            st.session_state.modo_tela = "ver_feedbacks"
            st.rerun()

    st.divider()
    st.caption(f"Status: Online • {VERSAO_IA}")
    st.caption("Criado por Luca de Brito Ferreira")

st.markdown(f"""
<div class="gemini-header">
    <div class="chip-emblem">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <rect x="6" y="6" width="12" height="12" rx="2.5" stroke="url(#grad_chip)" stroke-width="2"/>
            <rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="#00F3FF"/>
            <path d="M9 2V5M15 2V5M9 19V22M15 19V22M2 9H5M2 15H5M19 9H22M19 15H22" stroke="#00F3FF" stroke-width="2" stroke-linecap="round"/>
            <defs><linearGradient id="grad_chip" x1="6" y1="6" x2="18" y2="18" gradientUnits="userSpaceOnUse"><stop stop-color="#00F3FF"/><stop offset="1" stop-color="#E0F2FE"/></linearGradient></defs>
        </svg>
    </div>
    <div>
        <div><span class="gemini-title">L.U.C.AI</span><span class="gemini-sigla">— Lógica Unificada de Conhecimento e Ação Inteligente</span><span class="badge-v2">{VERSAO_IA}</span></div>
        <div class="gemini-subtitle">Sua assistente inteligente para ajudar com qualquer coisa do dia a dia.</div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.modo_tela != "chat":
    if st.button("Voltar ao Chat", icon=":material/arrow_back:"):
        st.session_state.modo_tela = "chat"
        st.rerun()

def tela_contas():
    st.subheader("Contas L.U.C.AI")
    if st.session_state.usuario_logado:
        st.success(f"Conectado como **{st.session_state.usuario_logado['nome']}** (`@{st.session_state.usuario_logado['usuario']}`).")
        if st.button("Sair da Conta (Logout)", icon=":material/logout:"):
            st.session_state.usuario_logado = None
            st.query_params.clear()
            st.session_state.modo_tela = "chat"
            st.rerun()
        return

    aba_entrar, aba_criar = st.tabs(["Entrar na Conta", "Criar Conta Gratuita"])
    with aba_entrar:
        with st.form("form_login"):
            u_login = st.text_input("Nome de usuário:")
            s_login = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                conn = sqlite3.connect("memoria.db")
                res = conn.execute("SELECT usuario, nome FROM usuarios WHERE usuario=? AND senha=?", (u_login.strip(), s_login.strip())).fetchone()
                conn.close()
                if res:
                    st.session_state.usuario_logado = {"usuario": res, "nome": res}
                    st.query_params["sessao"] = res
                    st.session_state.modo_tela = "chat"
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

    with aba_criar:
        with st.form("form_cadastro"):
            n_cad = st.text_input("Seu nome:")
            u_cad = st.text_input("Escolha um usuário (sem espaços):")
            s_cad = st.text_input("Crie uma senha:", type="password")
            if st.form_submit_button("Criar Conta e Desbloquear v2.0", type="primary"):
                if n_cad.strip() and u_cad.strip() and s_cad.strip():
                    try:
                        conn = sqlite3.connect("memoria.db")
                        conn.execute("INSERT INTO usuarios VALUES (?, ?, ?)", (u_cad.strip(), s_cad.strip(), n_cad.strip()))
                        conn.commit()
                        conn.close()
                        st.session_state.usuario_logado = {"usuario": u_cad.strip(), "nome": n_cad.strip()}
                        st.query_params["sessao"] = u_cad.strip()
                        st.session_state.modo_tela = "chat"
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Esse nome de usuário já existe. Escolha outro.")
                else:
                    st.warning("Preencha todos os campos.")

def tela_feedback():
    st.subheader("Enviar Feedback para o Criador")
    st.caption("Tem alguma sugestão de melhoria ou encontrou algum erro na L.U.C.AI v2.0? Escreva abaixo!")
    with st.form("form_feedback"):
        nome_padrao = st.session_state.usuario_logado["nome"] if st.session_state.usuario_logado else ""
        autor_fb = st.text_input("Seu nome (opcional):", value=nome_padrao)
        msg_fb = st.text_area("Sua mensagem ou sugestão:")
        if st.form_submit_button("Enviar Feedback", type="primary"):
            if msg_fb.strip():
                conn = sqlite3.connect("memoria.db")
