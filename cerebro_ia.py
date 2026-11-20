import os
import re
import json
import time
import uuid
import sqlite3
import urllib.parse
import requests
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria
import telas_extras

try:
    from duckduckgo_search import DDGS
    TEM_BUSCA = True
except ImportError:
    TEM_BUSCA = False

st.set_page_config(page_title="L.U.C.AI (v3.2) — Lógica Unificada de Conhecimento e Ação Inteligente", page_icon=":material/memory:", layout="wide", initial_sidebar_state="auto")
banco_memoria.iniciar_banco()

def iniciar_tabelas_v3():
    conn = sqlite3.connect("memoria.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT, nome TEXT, creditos INTEGER DEFAULT 10)")
    c.execute("CREATE TABLE IF NOT EXISTS feedbacks (id INTEGER PRIMARY KEY AUTOINCREMENT, autor TEXT, mensagem TEXT, data TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS memorias_usr (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT, fato TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS codigos_pagos (codigo TEXT PRIMARY KEY, valor INTEGER, usado INTEGER DEFAULT 0)")
    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN creditos INTEGER DEFAULT 10")
    except Exception:
        pass
    conn.commit()
    conn.close()

iniciar_tabelas_v3()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "v3.2"

def obter_data_hora_atual():
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.AI** (*Lógica Unificada de Conhecimento e Ação Inteligente* — **v3.2**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — gerando **imagens reais**, lendo arquivos, com créditos **100% gratuitos** e personalização total no menu **⋮**. Como posso ajudar hoje?"

CFG_PADRAO = {
    "system_prompt": "",
    "tom_voz": "Casual e Amigável",
    "temperatura": 0.7,
    "tamanho": "Equilibrado",
    "idioma": "Português (Brasil)",
    "janela_contexto": 10,
    "base_conhecimento": "",
    "web_ativa": True,
    "img_ativa": True,
    "arq_ativo": True,
    "cod_ativo": True,
    "conexoes": {"Google Agenda": False, "Notion": False, "WhatsApp": False, "CRM": False},
    "modo_aprovacao": "Pedir confirmação antes de agir",
    "atalhos": {"/resumir": "Resuma o texto ou assunto abaixo em tópicos claros e objetivos:", "/corrigir": "Revise e corrija a gramática e a clareza do texto abaixo:", "/ideias": "Me dê 5 ideias criativas e práticas sobre:", "/imagem": "Crie uma imagem detalhada de:"},
    "modo_anonimo": False,
    "limite_msgs_dia": 100
}

if "cfg" not in st.session_state:
    st.session_state.cfg = CFG_PADRAO.copy()

if "msgs_hoje" not in st.session_state:
    st.session_state.msgs_hoje = 0

if "creditos_visitante" not in st.session_state:
    st.session_state.creditos_visitante = 5

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
    if "sessao" in st.query_params:
        usr_salvo = st.query_params["sessao"]
        conn = sqlite3.connect("memoria.db")
        dados_usr = conn.execute("SELECT usuario, nome FROM usuarios WHERE usuario=?", (usr_salvo,)).fetchone()
        conn.close()
        if dados_usr:
            st.session_state.usuario_logado = {"usuario": dados_usr[0], "nome": dados_usr[1]}

if "conversas" not in st.session_state:
    id_ini = str(uuid.uuid4())
    st.session_state.conversas = {id_ini: {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}}
    st.session_state.conversa_atual = id_ini

if "modo_tela" not in st.session_state:
    st.session_state.modo_tela = "chat"

if "menu_aberto" not in st.session_state:
    st.session_state.menu_aberto = False

def obter_creditos():
    if st.session_state.usuario_logado:
        conn = sqlite3.connect("memoria.db")
        row = conn.execute("SELECT creditos FROM usuarios WHERE usuario=?", (st.session_state.usuario_logado["usuario"],)).fetchone()
        conn.close()
        return row[0] if (row and row[0] is not None) else 10
    return st.session_state.creditos_visitante

def alterar_creditos(delta):
    if st.session_state.usuario_logado:
        atual = obter_creditos()
        novo = max(0, atual + delta)
        conn = sqlite3.connect("memoria.db")
        conn.execute("UPDATE usuarios SET creditos=? WHERE usuario=?", (novo, st.session_state.usuario_logado["usuario"]))
        conn.commit()
        conn.close()
    else:
        st.session_state.creditos_visitante = max(0, st.session_state.creditos_visitante + delta)

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
