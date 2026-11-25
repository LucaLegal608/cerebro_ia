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

st.set_page_config(page_title="L.U.C.AI (v3.7) — Lógica Unificada de Conhecimento e Ação Inteligente", page_icon=":material/memory:", layout="wide", initial_sidebar_state="auto")
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
VERSAO_IA = "v3.7"

def obter_data_hora_atual():
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.AI** (*Lógica Unificada de Conhecimento e Ação Inteligente* — **v3.7**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — pesquisando na web em tempo real, lendo arquivos e com **15 créditos gratuitos ⚡** já liberados. Como posso ajudar hoje?"

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

if "efeito_estrelas" not in st.session_state:
    st.session_state.efeito_estrelas = False

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
    st.session_state.efeito_estrelas = True

def excluir_conversa(id_conv):
    if len(st.session_state.conversas) > 1:
        del st.session_state.conversas[id_conv]
        if st.session_state.conversa_atual == id_conv:
            st.session_state.conversa_atual = list(st.session_state.conversas.keys())[-1]
    else:
        st.session_state.conversas[id_conv] = {"titulo": "Nova conversa", "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]}

css_estilo = (
    "<style>"
    "@import url('https://googleapis.com');"
    "html, body, .stApp { font-family: 'Plus Jakarta Sans', sans-serif !important; }"
    ".gemini-header { display: flex; align-items: center; gap: 14px; padding: 0.5rem 0.2rem 0.9rem 0.2rem; margin-bottom: 0.8rem; border-bottom: 1px solid rgba(128, 128, 128, 0.25); }"
    ".chip-emblem { width: 48px; height: 48px; border-radius: 14px; background: linear-gradient(135deg, #0284C7 0%, #38BDF8 50%, #7C3AED 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(0, 229, 255, 0.35); flex-shrink: 0; }"
    ".gemini-title { font-size: 1.95rem; font-weight: 700; background: linear-gradient(90deg, #0284C7 0%, #00B4D8 50%, #9333EA 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent !important; display: inline-block; margin: 0; line-height: 1.2; }"
    ".gemini-sigla { font-size: 0.98rem; opacity: 0.8; font-weight: 500; margin-left: 6px; }"
    ".badge-v3 { background-color: rgba(0, 229, 255, 0.15) !important; color: #00B4D8 !important; border: 1px solid #00B4D8 !important; font-size: 0.74rem; font-weight: 700; padding: 2px 10px; border-radius: 999px; vertical-align: middle; margin-left: 8px; }"
    ".gemini-subtitle { opacity: 0.8; font-size: 0.92rem; margin-top: 0.2rem; }"
    "@media (max-width: 768px) {"
    ".gemini-header { gap: 10px; padding-top: 0.2rem; }"
    ".chip-emblem { width: 40px; height: 40px; border-radius: 12px; }"
    ".gemini-title { font-size: 1.45rem; }"
    ".gemini-sigla { display: block; margin-left: 0; font-size: 0.8rem; }"
    ".gemini-subtitle { font-size: 0.82rem; }"
    ".block-container { padding-top: 2.8rem !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }"
    "}"
    ".stButton > button, [data-testid='stFormSubmitButton'] > button, [data-testid='stDownloadButton'] > button { border-radius: 14px !important; border: 1.5px solid rgba(0, 229, 255, 0.45) !important; font-weight: 600 !important; transition: all 0.25s ease !important; }"
    ".stButton > button:hover, [data-testid='stFormSubmitButton'] > button:hover, [data-testid='stDownloadButton'] > button:hover { border-color: #00F3FF !important; box-shadow: 0 0 14px rgba(0, 243, 255, 0.55) !important; }"
    "@keyframes pulsoCianoNeon { 0% { transform: scale(1); box-shadow: 0 0 16px #00E5FF; } 40% { transform: scale(0.94); box-shadow: 0 0 42px #00F3FF, 0 0 20px #FFFFFF; } 80% { transform: scale(1.04); box-shadow: 0 0 30px #00F3FF; } 100% { transform: scale(1); box-shadow: 0 0 18px #00E5FF; } }"
    "button[kind='primary'], button[data-testid='baseButton-primary'], button[data-testid='stBaseButton-primary'], [data-testid='stSidebar'] button[kind='primary'], [data-testid='stSidebar'] [data-testid='stBaseButton-primary'], [data-testid='stFormSubmitButton'] button[kind='primary'] { background: linear-gradient(90deg, #00B4D8 0%, #00F3FF 100%) !important; background-color: #00E5FF !important; border: 1.5px solid #80F9FF !important; color: #021420 !important; font-weight: 700 !important; box-shadow: 0 0 18px rgba(0, 243, 255, 0.8), 0 0 6px rgba(0, 243, 255, 0.6) !important; }"
    "button[kind='primary'] *, button[data-testid='baseButton-primary'] *, button[data-testid='stBaseButton-primary'] *, [data-testid='stSidebar'] button[kind='primary'] * { color: #021420 !important; }"
    "button[kind='primary']:hover, button[data-testid='stBaseButton-primary']:hover { background: linear-gradient(90deg, #00E5FF 0%, #67F7FF 100%) !important; box-shadow: 0 0 28px #00F3FF, 0 0 14px #FFFFFF !important; transform: translateY(-2px) !important; }"
    "button[kind='primary']:active, button[data-testid='stBaseButton-primary']:active { animation: pulsoCianoNeon 0.45s ease-out !important; }"
    "@keyframes voarEstrela { 0% { opacity: 1; transform: translateY(0) scale(0.6) rotate(0deg); } 50% { opacity: 1; transform: translateY(-45px) scale(1.3) rotate(180deg); } 100% { opacity: 0; transform: translateY(-95px) scale(0.8) rotate(360deg); } }"
    ".estrelas-box { position: fixed; top: 18%; left: 50%; transform: translateX(-50%); z-index: 9999; pointer-events: none; font-size: 2rem; display: flex; gap: 18px; }"
    ".estrela-anim { display: inline-block; text-shadow: 0 0 14px #00F3FF, 0 0 22px #FFFFFF; animation: voarEstrela 1.4s ease-out forwards; }"
    "[data-testid='stChatMessage'] { border-radius: 18px !important; padding: 0.9rem 1rem !important; margin-bottom: 0.65rem !important; }"
    "[data-testid='stChatInput'] { border-radius: 22px !important; }"
    "</style>"
)
st.markdown(css_estilo, unsafe_allow_html=True)

if st.session_state.efeito_estrelas:
    estrelas_html = (
        '<div class="estrelas-box">'
        '<span class="estrela-anim" style="animation-delay:0s;">✨</span>'
        '<span class="estrela-anim" style="animation-delay:0.1s;">⭐</span>'
        '<span class="estrela-anim" style="animation-delay:0.2s;">💫</span>'
        '<span class="estrela-anim" style="animation-delay:0.15s;">✨</span>'
        '<span class="estrela-anim" style="animation-delay:0.25s;">🌟</span>'
        '</div>'
    )
    st.markdown(estrelas_html, unsafe_allow_html=True)
    st.session_state.efeito_estrelas = False

def pesquisar_na_web(consulta):
    if not TEM_BUSCA:
        return ""
    try:
        resultados = list(DDGS().text(consulta, region="br-pt", max_results=5))
        if not resultados:
            resultados = list(DDGS().news(consulta, region="br-pt", max_results=4))
        if not resultados:
            return ""
        resumo_web = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in resultados])
        return f"\n\n[DADOS ATUALIZADOS DA INTERNET AGORA — USE OBRIGATORIAMENTE PARA RESPONDER]:\n{resumo_web}"
    except Exception:
        return ""

def ler_memorias_usuario():
    return st.session_state.memorias_sessao

def ler_dna_criador():
    try:
        with open("perfil_cerebro.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Projeto criado por Luca de Brito Ferreira."

def gerar_resposta(mensagem, historico, instrucao_sistema, temperatura):
    regra_idioma = "\n\n[INSTRUÇÃO DE QUALIDADE]: Responda SEMPRE em português do Brasil natural, fluido, inteligente e bem escrito. NUNCA coloque frases entre colchetes [...] no final da resposta e NUNCA invente que pesquisou no Google ou Mercado Livre se não houver dados de pesquisa acima."
    sistema_completo = f"{instrucao_sistema}{regra_idioma}\n\n[DATA E HORA ATUAL EM BRASÍLIA: {obter_data_hora_atual()}.]"
    mensagens_formatadas = [{"role": "system", "content": sistema_completo}]
    janela = st.session_state.cfg["janela_contexto"]
    for item in historico[-janela:]:
        mensagens_formatadas.append({"role": item["role"], "content": item["content"]})
    mensagens_formatadas.append({"role": "user", "content": mensagem})

    preferidos = (
        "llama-3.3-70b-versatile",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.1-70b-versatile",
        "llama3-70b-8192"
    )
    disponiveis = []
    try:
        for m in client.models.list().data:
            if not any(x in m.id.lower() for x in ("whisper", "guard", "tts", "vision", "compound", "8b")):
                disponiveis.append(m.id)
    except Exception as e:
        return f"Erro na chave da API: {e}"

    lista_final = [m for m in preferidos if m in disponiveis] + [m for m in disponiveis if m not in preferidos]
    if not lista_final:
        lista_final = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

    ultimo_erro = ""
    for modelo in lista_final:
        try:
            resposta = client.chat.completions.create(model=modelo, messages=mensagens_formatadas, temperature=temperatura)
            for escolha in resposta.choices:
                conteudo = escolha.message.content
                if conteudo and conteudo.strip():
                    return conteudo.strip()
        except Exception as erro:
            ultimo_erro = str(erro)
            time.sleep(0.5)
    return f"Não foi possível responder agora. Detalhe: {ultimo_erro}"

def precisa_pesquisar(texto):
    t = texto.lower()
    gatilhos = (
        "pesquise", "busque", "procure", "notícia", "noticia", "hoje", "ontem",
        "amanhã", "atual", "preço", "valor", "cotação", "dólar", "clima",
        "tempo", "previsão", "resultado", "placar", "jogo", "quem ganhou",
        "lançamento", "2025", "2026", "onde fica", "site oficial", "link"
    )
    return any(g in t for g in gatilhos)

def processar_envio_publico(texto_usuario):
    cfg = st.session_state.cfg
    vai_buscar_web = cfg["web_ativa"] and precisa_pesquisar(texto_usuario)
    custo = 2 if (vai_buscar_web or cfg["base_conhecimento"]) else 1

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
