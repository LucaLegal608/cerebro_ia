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

try:
    from duckduckgo_search import DDGS
    TEM_BUSCA = True
except ImportError:
    TEM_BUSCA = False

try:
    from pypdf import PdfReader
    TEM_PDF = True
except ImportError:
    TEM_PDF = False

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

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.AI** (*Lógica Unificada de Conhecimento e Ação Inteligente* — **v3.2**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — agora gerando **imagens reais**, lendo arquivos, com créditos **100% gratuitos** e personalização total no menu **⋮**. Como posso ajudar hoje?"

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

st.markdown("""
<style>
    @import url('https://googleapis.com');
    html, body, .stApp { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .gemini-header { display: flex; align-items: center; gap: 14px; padding: 0.5rem 0.2rem 0.9rem 0.2rem; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(128, 128, 128, 0.25); }
    .chip-emblem { width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, #0284C7 0%, #38BDF8 50%, #7C3AED 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(0, 229, 255, 0.35); flex-shrink: 0; }
    .gemini-title { font-size: 1.95rem; font-weight: 700; background: linear-gradient(90deg, #0284C7 0%, #00B4D8 50%, #9333EA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent !important; display: inline-block; margin: 0; line-height: 1.2; }
    .gemini-sigla { font-size: 0.98rem; opacity: 0.8; font-weight: 500; margin-left: 6px; }
    .badge-v3 { background-color: rgba(0, 229, 255, 0.15) !important; color: #00B4D8 !important; border: 1px solid #00B4D8 !important; font-size: 0.74rem; font-weight: 700; padding: 2px 10px; border-radius: 999px; vertical-align: middle; margin-left: 8px; }
    .gemini-subtitle { opacity: 0.8; font-size: 0.92rem; margin-top: 0.2rem; }
    @media (max-width: 768px) {
        .gemini-header { gap: 10px; padding-top: 0.2rem; }
        .chip-emblem { width: 40px; height: 40px; border-radius: 12px; }
        .gemini-title { font-size: 1.45rem; }
        .gemini-sigla { display: block; margin-left: 0; font-size: 0.8rem; }
        .gemini-subtitle { font-size: 0.82rem; }
        .block-container { padding-top: 2.8rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
    }
    .stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stDownloadButton"] > button {
        border-radius: 14px !important; border: 1.5px solid rgba(128, 128, 128, 0.35) !important; font-weight: 600 !important; transition: all 0.2s ease !important;
    }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover, [data-testid="stDownloadButton"] > button:hover {
        border-color: #00B4D8 !important;
    }
    @keyframes pulsoCiano {
        0% { transform: scale(1); box-shadow: 0 0 12px rgba(0, 229, 255, 0.75); }
        45% { transform: scale(0.93); box-shadow: 0 0 36px rgba(0, 243, 255, 1), 0 0 14px #FFFFFF; }
        80% { transform: scale(1.03); box-shadow: 0 0 24px rgba(0, 243, 255, 0.95); }
        100% { transform: scale(1); box-shadow: 0 0 16px rgba(0, 229, 255, 0.8); }
    }
    button[kind="primary"], [data-testid="stBaseButton-primary"] {
        background: linear-gradient(90deg, #0096C7 0%, #00E5FF 100%) !important; border: 1.5px solid #00F3FF !important; color: #031525 !important; font-weight: 700 !important; box-shadow: 0 0 15px rgba(0, 229, 255, 0.65) !important; transition: all 0.25s ease !important;
    }
    button[kind="primary"] *, [data-testid="stBaseButton-primary"] * { color: #031525 !important; }
    button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover { box-shadow: 0 0 26px rgba(0, 243, 255, 0.95), 0 0 10px rgba(0, 243, 255, 0.8) !important; transform: translateY(-2px) !important; }
    button[kind="primary"]:active, [data-testid="stBaseButton-primary"]:active { animation: pulsoCiano 0.4s ease-out !important; }
    [data-testid="stChatMessage"] { border-radius: 18px !important; padding: 0.9rem 1rem !important; margin-bottom: 0.65rem !important; }
    [data-testid="stChatInput"] { border-radius: 22px !important; }
</style>
""", unsafe_allow_html=True)

def pesquisar_na_web(consulta):
    if not TEM_BUSCA:
        return ""
    try:
        resultados = DDGS().text(consulta, region="br-pt", max_results=4)
        if not resultados:
            return ""
        resumo_web = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in resultados])
        return f"\n\n[PESQUISA NA INTERNET EM TEMPO REAL]:\n{resumo_web}"
    except Exception:
        return ""

def ler_memorias_usuario():
    usr = st.session_state.usuario_logado["usuario"] if st.session_state.usuario_logado else "visitante"
    conn = sqlite3.connect("memoria.db")
    itens = conn.execute("SELECT id, fato FROM memorias_usr WHERE usuario=?", (usr,)).fetchall()
    conn.close()
    return itens

def ler_dna_criador():
    try:
        with open("perfil_cerebro.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Projeto criado por Luca de Brito Ferreira."

def gerar_resposta(mensagem, historico, instrucao_sistema, temperatura):
    sistema_completo = f"{instrucao_sistema}\n\n[DADO INTERNO SILENCIOSO - DATA E HORA ATUAL EM BRASÍLIA: {obter_data_hora_atual()}. NUNCA imprima esse colchete na resposta.]"
    mensagens_formatadas = [{"role": "system", "content": sistema_completo}]
    janela = st.session_state.cfg["janela_contexto"] if st.session_state.usuario_logado else 4
    for item in historico[-janela:]:
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
            return resposta.choices[0].message.content
        except Exception as erro:
            ultimo_erro = str(erro)
            time.sleep(1)
    return f"Não foi possível responder agora. Detalhe: {ultimo_erro}"

def processar_envio_publico(texto_usuario):
    cfg = st.session_state.cfg
    custo = 2 if (cfg["web_ativa"] or cfg["base_conhecimento"]) else 1

    saldo = obter_creditos()
    if saldo < custo:
        st.error(f"Créditos insuficientes! Esta ação custa **{custo} créditos ⚡**, mas você tem **{saldo}**. Os créditos são **100% gratuitos** — vá em **Resgatar Créditos ⚡** no menu **⋮** e peça um código gratuito ao criador Luca Legal!")
        return

    if st.session_state.msgs_hoje >= cfg["limite_msgs_dia"]:
        st.warning(f"Limite diário de {cfg['limite_msgs_dia']} mensagens atingido!")
        return

    for cmd, expansao in cfg["atalhos"].items():
        if texto_usuario.strip().startswith(cmd):
            resto = texto_usuario.strip()[len(cmd):].strip()
            texto_usuario = f"{expansao} {resto}".strip()
            break

    conv = st.session_state.conversas[st.session_state.conversa_atual]
    if conv["titulo"] == "Nova conversa" and not cfg["modo_anonimo"]:
        conv["titulo"] = texto_usuario[:26] + ("..." if len(texto_usuario) > 26 else "")
    conv["mensagens"].append({"role": "user", "content": texto_usuario})
    st.session_state.msgs_hoje += 1

    nome_usr = st.session_state.usuario_logado["nome"] if st.session_state.usuario_logado else "Visitante"
    mems_usr = "\n".join([f"- {f}" for _, f in ler_memorias_usuario()])
    apps_ativos = [k for k, v in cfg["conexoes"].items() if v]
    
    bloco_regras = f"""Você é a 'L.U.C.AI' (Lógica Unificada de Conhecimento e Ação Inteligente), versão {VERSAO_IA}, criada por Luca de Brito Ferreira. Você conversa com {nome_usr}.
    - REGRA SOBRE CRÉDITOS (IMPORTANTE): Todos os créditos da L.U.C.AI são 100% GRATUITOS! Ninguém paga nada para usar. Visitantes ganham 5 créditos grátis, contas criadas ganham 10 créditos grátis e, se precisarem de mais, basta pedir um código de recarga gratuito para o criador Luca Legal (nos comentários do YouTube ou redes sociais) e resgatar na aba 'Resgatar Créditos ⚡' no menu '⋮'.
    - GERAÇÃO DE IMAGENS ({'ATIVA' if cfg['img_ativa'] else 'DESATIVADA'}): Se estiver ATIVA e o usuário pedir para criar, gerar, desenhar ou fazer uma imagem/foto/arte/ilustração, responda com uma frase curta e simpática em português e coloque OBRIGATORIAMENTE no final da resposta a tag exata: [GERAR_IMAGEM: detailed visual prompt in English describing the image]. Nunca use links markdown para imagens, use apenas essa tag.
    - IDIOMA: {cfg['idioma']}.
    - TOM DE VOZ: {cfg['tom_voz']}.
    - TAMANHO DA RESPOSTA: {cfg['tamanho']}.
    - INSTRUÇÕES DO USUÁRIO: {cfg['system_prompt'] or 'Nenhuma regra extra.'}
    - MEMÓRIA APRENDIDA SOBRE O USUÁRIO: {mems_usr or 'Nenhum fato salvo ainda.'}
    - BASE DE CONHECIMENTO: {cfg['base_conhecimento'][:4000] if (cfg['base_conhecimento'] and cfg['arq_ativo']) else 'Nenhum arquivo anexado.'}
    - INTEGRAÇÕES: {', '.join(apps_ativos) if apps_ativos else 'Nenhuma'} | APROVAÇÃO: {cfg['modo_aprovacao']}.
    - CONTEXTO DO CRIADOR: {ler_dna_criador()}. MEMÓRIAS GERAIS: {banco_memoria.buscar_todas_notas()}."""

    dados_web = pesquisar_na_web(texto_usuario) if cfg["web_ativa"] else ""
    resp = gerar_resposta(texto_usuario, conv["mensagens"][:-1], bloco_regras + dados_web, cfg["temperatura"])
    if "[GERAR_IMAGEM:" in resp:
        custo = max(custo, 2)
    alterar_creditos(-custo)
    conv["mensagens"].append({"role": "assistant", "content": resp})

with st.sidebar:
    st.markdown("### :material/memory: L.U.C.AI")
    st.caption("Lógica Unificada de Conhecimento e Ação Inteligente")
    st.caption(f":material/schedule: {obter_data_hora_atual()}")

    saldo_atual = obter_creditos()
    st.metric(label="Seus Créditos Grátis", value=f"{saldo_atual} ⚡", help="Os créditos são 100% gratuitos! Peça um código ao criador se precisar de mais.")

    if st.session_state.usuario_logado:
        st.success(f"Conectado: **{st.session_state.usuario_logado['nome']}**")
        if st.button("Nova conversa", icon=":material/add_comment:", use_container_width=True, type="primary", help="Inicia um novo bate-papo do zero"):
            criar_nova_conversa()
            st.rerun()
        if st.session_state.cfg["modo_anonimo"]:
            st.warning("Modo Anônimo Ativo")
        st.markdown("##### Recentes")
        for id_conv in reversed(list(st.session_state.conversas.keys())):
            dados = st.session_state.conversas[id_conv]
            c_tit, c_del = st.columns([0.80, 0.20])
            icone_chat = ":material/chat:" if id_conv == st.session_state.conversa_atual else ":material/chat_bubble_outline:"
            if c_tit.button(dados["titulo"], icon=icone_chat, key=f"btn_{id_conv}", use_container_width=True, help="Abrir esta conversa"):
                st.session_state.conversa_atual = id_conv
                st.session_state.modo_tela = "chat"
                st.rerun()
            if c_del.button("", icon=":material/delete:", key=f"del_{id_conv}", help="Apagar esta conversa"):
                excluir_conversa(id_conv)
                st.rerun()
    else:
        st.info("Modo Visitante (5 créditos grátis)")
        if st.button("Entrar / Criar Conta (+10 ⚡ Grátis)", icon=":material/login:", use_container_width=True, help="Crie sua conta gratuita para ganhar 10 créditos grátis na hora"):
            st.session_state.modo_tela = "contas"
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
        if st.button("Contas (Login)", icon=":material/account_circle:", use_container_width=True, help="Entrar, cadastrar ou sair da conta"):
            st.session_state.modo_tela = "contas"
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

st.markdown(f"""
<div class="gemini-header">
    <div class="chip-emblem">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <rect x="6" y="6" width="12" height="12" rx="2.5" stroke="url(#grad_chip)" stroke-width="2"/>
            <rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="#00F3FF"/>
            <path d="M9 2V5M15 2V5M9 19V22M15 19V22M2 9H5M2 15H5M19 9H22M19 15H22" stroke="#00F3FF" stroke-width="2" stroke-linecap="round"/>
            <defs><linearGradient id="grad_chip" x1="6" y1="6" x2="18" y2="18" gradientUnits="userSpaceOnUse"><stop stop-color="#00F3FF"/><stop offset="1" stop-color="#E0F2FE"/></linearGradient></defs>
        </svg>
    </div>
    <div>
        <div><span class="gemini-title">L.U.C.AI</span><span class="gemini-sigla">— Lógica Unificada de Conhecimento e Ação Inteligente</span><span class="badge-v3">{VERSAO_IA}</span></div>
        <div class="gemini-subtitle">Sua assistente inteligente completa para ajudar com qualquer coisa do dia a dia.</div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.modo_tela != "chat":
    if st.button("Voltar ao Chat", icon=":material/arrow_back:", help="Voltar para a conversa"):
        st.session_state.modo_tela = "chat"
        st.rerun()

def tela_creditos():
    st.subheader("Central de Créditos 100% Gratuitos — L.U.C.AI ⚡")
    st.metric("Seu Saldo Atual", f"{obter_creditos()} créditos grátis ⚡", help="Todos os créditos da L.U.C.AI são totalmente gratuitos!")
    st.caption("Consumo por uso: Mensagem = **1 ⚡** | Pesquisa Web / Imagem / Arquivo = **2 ⚡**")

    st.info("🎁 **Os créditos são 100% de graça!** Peça um **Código de Recarga Gratuito** diretamente para o criador **Luca Legal** (nos comentários do YouTube, redes sociais ou mensagem) e ative abaixo sem pagar nada!")

    with st.form("form_resgate_gratis"):
        cod_input = st.text_input("Digite o Código Gratuito que você recebeu do criador:")
        if st.form_submit_button("Resgatar Créditos de Graça", icon=":material/redeem:", type="primary", help="Adiciona seus créditos gratuitos na hora"):
            cod = cod_input.strip().upper()
            if cod:
                conn = sqlite3.connect("memoria.db")
                row = conn.execute("SELECT valor, usado FROM codigos_pagos WHERE codigo=?", (cod,)).fetchone()
                if not row:
                    conn.close()
                    st.error("Código inválido. Peça um código gratuito válido ao criador Luca Legal.")
                elif row[1] == 1:
                    conn.close()
                    st.error("Este código já foi usado anteriormente. Peça um novo código gratuito ao criador!")
                else:
                    conn.execute("UPDATE codigos_pagos SET usado=1 WHERE codigo=?", (cod,))
                    conn.commit()
                    conn.close()
                    alterar_creditos(row[0])
                    st.success(f"Parabéns! +{row[0]} créditos gratuitos ⚡ adicionados à sua conta!")
                    st.rerun()

    st.divider()
    with st.expander("Painel do Criador — Gerar Códigos Gratuitos (Acesso Restrito)"):
        s_cred = st.text_input("Código de acesso do criador:", type="password", key="pwd_cred")
        if s_cred == SENHA_CRIADOR:
            st.markdown("#### 1. Gerar Código Gratuito Único (Para Enviar a um Inscrito)")
            col_g1, col_g2 = st.columns(2)
            pacote_gerar = col_g1.selectbox("Quantidade de créditos grátis:", [50, 100, 300, 500, 1000], help="Escolha quantos créditos gratuitos esse código vai dar")
            if col_g2.button("Gerar Código Grátis Agora", icon=":material/key:", help="Cria um código único de recarga gratuita"):
                novo_cod = f"LUCA-{pacote_gerar}-{str(uuid.uuid4())[:6].upper()}"
                conn = sqlite3.connect("memoria.db")
                conn.execute("INSERT INTO codigos_pagos (codigo, valor, usado) VALUES (?, ?, 0)", (novo_cod, pacote_gerar))
                conn.commit()
                conn.close()
                st.success("Código gratuito gerado! Copie e envie para o usuário (uso único):")
                st.code(novo_cod, language="text")

            st.divider()
            st.markdown("#### 2. Enviar Créditos Grátis Direto para uma Conta")
            u_alvo = st.text_input("Nome de usuário (sem @):")
            qtd_add = st.number_input("Quantidade de créditos grátis:", min_value=10, max_value=50000, value=100)
            if st.button("Creditar Grátis Diretamente", icon=":material/send:", help="Envia créditos gratuitos direto para o usuário"):
                conn = sqlite3.connect("memoria.db")
                conn.execute("UPDATE usuarios SET creditos = COALESCE(creditos, 10) + ? WHERE usuario=?", (qtd_add, u_alvo.strip()))
                conn.commit()
                conn.close()
                st.success(f"+{qtd_add} créditos gratuitos enviados para @{u_alvo.strip()}!")

def tela_configuracoes():
   if st.session_state.modo_tela == "chat":
    conv = st.session_state.conversas[st.session_state.conversa_atual]
    for idx, msg in enumerate(conv["mensagens"]):
        with st.chat_message(msg["role"], avatar=":material/memory:" if msg["role"] == "assistant" else ":material/person:"):
            texto_msg = msg["content"]
            match_img = re.search(r"\[GERAR_IMAGEM:\s*(.*?)\]", texto_msg, re.DOTALL)
            if match_img:
                prompt_en = match_img.group(1).strip()
                texto_limpo = re.sub(r"\[GERAR_IMAGEM:.*?\]", "", texto_msg, flags=re.DOTALL).strip()
                if texto_limpo:
                    st.markdown(texto_limpo)
                url_img = f"https://pollinations.ai{urllib.parse.quote(prompt_en)}?width=1024&height=1024&nologo=true&seed={idx + 42}"
                st.image(url_img, caption=f"Imagem gerada pela L.U.C.AI: {prompt_en}", use_container_width=True)
            else:
                st.markdown(texto_msg)

    if prompt_pub := st.chat_input("Pergunte à L.U.C.AI ou peça para criar uma imagem..."):
        processar_envio_publico(prompt_pub)
        st.rerun()

elif st.session_state.modo_tela == "creditos":
    tela_creditos()

elif st.session_state.modo_tela == "configuracoes":
    tela_configuracoes()

elif st.session_state.modo_tela == "compartilhar":
    st.subheader("Compartilhar L.U.C.AI")
    st.code("https://streamlit.app", language="text")

elif st.session_state.modo_tela == "contas":
    st.subheader("Contas L.U.C.AI")
    if st.session_state.usuario_logado:
        st.success(f"Conectado como **{st.session_state.usuario_logado['nome']}** (`@{st.session_state.usuario_logado['usuario']}`).")
        if st.button("Sair da Conta (Logout)", icon=":material/logout:", help="Desconecta sua conta"):
            st.session_state.usuario_logado = None
            st.query_params.clear()
            st.session_state.modo_tela = "chat"
            st.rerun()
    else:
        aba_entrar, aba_criar = st.tabs(["Entrar na Conta", "Criar Conta Gratuita (+10 Créditos Grátis)"])
        with aba_entrar:
            with st.form("form_login"):
                u_login = st.text_input("Nome de usuário:")
                s_login = st.text_input("Senha:", type="password")
                if st.form_submit_button("Entrar", help="Acessar sua conta"):
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
                if st.form_submit_button("Criar Conta Grátis (+10 Créditos)", help="Cria sua conta gratuita e ganha 10 créditos de graça"):
                    if n_cad.strip() and u_cad.strip() and s_cad.strip():
                        conn = sqlite3.connect("memoria.db")
                        if conn.execute("SELECT usuario FROM usuarios WHERE usuario=?", (u_cad.strip(),)).fetchone():
                            conn.close()
                            st.error("Esse nome de usuário já existe.")
                        else:
                            conn.execute("INSERT INTO usuarios (usuario, senha, nome, creditos) VALUES (?, ?, ?, 10)", (u_cad.strip(), s_cad.strip(), n_cad.strip()))
                            conn.commit()
                            conn.close()
                            st.session_state.usuario_logado = {"usuario": u_cad.strip(), "nome": n_cad.strip()}
                            st.query_params["sessao"] = u_cad.strip()
                            st.session_state.modo_tela = "chat"
                            st.rerun()

elif st.session_state.modo_tela == "feedback":
    st.subheader("Enviar Feedback")
    with st.form("form_feedback"):
        autor_fb = st.text_input("Seu nome (opcional):")
        msg_fb = st.text_area("Sua mensagem:")
        if st.form_submit_button("Enviar Feedback", help="Envia sua mensagem para o criador"):
            if msg_fb.strip():
                conn = sqlite3.connect("memoria.db")
                conn.execute("INSERT INTO feedbacks (autor, mensagem, data) VALUES (?, ?, ?)", (autor_fb.strip() or "Anônimo", msg_fb.strip(), obter_data_hora_atual()))
                conn.commit()
                conn.close()
                st.success("Feedback enviado com sucesso!")

elif st.session_state.modo_tela == "ver_feedbacks":
    st.subheader("Feedbacks Recebidos (Acesso Restrito)")
    senha_fb = st.text_input("Código de acesso:", type="password", key="pwd_fb")
    if senha_fb == SENHA_CRIADOR:
        conn = sqlite3.connect("memoria.db")
        lista_fb = conn.execute("SELECT id, autor, mensagem, data FROM feedbacks ORDER BY id DESC").fetchall()
        conn.close()
        for item in lista_fb:
            st.markdown(f"**#{item} • {item}** *({item})*")
            st.info(item)

elif st.session_state.modo_tela == "estudio":
    st.subheader("Estúdio do Criador (Acesso Restrito)")
    senha_est = st.text_input("Código de acesso:", type="password", key="pwd_est")
    if senha_est == SENHA_CRIADOR:
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
    senha_mem = st.text_input("Código de acesso:", type="password", key="pwd_mem")
    if senha_mem == SENHA_CRIADOR:
        cat = st.selectbox("Categoria", ["Novidade", "Produto/Link", "Informação Geral", "Regra de Resposta"])
        nota = st.text_area("O que a L.U.C.AI deve memorizar?")
        if st.button("Salvar Manualmente", icon=":material/save:", help="Grava essa memória permanentemente"):
            if nota.strip():
                banco_memoria.salvar_nota(cat, nota)
                st.success("Salvo com sucesso!")
                st.rerun()
        st.info(banco_memoria.buscar_todas_notas() or "Nenhuma memória extra salva.")
