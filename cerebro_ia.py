import os
from groq import Groq
import streamlit as st
import banco_memoria

# 1. Configuração da página e banco de memória
st.set_page_config(
    page_title="L.U.C.A. AI — Lógica Unificada de Conhecimento e Ação",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)
banco_memoria.iniciar_banco()

# Puxa a chave do cofre secreto do Streamlit Cloud:
CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

# SENHA DO CRIADOR:
SENHA_CRIADOR = "947298688"

# 2. CSS Personalizado com visual tecnológico
st.markdown("""
<style>
    /* Cabeçalho estilizado estilo Tech/AI */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 55%, #0284C7 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(56, 189, 248, 0.3);
        box-shadow: 0 8px 25px rgba(2, 132, 199, 0.2);
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        line-height: 1.3;
    }
    .hero-banner .sigla-lado {
        font-size: 1.15rem;
        color: #38BDF8;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .hero-banner p {
        margin: 0.8rem 0 0 0;
        font-size: 1.05rem;
        opacity: 0.92;
    }
    /* Estilo das abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
    }
    /* Mensagens do chat com bordas suaves */
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
        return "Canal Luca Legal — Defesa pessoal, cultura pop e humor."

def gerar_resposta(mensagem, historico, instrucao_sistema, temperatura):
    mensagens_formatadas = [
        {"role": "system", "content": instrucao_sistema}
    ]
    for item in historico:
        mensagens_formatadas.append(
            {"role": item["role"], "content": item["content"]}
        )
    mensagens_formatadas.append(
        {"role": "user", "content": mensagem}
    )

    modelos_disponiveis = []
    try:
        lista_modelos = client.models.list()
        for m in lista_modelos.data:
            nome = m.id
            if not any(x in nome.lower() for x in ["whisper", "guard", "tts"]):
                modelos_disponiveis.append(nome)
    except Exception:
        pass

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
            continue

    return "⚠️ Núcleo sobrecarregado no momento. Aguarde alguns segundos e tente novamente!"

# 3. Barra Lateral (Sidebar)
with st.sidebar:
    st.markdown("## 🤖 L.U.C.A. AI")
    st.caption("Lógica Unificada de Conhecimento e Ação")
    st.info("Olá! Eu sou a **L.U.C.A. AI** (*Lógica Unificada de Conhecimento e Ação*). Fui projetada para ajudar com **defesa pessoal**, **cultura pop**, novidades do canal e responder **qualquer pergunta do seu dia a dia**.")
    
    st.markdown("### ⚡ Comandos Sugeridos:")
    st.markdown("""
    - 🛡️ *Como escapar de um agarre no pulso?*
    - 🎬 *O John Wick sobreviveria na vida real?*
    - 💻 *Me ajude a programar ou estudar.*
    - 🧠 *Me conte uma curiosidade científica!*
    """)
    st.divider()
    st.caption("Status: 🟢 Online • Comunidade Luca Legal")

# 4. Banner Principal com a sigla ao lado do nome
st.markdown("""
<div class="hero-banner">
    <h1>🤖 L.U.C.A. AI <span class="sigla-lado">— Lógica Unificada de Conhecimento e Ação</span></h1>
    <p>Inteligência Artificial oficial da comunidade Luca Legal — pronta para falar sobre defesa pessoal, cultura pop e qualquer assunto que você imaginar.</p>
</div>
""", unsafe_allow_html=True)

aba_publica, aba_criador, aba_memoria = st.tabs([
    "💬 Terminal Aberto (Público)", 
    "🎬 Núcleo do Criador (Restrito)", 
    "💾 Banco de Dados (Restrito)"
])

# --- ABA 1: PÚBLICA (Conversa sobre TUDO, com foco no canal) ---
with aba_publica:
    if "hist_publico" not in st.session_state:
        st.session_state.hist_publico = [
            {"role": "assistant", "content": "Sistemas online! 🤖 Fala, pessoal! Eu sou a **L.U.C.A. AI** (*Lógica Unificada de Conhecimento e Ação*), a inteligência artificial oficial da comunidade **Luca Legal**. Posso te ajudar com análises de filmes e heróis, fundamentos de defesa pessoal, novidades do canal ou conversar sobre **qualquer outro assunto** (estudos, tecnologia, jogos, curiosidades). Como posso ajudar hoje? ⚡"}
        ]

    for msg in st.session_state.hist_publico:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    if prompt_pub := st.chat_input("Digite sua mensagem para a L.U.C.A. AI...", key="in_pub"):
        st.session_state.hist_publico.append({"role": "user", "content": prompt_pub})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt_pub)

        dna = ler_dna_criador()
        memorias = banco_memoria.buscar_todas_notas()
        instrucao = f"""
        Você é a 'L.U.C.A. AI' (Lógica Unificada de Conhecimento e Ação), a Inteligência Artificial Oficial da comunidade e canal 'Luca Legal'.
        Você está conversando com um visitante, inscrito ou cliente no site oficial.

        CONHECIMENTO SOBRE O CANAL E PRODUTOS:
        {dna}

        ATUALIZAÇÕES E REGRAS SALVAS:
        {memorias}

        DIRETRIZES DE IDENTIDADE E COMPORTAMENTO:
        1. NOME E POSTURA: Assuma a identidade da L.U.C.A. AI — uma inteligência artificial moderna, ágil, inteligente e bem-humorada (no estilo leve e direto do canal Luca Legal, adequado para todas as idades).
        2. VERSATILIDADE TOTAL: Converse sobre QUALQUER assunto que o usuário pedir (estudos, programação, receitas, jogos, ciência, conselhos, curiosidades, etc.) com clareza e profundidade.
        3. ESPECIALIDADE PRINCIPAL: Seus temas centrais são Defesa Pessoal, Cultura Pop (filmes, séries, super-heróis) e os conteúdos/produtos do canal Luca Legal. Conecte com esses temas sempre que fizer sentido natural.
        4. PÚBLICO-ALVO: NUNCA trate o usuário como dono do canal. Proibido dizer "sua IA", "seu canal" ou "seus vídeos". Fale como a IA oficial da comunidade atendendo um visitante.
        5. ENGAJAMENTO: Quando falar sobre vídeos ou produtos do canal, convide a pessoa a se inscrever e comentar no YouTube do Luca Legal.
        """
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Processando resposta..."):
                resp = gerar_resposta(prompt_pub, st.session_state.hist_publico[:-1], instrucao, 0.7)
                st.markdown(resp)
        st.session_state.hist_publico.append({"role": "assistant", "content": resp})

# --- ABA 2: ESTÚDIO DO CRIADOR (Protegido por senha) ---
with aba_criador:
    senha_digitada = st.text_input("🔑 Código de acesso do criador:", type="password", key="pwd_est")
    if senha_digitada == SENHA_CRIADOR:
        st.success("Identidade confirmada, Luca! Modo estrategista de YouTube ativado.")
        if "hist_copiloto" not in st.session_state:
            st.session_state.hist_copiloto = []

        for msg in st.session_state.hist_copiloto:
            avatar = "🎬" if msg["role"] == "assistant" else "🦸‍♂️"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

        if prompt_yt := st.chat_input("Peça uma ideia de vídeo, título ou roteiro...", key="in_yt"):
            st.session_state.hist_copiloto.append({"role": "user", "content": prompt_yt})
            with st.chat_message("user", avatar="🦸‍♂️"):
                st.markdown(prompt_yt)

            dna = ler_dna_criador()
            memorias = banco_memoria.buscar_todas_notas()
            instrucao = f"""
            Você é a L.U.C.A. AI operando em modo privado para o criador Luca Legal nos bastidores.
            Ajude a criar títulos de alto CTR, ganchos de 15s, roteiros virais e estratégias de engajamento.
            SEU DNA: {dna}
            MEMÓRIAS SALVAS: {memorias}
            """
            with st.chat_message("assistant", avatar="🎬"):
                with st.spinner("Calculando estratégia viral..."):
                    resp = gerar_resposta(prompt_yt, st.session_state.hist_copiloto[:-1], instrucao, 0.8)
                    st.markdown(resp)
            st.session_state.hist_copiloto.append({"role": "assistant", "content": resp})
    elif senha_digitada:
        st.error("Acesso negado. Código incorreto.")

# --- ABA 3: TREINAR IA (Protegido por senha) ---
with aba_memoria:
    senha_mem = st.text_input("🔑 Código de acesso para atualizar memória:", type="password", key="pwd_mem")
    if senha_mem == SENHA_CRIADOR:
        st.caption("Insira novos dados no núcleo da L.U.C.A. AI para ela responder aos inscritos.")
        categoria = st.selectbox("Categoria", ["Vídeo Novo", "Produto/Link", "Curiosidade do Canal", "Regra de Resposta"])
        nova_nota = st.text_area("O que a L.U.C.A. AI deve memorizar?", placeholder="Ex: Lançamos um vídeo novo analisando o John Wick! Recomende para fãs de ação.")
        if st.button("Atualizar Núcleo", type="primary"):
            if nova_nota.strip():
                banco_memoria.salvar_nota(categoria, nova_nota)
