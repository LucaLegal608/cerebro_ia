import os
import re
import json
import time
import uuid
import sqlite3
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria
import telas_extras

try:
    from ddgs import DDGS
    TEM_BUSCA = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        TEM_BUSCA = True
    except ImportError:
        TEM_BUSCA = False

st.set_page_config(page_title="L.U.C.AI (v3.6) — Lógica Unificada de Conhecimento e Ação Inteligente", page_icon=":material/memory:", layout="wide", initial_sidebar_state="auto")
banco_memoria.iniciar_banco()

def iniciar_tabelas_v3():
    conn = sqlite3.connect("memoria.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS feedbacks (id INTEGER PRIMARY KEY AUTOINCREMENT, autor TEXT, mensagem TEXT, data TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS codigos_pagos (codigo TEXT PRIMARY KEY, valor INTEGER, usado INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

iniciar_tabelas_v3()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "v3.6"

def obter_data_hora_atual():
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.AI** (*Lógica Unificada de Conhecimento e Ação Inteligente* — **v3.6**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — pesquisando na web em tempo real, lendo arquivos e com **15 créditos gratuitos ⚡** já liberados. Como posso ajudar hoje?"

CFG_PADRAO = {
    "system_prompt": "",
    "tom_voz": "Casual e Amigável",
    "temperatura": 0.7,
    "tamanho": "Equilibrado",
    "idioma": "Português (Brasil)",
    "janela_contexto": 10,
    "base_conhecimento": "",
    "web_ativa": True,
    "arq_ativo": True,
    "cod_ativo": True,
    "conexoes": {"Google Agenda": False, "Notion": False, "WhatsApp": False, "CRM": False},
    "modo_aprovacao": "Pedir confirmação antes de agir",
    "atalhos": {"/resumir": "Resuma o texto ou assunto abaixo em tópicos claros e objetivos:", "/corrigir": "Revise e corrija a gramática e a clareza do texto abaixo:", "/ideias": "Me dê 5 ideias criativas e práticas sobre:"},
    "modo_anonimo": False,
    "limite_msgs_dia": 100
}

if "cfg" not in st.session_state:
    st.session_state.cfg = CFG_PADRAO.copy()

if "msgs_hoje" not in st.session_state:
    st.session_state.msgs_hoje = 0

if "creditos_sessao" not in st.session_state:
    st.session_state.creditos_sessao = 15

if "memorias_sessao" not in st.session_state:
    st.session_state.memorias_sessao = []

if "criador_autenticado" not in st.session_state:
    st.session_state.criador_autenticado = False

if "conversas" not in st.session_state:
    id_ini = str(uuid.uuid4())
    st.session_state.conversas = {id_ini: {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}}
    st.session_state.conversa_atual = id_ini

if "modo_tela" not in st.session_state:
    st.session_state.modo_tela = "chat"

if "menu_aberto" not in st.session_state:
    st.session_state.menu_aberto = False

def obter_creditos():
    return int(st.session_state.creditos_sessao)

def alterar_creditos(delta):
    st.session_state.creditos_sessao = max(0, int(st.session_state.creditos_sessao) + delta)

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

with st.sidebar:
    st.markdown("### :material/memory: L.U.C.AI")
    st.caption("Lógica Unificada de Conhecimento e Ação Inteligente")
    st.caption(f":material/schedule: {obter_data_hora_atual()}")

    saldo_atual = obter_creditos()
    st.metric(label="Seus Créditos Grátis", value=f"{saldo_atual} ⚡", help="Os créditos são 100% gratuitos! Peça um código ao criador se precisar de mais.")

    if st.button("Nova conversa", icon=":material/add_comment:", use_container_width=True, type="primary", help="Inicia um novo bate-papo do zero"):
        criar_nova_conversa()
        st.rerun()

    if st.session_state.cfg["modo_anonimo"]:
        st.warning("Modo Anônimo Ativo")

    st.markdown("##### Recentes")
    for id_conv in reversed(list(st.session_state.conversas.keys())):
        dados = st.session_state.conversas[id_conv]
        c_tit, c_del = st.columns((0.80, 0.20))
        icone_chat = ":material/chat:" if id_conv == st.session_state.conversa_atual else ":material/chat_bubble_outline:"
        if c_tit.button(dados["titulo"], icon=icone_chat, key=f"btn_{id_conv}", use_container_width=True, help="Abrir esta conversa"):
            st.session_state.conversa_atual = id_conv
            st.session_state.modo_tela = "chat"
            st.rerun()
        if c_del.button("", icon=":material/delete:", key=f"del_{id_conv}", help="Apagar esta conversa"):
            excluir_conversa(id_conv)
            st.rerun()

    st.divider()
    if st.button("⋮", key="btn_tres_pontos", help="Configurações"):
        st.session_state.menu_aberto = not st.session_state.menu_aberto

    if st.session_state.menu_aberto:
        if st.button("Chat Principal", icon=":material/chat:", use_container_width=True, help="Voltar para o chat com a L.U.C.AI"):
            st.session_state.modo_tela = "chat"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Resgatar Créditos ⚡", icon=":material/redeem:", use_container_width=True, help="Ativar código gratuito recebido do criador para ganhar mais créditos de graça"):
            st.session_state.modo_tela = "creditos"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Configurações Completas", icon=":material/settings:", use_container_width=True, help="Personalidade, Memória, Plugins, Atalhos e Segurança"):
            st.session_state.modo_tela = "configuracoes"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Compartilhar L.U.C.AI", icon=":material/share:", use_container_width=True, help="Copiar o link oficial da L.U.C.AI"):
            st.session_state.modo_tela = "compartilhar"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Enviar Feedback", icon=":material/rate_review:", use_container_width=True, help="Enviar sugestões ao criador"):
            st.session_state.modo_tela = "feedback"
            st.session_state.menu_aberto = False
            st.rerun()
        st.divider()
        st.caption("Área Restrita (Criador)")
        if st.button("Estúdio do Criador", icon=":material/movie_edit:", use_container_width=True, help="Treinamento e roteiros"):
            st.session_state.modo_tela = "estudio"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Banco de Dados", icon=":material/database:", use_container_width=True, help="Memórias globais"):
            st.session_state.modo_tela = "memoria"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Ler Feedbacks", icon=":material/inbox:", use_container_width=True, help="Ler mensagens dos usuários"):
            st.session_state.modo_tela = "ver_feedbacks"
            st.session_state.menu_aberto = False
            st.rerun()

    st.divider()
    st.caption(f"Status: Online • {VERSAO_IA}")
    st.caption("Criado por Luca de Brito Ferreira")

header_html = (
    '<div class="gemini-header">'
    '<div class="chip-emblem">'
    '<svg width="28" height="28" viewBox="0 0 24 24" fill="none">'
    '<rect x="6" y="6" width="12" height="12" rx="2.5" stroke="#00F3FF" stroke-width="2"/>'
    '<rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="#00F3FF"/>'
    '<path d="M9 2V5M15 2V5M9 19V22M15 19V22M2 9H5M2 15H5M19 9H22M19 15H22" stroke="#00F3FF" stroke-width="2" stroke-linecap="round"/>'
    '</svg></div><div>'
    f'<div><span class="gemini-title">L.U.C.AI</span><span class="gemini-sigla">- Logica Unificada de Conhecimento e Acao Inteligente</span><span class="badge-v3">{VERSAO_IA}</span></div>'
    '<div class="gemini-subtitle">Sua assistente inteligente completa para ajudar com qualquer coisa do dia a dia.</div>'
    '</div></div>'
)
st.markdown(header_html, unsafe_allow_html=True)

if st.session_state.modo_tela != "chat":
    if st.button("Voltar ao Chat", icon=":material/arrow_back:", help="Voltar para a conversa"):
        st.session_state.modo_tela = "chat"
        st.rerun()

if st.session_state.modo_tela == "chat":
    conv = st.session_state.conversas[st.session_state.conversa_atual]
    for msg in conv["mensagens"]:
        with st.chat_message(msg["role"], avatar=":material/memory:" if msg["role"] == "assistant" else ":material/person:"):
            texto_msg = str(msg.get("content") or "").strip()
            texto_msg = re.sub(r"<think>.*?</think>", "", texto_msg, flags=re.DOTALL).strip()
            st.markdown(texto_msg if texto_msg else "_(Resposta vazia recebida. Tente perguntar novamente.)_")

    if prompt_pub := st.chat_input("Pergunte qualquer coisa à L.U.C.AI..."):
        processar_envio_publico(prompt_pub)
        st.rerun()

elif st.session_state.modo_tela == "creditos":
    telas_extras.exibir_tela_creditos(obter_creditos, alterar_creditos, SENHA_CRIADOR)

elif st.session_state.modo_tela == "configuracoes":
    telas_extras.exibir_tela_configuracoes(ler_memorias_usuario, criar_nova_conversa)

elif st.session_state.modo_tela == "compartilhar":
    st.subheader("Compartilhar L.U.C.AI")
    st.code("https://streamlit.app", language="text")

elif st.session_state.modo_tela == "feedback":
    st.subheader("Enviar Feedback")
    with st.form("form_feedback"):
        autor_fb = st.text_input("Seu nome (opcional):")
        msg_fb = st.text_area("Sua mensagem:")
        if st.form_submit_button("Enviar Feedback"):
            if msg_fb.strip():
                conn = sqlite3.connect("memoria.db")
                conn.execute("INSERT INTO feedbacks (autor, mensagem, data) VALUES (?, ?, ?)", (autor_fb.strip() or "Anônimo", msg_fb.strip(), obter_data_hora_atual()))
                conn.commit()
                conn.close()
                st.success("Feedback enviado com sucesso!")

elif st.session_state.modo_tela == "ver_feedbacks":
    st.subheader("Feedbacks Recebidos (Acesso Restrito)")
    if telas_extras.verificar_acesso_criador(SENHA_CRIADOR, "pwd_fb"):
        conn = sqlite3.connect("memoria.db")
        lista_fb = conn.execute("SELECT id, autor, mensagem, data FROM feedbacks ORDER BY id DESC").fetchall()
        conn.close()
        if not lista_fb:
            st.info("Nenhum feedback recebido ainda.")
        for fid, fautor, fmsg, fdata in lista_fb:
            st.markdown(f"**#{fid} • {fautor}** *({fdata})*")
            st.info(fmsg)

elif st.session_state.modo_tela == "estudio":
    st.subheader("Estúdio do Criador (Acesso Restrito)")
    if telas_extras.verificar_acesso_criador(SENHA_CRIADOR, "pwd_est"):
        st.success("Acesso autorizado, Luca!")
        if "hist_copiloto" not in st.session_state:
            st.session_state.hist_copiloto = []
        for msg in st.session_state.hist_copiloto:
            with st.chat_message(msg["role"], avatar=":material/movie_edit:" if msg["role"] == "assistant" else ":material/person:"):
                st.markdown(msg["content"])
        if prompt_yt := st.chat_input("Peça roteiros ou salve na memória...", key="in_yt"):
            st.session_state.hist_copiloto.append({"role": "user", "content": prompt_yt})
            inst_yt = f"Você é a L.U.C.AI ({VERSAO_IA}) operando para o criador Luca Legal. Se pedir para salvar/lembrar algo, inclua no final: [SALVAR_MEMORIA: texto]. DNA: {ler_dna_criador()}. MEMÓRIAS: {banco_memoria.buscar_todas_notas()}"
            resp = gerar_resposta(prompt_yt, st.session_state.hist_copiloto[:-1], inst_yt, 0.7)
            match = re.search(r"\[SALVAR_MEMORIA:\s*(.*?)\]", resp, re.DOTALL)
            if match:
                txt = match.group(1).strip()
                banco_memoria.salvar_nota("Atualização via Chat", txt)
                resp = re.sub(r"\[SALVAR_MEMORIA:.*?\]", "", resp, flags=re.DOTALL).strip() + f"\n\n*Salvo na memória:* `{txt}`"
            st.session_state.hist_copiloto.append({"role": "assistant", "content": resp})
            st.rerun()

elif st.session_state.modo_tela == "memoria":
    st.subheader("Banco de Dados (Acesso Restrito)")
    if telas_extras.verificar_acesso_criador(SENHA_CRIADOR, "pwd_mem"):
        cat = st.selectbox("Categoria", ("Novidade", "Produto/Link", "Informação Geral", "Regra de Resposta"))
        nota = st.text_area("O que a L.U.C.AI deve memorizar?")
        if st.button("Salvar Manualmente", icon=":material/save:"):
            if nota.strip():
                banco_memoria.salvar_nota(cat, nota)
                st.success("Salvo com sucesso!")
                st.rerun()
        st.info(banco_memoria.buscar_todas_notas() or "Nenhuma memória extra salva.")
