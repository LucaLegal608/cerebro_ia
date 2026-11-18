import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

from PIL import Image, ImageChops

ARQUIVOS_IMG = [f for f in os.listdir(".") if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
ARQUIVO_LOGO = None
if ARQUIVOS_IMG:
    img = Image.open(ARQUIVOS_IMG).convert("RGBA")
    fundo = Image.new("RGBA", img.size, (255, 255, 255, 255))
    diff = ImageChops.difference(img.convert("RGB"), fundo.convert("RGB"))
    caixa = diff.getbbox()
    if caixa:
        img = img.crop(caixa)
    # Pega apenas a metade superior (o símbolo da rede neural com raio) para ficar grande e nítido
    largura, altura = img.size
    img_simbolo = img.crop((0, 0, largura, int(altura * 0.68)))
    img_simbolo.save("logo_recortada.png")
    ARQUIVO_LOGO = "logo_recortada.png"

TEM_LOGO = ARQUIVO_LOGO is not None
ICONE_PAGINA = ARQUIVO_LOGO if TEM_LOGO else ":material/auto_awesome:"


st.set_page_config(page_title="L.U.C.A IA (BETA v1.6) — Lógica Unificada de Conhecimento e Ação", page_icon=ICONE_PAGINA, layout="wide", initial_sidebar_state="expanded")
banco_memoria.iniciar_banco()

CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

SENHA_CRIADOR = "947298688"
VERSAO_IA = "BETA • v1.6"

def obter_data_hora_atual():
    agora = datetime.now(timezone(timedelta(hours=-3)))
    dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dias[agora.weekday()]})")

MENSAGEM_INICIAL = "Olá! Eu sou a **L.U.C.A IA** (*Lógica Unificada de Conhecimento e Ação* — **BETA v1.6**). Estou pronta para ajudar você com **qualquer coisa do dia a dia** — estudos, ideias, textos, programação ou dúvidas gerais. Como posso ajudar hoje?"

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
    .stApp { background-color: #FFFFFF !important; color: #1F1F1F !important; font-family: 'Plus Jakarta Sans', sans-serif; }
    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    section[data-testid="stSidebar"] { background-color: #F8FAFD !important; border-right: 1px solid #E2E8F0 !important; }
    section[data-testid="stSidebar"] * { color: #1F1F1F !important; }
    .gemini-title { font-size: 2.1rem; font-weight: 700; background: linear-gradient(90deg, #1E293B 0%, #00B4D8 55%, #8B5CF6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; margin: 0; }
    .gemini-sigla { font-size: 1.05rem; color: #5F6368; font-weight: 500; margin-left: 8px; }
    .badge-gemini { background-color: #E0F7FA; color: #00838F; border: 1px solid #00E5FF; font-size: 0.75rem; font-weight: 700; padding: 3px 12px; border-radius: 999px; vertical-align: middle; margin-left: 10px; }
    .gemini-subtitle { color: #5F6368; font-size: 0.98rem; margin-top: 0.25rem; }
    .stButton > button { border-radius: 14px !important; border: 1px solid #CBD5E1 !important; background-color: #F8FAFD !important; color: #1F1F1F !important; font-weight: 600 !important; transition: all 0.25s ease-in-out !important; }
    .stButton > button:hover { background-color: #00E5FF !important; border-color: #00B8D4 !important; color: #002535 !important; box-shadow: 0 0 18px rgba(0, 229, 255, 0.85), 0 0 6px rgba(0, 229, 255, 0.6) !important; transform: translateY(-1px) !important; }
    .stButton > button[kind="primary"] { background-color: #D3E3FD !important; border: 1px solid #90CAF9 !important; color: #041E49 !important; }
    .stButton > button[kind="primary"]:hover { background-color: #00E5FF !important; border-color: #00B8D4 !important; color: #002535 !important; box-shadow: 0 0 20px rgba(0, 229, 255, 0.9) !important; }
    [data-testid="stChatMessage"] { background-color: #F8FAFD !important; border: 1px solid #E2E8F0 !important; border-radius: 18px !important; padding: 1rem 1.2rem !important; margin-bottom: 0.75rem !important; color: #1F1F1F !important; }
    [data-testid="stBottom"] { background-color: #FFFFFF !important; border-top: 1px solid #E2E8F0 !important; }
    [data-testid="stChatInput"] { border-radius: 24px !important; border: 2px solid #CBD5E1 !important; background-color: #F8FAFD !important; }
    [data-testid="stChatInput"]:focus-within { border-color: #00E5FF !important; box-shadow: 0 0 14px rgba(0, 229, 255, 0.45) !important; }
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
    for item in historico[-10:]:
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
    conv = st.session_state.conversas[st.session_state.conversa_atual]
    if conv["titulo"] == "Nova conversa":
        conv["titulo"] = texto_usuario[:26] + ("..." if len(texto_usuario) > 26 else "")
    conv["mensagens"].append({"role": "user", "content": texto_usuario})
    inst = f"Você é a 'L.U.C.A IA' (Lógica Unificada de Conhecimento e Ação), versão {VERSAO_IA} (em desenvolvimento), criada por Luca de Brito Ferreira. Fale EXCLUSIVAMENTE em Português do Brasil natural (nunca use português de Portugal). CONTEXTO DO CRIADOR (use só se perguntarem sobre o canal Luca Legal): {ler_dna_criador()}. MEMÓRIAS: {banco_memoria.buscar_todas_notas()}. Ajude com qualquer assunto do dia a dia de forma amigável e inteligente."
    conv["mensagens"].append({"role": "assistant", "content": gerar_resposta(texto_usuario, conv["mensagens"][:-1], inst, 0.7)})

with st.sidebar:
    if TEM_LOGO:
        st.image(ARQUIVO_LOGO, width=180)
    else:
        st.markdown("### :material/auto_awesome: L.U.C.A IA")
    st.caption("Lógica Unificada de Conhecimento e Ação")
    st.caption(f":material/schedule: {obter_data_hora_atual()}")
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

    st.divider()
    st.markdown("##### Painel")
    if st.button("Chat Público", icon=":material/forum:", use_container_width=True):
        st.session_state.modo_tela = "chat"
        st.rerun()
    if st.button("Estúdio do Criador", icon=":material/movie_edit:", use_container_width=True):
        st.session_state.modo_tela = "estudio"
        st.rerun()
    if st.button("Banco de Dados", icon=":material/database:", use_container_width=True):
        st.session_state.modo_tela = "memoria"
        st.rerun()

    st.divider()
    st.caption(f"Status: Online • {VERSAO_IA}")
    st.caption("Criado por Luca de Brito Ferreira")
    st.caption("Esta IA está em fase de desenvolvimento.")

col_logo, col_txt = st.columns([0.12, 0.88])
with col_logo:
    if TEM_LOGO:
        st.image(ARQUIVO_LOGO, width=85)
with col_txt:
    st.markdown(f"<div><span class='gemini-title'>L.U.C.A IA</span><span class='gemini-sigla'>— Lógica Unificada de Conhecimento e Ação</span><span class='badge-gemini'>{VERSAO_IA}</span></div><div class='gemini-subtitle'>Sua assistente inteligente para ajudar com qualquer coisa do dia a dia.</div>", unsafe_allow_html=True)
st.divider()

avatar_ia = ARQUIVO_LOGO if TEM_LOGO else ":material/auto_awesome:"

if st.session_state.modo_tela == "chat":
    conv = st.session_state.conversas[st.session_state.conversa_atual]
    if len(conv["mensagens"]) == 1:
        st.caption("Sugestões para começar:")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("Me ajude a estudar", icon=":material/school:", use_container_width=True):
            processar_envio_publico("Me ajude a estudar e resumir um assunto importante hoje!")
            st.rerun()
        if c2.button("Criar um código", icon=":material/code:", use_container_width=True):
            processar_envio_publico("Quero ajuda para criar ou entender um código de programação.")
            st.rerun()
        if c3.button("Receita prática", icon=":material/restaurant:", use_container_width=True):
            processar_envio_publico("Me sugira uma receita rápida, gostosa e fácil de fazer hoje!")
            st.rerun()
        if c4.button("Ideias criativas", icon=":material/lightbulb:", use_container_width=True):
            processar_envio_publico("Preciso de ideias criativas para um projeto novo!")
            st.rerun()

    for msg in conv["mensagens"]:
        with st.chat_message(msg["role"], avatar=avatar_ia if msg["role"] == "assistant" else ":material/person:"):
            st.markdown(msg["content"])

    if prompt_pub := st.chat_input("Pergunte à L.U.C.A IA..."):
        processar_envio_publico(prompt_pub)
        st.rerun()

elif st.session_state.modo_tela == "estudio":
    st.subheader("Estúdio do Criador (Acesso Restrito)")
    senha_est = st.text_input("Código de acesso:", type="password", key="pwd_est")
    if senha_est != "" and senha_est != SENHA_CRIADOR:
        st.error("Código incorreto.")
    if senha_est == SENHA_CRIADOR:
        st.success(f"Acesso autorizado, Luca! Peça para eu 'salvar na memória' qualquer novidade.")
        if "hist_copiloto" not in st.session_state:
            st.session_state.hist_copiloto = []
        for msg in st.session_state.hist_copiloto:
            with st.chat_message(msg["role"], avatar=avatar_ia if msg["role"] == "assistant" else ":material/person:"):
                st.markdown(msg["content"])
        if prompt_yt := st.chat_input("Peça roteiros ou atualize a memória por conversa...", key="in_yt"):
            st.session_state.hist_copiloto.append({"role": "user", "content": prompt_yt})
            inst_yt = f"Você é a L.U.C.A IA ({VERSAO_IA}) operando para o criador Luca Legal em Português do Brasil. Sempre que o Luca pedir para lembrar/salvar algo no banco de dados/memória, inclua no final: [SALVAR_MEMORIA: texto resumido]. DNA: {ler_dna_criador()}. MEMÓRIAS: {banco_memoria.buscar_todas_notas()}"
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
    if senha_mem != "" and senha_mem != SENHA_CRIADOR:
        st.error("Código incorreto.")
    if senha_mem == SENHA_CRIADOR:
        cat = st.selectbox("Categoria", ["Novidade", "Produto/Link", "Informação Geral", "Regra de Resposta"])
        nota = st.text_area("O que a L.U.C.A IA deve memorizar?")
        if st.button("Salvar Manualmente", icon=":material/save:", type="primary"):
            if nota.strip():
                banco_memoria.salvar_nota(cat, nota)
                st.success("Salvo com sucesso!")
                st.rerun()
        st.divider()
        st.info(banco_memoria.buscar_todas_notas() or "Nenhuma memória extra salva.")
