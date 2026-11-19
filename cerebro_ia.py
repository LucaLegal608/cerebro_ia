import os
import re
import io
import json
import time
import uuid
import sqlite3
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

try:
    from gtts import gTTS
    TEM_VOZ = True
except ImportError:
    TEM_VOZ = False

st.set_page_config(page_title="L.U.C.AI (v3.1) — Lógica Unificada de Conhecimento e Ação Inteligente", page_icon=":material/memory:", layout="wide", initial_sidebar_state="auto")
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
VERSAO_IA = "v3.1"

def obter_data_hora_atual():
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.AI** (*Lógica Unificada de Conhecimento e Ação Inteligente* — **v3.1**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — com memória, voz, leitura de arquivos, loja de créditos e personalização total no menu **⋮**. Como posso ajudar hoje?"

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
    "voz_ativa": False,
    "voz_sotaque": "pt",
    "voz_lenta": False,
    "atalhos": {"/resumir": "Resuma o texto ou assunto abaixo em tópicos claros e objetivos:", "/corrigir": "Revise e corrija a gramática e a clareza do texto abaixo:", "/ideias": "Me dê 5 ideias criativas e práticas sobre:"},
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

def gerar_audio_voz(texto):
    if not TEM_VOZ:
        return None
    try:
        limpo = re.sub(r"[*#`_\[\]]", "", texto)[:600]
        tts = gTTS(text=limpo, lang=st.session_state.cfg["voz_sotaque"], slow=st.session_state.cfg["voz_lenta"])
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp
    except Exception:
        return None

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
    custo = 1
    if cfg["web_ativa"] or cfg["base_conhecimento"]:
        custo = 2
    if cfg["voz_ativa"]:
        custo = 3

    saldo = obter_creditos()
    if saldo < custo:
        st.error(f"Créditos insuficientes! Esta ação custa **{custo} créditos ⚡**, mas você tem **{saldo}**. Acesse **Loja de Créditos** no menu **⋮** para recarregar!")
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
    - IDIOMA: {cfg['idioma']}.
    - TOM DE VOZ: {cfg['tom_voz']}.
    - TAMANHO DA RESPOSTA: {cfg['tamanho']}.
    - INSTRUÇÕES DO USUÁRIO: {cfg['system_prompt'] or 'Nenhuma regra extra.'}
    - MEMÓRIA APRENDIDA SOBRE O USUÁRIO: {mems_usr or 'Nenhum fato salvo ainda.'}
    - BASE DE CONHECIMENTO: {cfg['base_conhecimento'][:4000] if (cfg['base_conhecimento'] and cfg['arq_ativo']) else 'Nenhum arquivo anexado.'}
    - INTEGRAÇÕES: {', '.join(apps_ativos) if apps_ativos else 'Nenhuma'} | APROVAÇÃO: {cfg['modo_aprovacao']}.
    - IMAGENS ({'ATIVO' if cfg['img_ativa'] else 'DESATIVADO'}): Se o usuário pedir uma imagem e estiver ativo, gere `![Imagem](https://pollinations.ai)`.
    - CONTEXTO DO CRIADOR: {ler_dna_criador()}. MEMÓRIAS GERAIS: {banco_memoria.buscar_todas_notas()}."""

    dados_web = pesquisar_na_web(texto_usuario) if cfg["web_ativa"] else ""
    resp = gerar_resposta(texto_usuario, conv["mensagens"][:-1], bloco_regras + dados_web, cfg["temperatura"])
    alterar_creditos(-custo)
    conv["mensagens"].append({"role": "assistant", "content": resp})

with st.sidebar:
    st.markdown("### :material/memory: L.U.C.AI")
    st.caption("Lógica Unificada de Conhecimento e Ação Inteligente")
    st.caption(f":material/schedule: {obter_data_hora_atual()}")

    saldo_atual = obter_creditos()
    st.metric(label="Seus Créditos", value=f"{saldo_atual} ⚡")

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
        st.info("Modo Visitante (5 créditos de teste)")
        if st.button("Entrar / Criar Conta (+10 ⚡)", icon=":material/login:", use_container_width=True, help="Crie sua conta gratuita para ganhar 10 créditos de teste"):
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
        if st.button("Loja de Créditos ⚡", icon=":material/shopping_cart:", use_container_width=True, help="Comprar pacotes de créditos ou ativar código pago"):
            st.session_state.modo_tela = "creditos"
            st.session_state.menu_aberto = False
            st.rerun()
        if st.button("Configurações Completas", icon=":material/settings:", use_container_width=True, help="Personalidade, Memória, Plugins, Voz e Segurança"):
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
    st.subheader("Loja de Créditos — L.U.C.AI ⚡")
    st.metric("Seu Saldo Atual", f"{obter_creditos()} créditos")
    st.caption("Consumo por uso: Mensagem = **1 ⚡** | Pesquisa Web / Arquivo = **2 ⚡** | Voz / Áudio = **3 ⚡**")

    st.divider()
    st.markdown("### Escolha seu Pacote de Créditos")
    p1, p2, p3 = st.columns(3)

    with p1:
        st.info("**Pacote Inicial**\n\n### +100 Créditos ⚡\n\n**R$ 9,90** *(pagamento único)*")
        st.link_button("Comprar 100 ⚡ (R$ 9,90)", "https://mercadopago.com.br", use_container_width=True)

    with p2:
        st.success("**Pacote Criador (Mais Vendido)**\n\n### +350 Créditos ⚡\n\n**R$ 24,90** *(pagamento único)*")
        st.link_button("Comprar 350 ⚡ (R$ 24,90)", "https://mercadopago.com.br", use_container_width=True)

    with p3:
        st.warning("**Pacote Pro Max**\n\n### +1.000 Créditos ⚡\n\n**R$ 49,90** *(pagamento único)*")
        st.link_button("Comprar 1.000 ⚡ (R$ 49,90)", "https://mercadopago.com.br", use_container_width=True)

    st.caption("Após concluir o pagamento, insira abaixo o **Código de Ativação** recebido no comprovante:")

    with st.form("form_resgate_pago"):
        cod_input = st.text_input("Código de Ativação do Pacote:")
        if st.form_submit_button("Ativar Créditos Comprados", icon=":material/verified:", type="primary"):
            cod = cod_input.strip().upper()
            if cod:
                conn = sqlite3.connect("memoria.db")
                row = conn.execute("SELECT valor, usado FROM codigos_pagos WHERE codigo=?", (cod,)).fetchone()
                if not row:
                    conn.close()
                    st.error("Código inválido. Verifique se digitou corretamente.")
                elif row[1] == 1:
                    conn.close()
                    st.error("Este código já foi utilizado anteriormente.")
                else:
                    conn.execute("UPDATE codigos_pagos SET usado=1 WHERE codigo=?", (cod,))
                    conn.commit()
                    conn.close()
                    alterar_creditos(row[0])
                    st.success(f"Pagamento confirmado! +{row[0]} créditos ⚡ adicionados à sua conta!")
                    st.rerun()

    st.divider()
    with st.expander("Painel Financeiro do Criador (Gerar Códigos e Creditar)"):
        s_cred = st.text_input("Código de acesso do criador:", type="password", key="pwd_cred")
        if s_cred == SENHA_CRIADOR:
            st.markdown("#### 1. Gerar Código de Recarga Único (Para Entregar ao Cliente)")
            col_g1, col_g2 = st.columns(2)
            pacote_gerar = col_g1.selectbox("Valor do pacote pago:", [100, 350, 1000])
            if col_g2.button("Gerar Novo Código Único", icon=":material/key:"):
                novo_cod = f"LUCA-{pacote_gerar}-{str(uuid.uuid4())[:6].upper()}"
                conn = sqlite3.connect("memoria.db")
                conn.execute("INSERT INTO codigos_pagos (codigo, valor, usado) VALUES (?, ?, 0)", (novo_cod, pacote_gerar))
                conn.commit()
                conn.close()
                st.success("Código gerado com sucesso (uso único):")
                st.code(novo_cod, language="text")

            st.divider()
            st.markdown("#### 2. Enviar Créditos Direto para um Usuário")
            u_alvo = st.text_input("Nome de usuário do comprador:")
            qtd_add = st.number_input("Quantidade de créditos:", min_value=10, max_value=50000, value=100)
            if st.button("Creditar Conta Manualmente", icon=":material/send:"):
                conn = sqlite3.connect("memoria.db")
                conn.execute("UPDATE usuarios SET creditos = COALESCE(creditos, 10) + ? WHERE usuario=?", (qtd_add, u_alvo.strip()))
                conn.commit()
                conn.close()
                st.success(f"+{qtd_add} créditos adicionados para @{u_alvo.strip()}!")

def tela_configuracoes():
    st.subheader("Central de Configurações — L.U.C.AI v3.1")
    cfg = st.session_state.cfg
    aba1, aba2, aba3, aba4, aba5 = st.tabs([
        "1. Personalidade", "2. Memória & Arquivos", "3. Ferramentas & Apps", "4. Voz & Atalhos", "5. Privacidade & Segurança"
    ])

    with aba1:
        cfg["system_prompt"] = st.text_area("Instruções personalizadas (System Prompt):", value=cfg["system_prompt"], placeholder="Ex: Sempre responda em tópicos ou Aja como um especialista financeiro...")
        c_tom, c_tam, c_idi = st.columns(3)
        lista_tons = ["Casual e Amigável", "Formal e Profissional", "Direto ao Ponto", "Criativo", "Didático"]
        lista_tams = ["Curto e direto", "Equilibrado", "Detalhado"]
        lista_idis = ["Português (Brasil)", "Detecção Automática", "Inglês", "Espanhol"]
        with c_tom:
            cfg["tom_voz"] = st.selectbox("Tom de voz:", lista_tons, index=lista_tons.index(cfg["tom_voz"]))
        with c_tam:
            cfg["tamanho"] = st.selectbox("Tamanho das respostas:", lista_tams, index=lista_tams.index(cfg["tamanho"]))
        with c_idi:
            cfg["idioma"] = st.selectbox("Idioma padrão:", lista_idis, index=lista_idis.index(cfg["idioma"]))
        cfg["temperatura"] = st.slider("Nível de criatividade (Temperatura):", 0.0, 1.0, float(cfg["temperatura"]), 0.1)

    with aba2:
        cfg["janela_contexto"] = st.slider("Janela de contexto (mensagens lembradas):", 2, 30, int(cfg["janela_contexto"]))
        usr_at = st.session_state.usuario_logado["usuario"] if st.session_state.usuario_logado else "visitante"
        novo_fato = st.text_input("Adicionar fato na memória:")
        if st.button("Salvar na Memória", icon=":material/add:"):
            if novo_fato.strip():
                conn = sqlite3.connect("memoria.db")
                conn.execute("INSERT INTO memorias_usr (usuario, fato) VALUES (?, ?)", (usr_at, novo_fato.strip()))
                conn.commit()
                conn.close()
                st.rerun()
        for fid, ftxt in ler_memorias_usuario():
            cm1, cm2 = st.columns([0.85, 0.15])
            cm1.info(ftxt)
            if cm2.button("", icon=":material/delete:", key=f"del_mem_{fid}"):
                conn = sqlite3.connect("memoria.db")
                conn.execute("DELETE FROM memorias_usr WHERE id=?", (fid,))
                conn.commit()
                conn.close()
                st.rerun()

        arq_up = st.file_uploader("Enviar documento (PDF / TXT / CSV / Código):", type=["pdf", "txt", "csv", "py", "md"])
        if arq_up is not None:
            if arq_up.name.lower().endswith(".pdf") and TEM_PDF:
                leitor = PdfReader(arq_up)
                texto_extraido = "\n".join([p.extract_text() or "" for p in leitor.pages])
            else:
                texto_extraido = arq_up.read().decode("utf-8", errors="ignore")
            cfg["base_conhecimento"] = f"Arquivo ({arq_up.name}):\n{texto_extraido[:6000]}"
            st.success(f"Arquivo '{arq_up.name}' carregado!")

    with aba3:
        t1, t2, t3, t4 = st.columns(4)
        cfg["web_ativa"] = t1.toggle("Pesquisa na Web", value=cfg["web_ativa"])
        cfg["img_ativa"] = t2.toggle("Geração de Imagens", value=cfg["img_ativa"])
        cfg["arq_ativo"] = t3.toggle("Leitura de Arquivos", value=cfg["arq_ativo"])
        cfg["cod_ativo"] = t4.toggle("Execução de Código", value=cfg["cod_ativo"])
        ca1, ca2 = st.columns(2)
        cfg["conexoes"]["Google Agenda"] = ca1.toggle("Google Agenda", value=cfg["conexoes"]["Google Agenda"])
        cfg["conexoes"]["Notion"] = ca1.toggle("Notion", value=cfg["conexoes"]["Notion"])
        cfg["conexoes"]["WhatsApp"] = ca2.toggle("WhatsApp", value=cfg["conexoes"]["WhatsApp"])
        cfg["conexoes"]["CRM"] = ca2.toggle("CRM", value=cfg["conexoes"]["CRM"])
        cfg["modo_aprovacao"] = st.radio("Modo de aprovação:", ["Pedir confirmação antes de agir", "Executar ações automaticamente"], index=0 if cfg["modo_aprovacao"] == "Pedir confirmação antes de agir" else 1)

    with aba4:
        cfg["voz_ativa"] = st.toggle("Ativar resposta automática por voz", value=cfg["voz_ativa"])
        cv1, cv2 = st.columns(2)
        with cv1:
            sotaque = st.selectbox("Voz / Idioma:", ["Português (Brasil)", "Inglês (EUA)", "Espanhol"])
            cfg["voz_sotaque"] = {"Português (Brasil)": "pt", "Inglês (EUA)": "en", "Espanhol": "es"}[sotaque]
        with cv2:
            vel = st.selectbox("Velocidade da fala:", ["Normal", "Mais lenta (Didática)"])
            cfg["voz_lenta"] = (vel == "Mais lenta (Didática)")
        for cmd, desc in list(cfg["atalhos"].items()):
            st.code(f"{cmd} -> {desc}")

    with aba5:
        cfg["modo_anonimo"] = st.toggle("Modo temporário (Incógnito)", value=cfg["modo_anonimo"])
        cfg["limite_msgs_dia"] = st.number_input("Limite de mensagens por sessão:", min_value=5, max_value=1000, value=int(cfg["limite_msgs_dia"]))
        conv_atual = st.session_state.conversas[st.session_state.conversa_atual]
        json_dados = json.dumps(conv_atual["mensagens"], ensure_ascii=False, indent=2)
        csv_dados = "autor,mensagem\n" + "\n".join([f"\"{m['role']}\",\"{m['content'].replace(chr(34), chr(39))}\"" for m in conv_atual["mensagens"]])
        ce1, ce2, ce3 = st.columns(3)
        ce1.download_button("Exportar JSON", data=json_dados, file_name="lucai_historico.json", mime="application/json", use_container_width=True)
        ce2.download_button("Exportar CSV", data=csv_dados, file_name="lucai_historico.csv", mime="text/csv", use_container_width=True)
        if ce3.button("Apagar Todos os Dados", icon=":material/delete_forever:", use_container_width=True):
            st.session_state.conversas = {}
            criar_nova_conversa()
            st.rerun()

if st.session_state.modo_tela == "chat":
    conv = st.session_state.conversas[st.session_state.conversa_atual]
    for idx, msg in enumerate(conv["mensagens"]):
