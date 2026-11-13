import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from groq import Groq
import streamlit as st
import banco_memoria

# 1. Configuração da página e banco de memória
st.set_page_config(
    page_title="L.U.C.A IA (BETA v1.0) — Lógica Unificada de Conhecimento e Ação",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
banco_memoria.iniciar_banco()

# Puxa a chave do cofre secreto do Streamlit Cloud:
CHAVE_API = st.secrets["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"]
client = Groq(api_key=CHAVE_API)

# SENHA DO CRIADOR E VERSÃO ATUAL:
SENHA_CRIADOR = "947298688"
VERSAO_IA = "BETA • v1.0"

# Função para capturar data e hora exatas sincronizadas
def obter_data_hora_atual():
    fuso_local = timezone(timedelta(hours=-1))
    agora = datetime.now(fuso_local)
    dias_semana = [
        "Segunda-feira", "Terça-feira", "Quarta-feira",
        "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
    ]
    dia_sem = dias_semana[agora.weekday()]
    return agora.strftime(f"%d/%m/%Y às %H:%M ({dia_sem})")

# 2. Inicializa o gerenciador de múltiplas conversas
MENSAGEM_INICIAL = "Olá! 🤖 Eu sou a **L.U.C.A IA** (*Lógica Unificada de Conhecimento e Ação* — **BETA v1.0**). Fui feita para te ajudar com **qualquer coisa do dia a dia** — desde tirar dúvidas de estudos, escrever mensagens, organizar ideias e aprender coisas novas até bater um papo sobre qualquer assunto. O que você precisa resolver hoje? ⚡"

if "conversas" not in st.session_state:
    id_inicial = str(uuid.uuid4())
    st.session_state.conversas = {
        id_inicial: {
            "titulo": "Nova conversa",
            "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]
        }
    }
    st.session_state.conversa_atual = id_inicial

def criar_nova_conversa():
    novo_id = str(uuid.uuid4())
    st.session_state.conversas[novo_id] = {
        "titulo": "Nova conversa",
        "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]
    }
    st.session_state.conversa_atual = novo_id

def excluir_conversa(id_conv):
    if len(st.session_state.conversas) > 1:
        del st.session_state.conversas[id_conv]
        if st.session_state.conversa_atual == id_conv:
            st.session_state.conversa_atual = list(st.session_state.conversas.keys())[-1]
    else:
        st.session_state.conversas[id_conv] = {
            "titulo": "Nova conversa",
            "mensagens": [{"role": "assistant", "content": MENSAGEM_INICIAL}]
        }

# 3. CSS Personalizado com visual tecnológico
st.markdown("""
<style>
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #0284C7 100%);
        padding: 1.8rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(56, 189, 248, 0.3);
        box-shadow: 0 8px 25px rgba(2, 132, 199, 0.2);
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        line-height: 1.3;
    }
    .hero-banner .sigla-lado {
        font-size: 1.1rem;
        color: #38BDF8;
        font-weight: 600;
    }
    .badge-beta {
        background-color: rgba(56, 189, 248, 0.2);
        border: 1px solid #38BDF8;
        color: #E0F2FE;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
        vertical-align: middle;
        margin-left: 8px;
        letter-spacing: 0.8px;
    }
    .hero-banner p {
        margin: 0.6rem 0 0 0;
        font-size: 1rem;
        opacity: 0.92;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
    }
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
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
    mensagens_formatadas = [
        {"role": "system", "content": instrucao_sistema}
    ]
    # Mantém as últimas 10 mensagens para economizar cota gratuita e evitar travamentos
    for item in historico[-10:]:
        mensagens_formatadas.append(
            {"role": item["role"], "content": item["content"]}
        )
    mensagem_com_relogio = f"[Relógio do Sistema Agora: {tempo_exato}]\nMensagem do usuário: {mensagem}"
    mensagens_formatadas.append(
        {"role": "user", "content": mensagem_com_relogio}
    )

    modelos_disponiveis = []
    try:
        lista_modelos = client.models.list()
        for m in lista_modelos.data:
            nome = m.id
            if not any(x in nome.lower() for x in ["whisper", "guard", "tts", "vision"]):
                modelos_disponiveis.append(nome)
    except Exception as e:
        return f"⚠️ Erro de conexão com a chave da API: verifique se sua chave no Secrets do Streamlit está ativa. ({e})"

    modelos_disponiveis.sort(key=lambda x: ("70b" not in x and "large" not in x, x))

    for modelo in modelos_disponiveis:
        try:
            resposta = client.chat.completions.create(
                model=modelo,
                messages=mensagens_formatadas,
                temperature=temperatura,
            )
            return resposta.choices[0].message.content
        except Exception:
            time.sleep(1.5)
            continue

    return "⚠️ Muitas mensagens enviadas ao mesmo tempo! Aguarde 10 segundos e tente novamente."

# 4. Barra Lateral (Sidebar) com Histórico de Conversas e Rodapé
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

# 5. Banner Principal com selo BETA v1.0
st.markdown(f"""
<div class="hero-banner">
    <h1>🤖 L.U.C.A IA <span class="sigla-lado">— Lógica Unificada de Conhecimento e Ação</span> <span class="badge-beta">{VERSAO_IA}</span></h1>
    <p>Sua assistente inteligente para ajudar com qualquer coisa do dia a dia — estudos, trabalho, ideias, dúvidas gerais e muito mais!</p>
</div>
""", unsafe_allow_html=True)

aba_publica, aba_criador, aba_memoria = st.tabs([
    "💬 Chat Aberto (Público)", 
    "🎬 Núcleo do Criador (Restrito)", 
    "💾 Banco de Dados (Restrito)"
])

# --- ABA 1: PÚBLICA ---
with aba_publica:
    conv_ativa = st.session_state.conversas[st.session_state.conversa_atual]
    
    for msg in conv_ativa["mensagens"]:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt_pub := st.chat_input("Pergunte ou peça ajuda com qualquer coisa...", key="in_pub"):
        if conv_ativa["titulo"] == "Nova conversa":
            titulo_resumido = prompt_pub[:28] + ("..." if len(prompt_pub) > 28 else "")
            conv_ativa["titulo"] = titulo_resumido

        conv_ativa["mensagens"].append({"role": "user", "content": prompt_pub})
        dna = ler_dna_criador()
        memorias = banco_memoria.buscar_todas_notas()
        
        instrucao_pub = (
            f"Você é a 'L.U.C.A IA' (Lógica Unificada de Conhecimento e Ação), atualmente na versão {VERSAO_IA} (em fase de desenvolvimento), criada por Luca de Brito Ferreira.\n"
            "REGRA DE DATA E HORA: Cada mensagem do usuário vem acompanhada de '[Relógio do Sistema Agora: ...]'. Sempre que perguntarem a data, o dia da semana ou a hora atual, responda EXATAMENTE com os números informados nesse relógio do sistema!\n"
            f"INFORMAÇÕES DE CONTEXTO E DO CRIADOR (Use apenas se o usuário perguntar sobre o canal Luca Legal ou produtos): {dna}\n"
            f"ATUALIZAÇÕES E REGRAS SALVAS: {memorias}\n"
            "DIRETRIZES DE COMPORTAMENTO:\n"
            "1. ASSISTENTE UNIVERSAL DO DIA A DIA: Seu objetivo principal é ajudar o usuário com absolutamente qualquer assunto — estudos, resumos, programação, receitas, dicas práticas, trabalho, conselhos, escrita, jogos ou curiosidades gerais.\n"
            "2. SEM FOCO FIXO: Não force assuntos específicos se o usuário não perguntou sobre isso. Responda diretamente ao que a pessoa precisa.\n"
            "3. IDENTIDADE PÚBLICA: NUNCA trate o usuário como dono do sistema. Proibido dizer 'sua IA', 'seu canal' ou 'seus vídeos'. Fale como uma assistente inteligente acessível a todos.\n"
            "4. TOM DE VOZ: Seja clara, educada, ágil, prestativa e bem-humorada na medida certa (adequada para todas as idades)."
        )
        
