import os
from groq import Groq
import streamlit as st
import banco_memoria

# 1. Configura a página e o banco de memória
st.set_page_config(page_title="Segundo Cérebro IA", page_icon="🧠", layout="wide")
banco_memoria.iniciar_banco()

# SUA CHAVE DA GROQ CONFIGURADA:
CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

def ler_dna_criador():
    try:
        with open("perfil_cerebro.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Perfil ainda não configurado."

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

    # Descobre automaticamente todos os modelos de texto ativos na sua conta Groq
    modelos_disponiveis = []
    try:
        lista_modelos = client.models.list()
        for m in lista_modelos.data:
            nome = m.id
            # Ignora modelos de áudio (whisper) ou moderação (guard)
            if not any(x in nome.lower() for x in ["whisper", "guard", "tts"]):
                modelos_disponiveis.append(nome)
    except Exception:
        pass

    # Garante ordem de preferência pelos maiores modelos (70b / llama / qwen / gpt)
    modelos_disponiveis.sort(key=lambda x: ("70b" not in x and "large" not in x, x))

    for modelo in modelos_disponiveis:
        try:
            resposta = client.chat.completions.create(
                model=modelo,
                messages=mensagens_formatadas,
                temperature=temperatura,
            )
            return resposta.choices[0].message.content
        except Exception as erro:
            # Se um modelo falhar, pula automaticamente para o próximo da lista
            continue

    return "⚠️ Nenhum modelo respondeu no momento. Aguarde alguns segundos e tente novamente."

# Interface Principal
st.title("🧠 Segundo Cérebro IA — YouTube & Atendimento")

aba1, aba2, aba3 = st.tabs([
    "🎬 Copiloto de YouTube (Meu Cérebro)", 
    "💬 Atendimento ao Cliente", 
    "💾 Alimentar Memória"
])

# --- ABA 1: COPILOTO ---
with aba1:
    st.caption("Brainstorm, roteiros, títulos magnéticos e estratégias de retenção com o seu estilo.")
    if "hist_copiloto" not in st.session_state:
        st.session_state.hist_copiloto = []

    for msg in st.session_state.hist_copiloto:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_yt := st.chat_input("Peça uma ideia de vídeo, título ou gancho...", key="in_yt"):
        st.session_state.hist_copiloto.append({"role": "user", "content": prompt_yt})
        with st.chat_message("user"):
            st.markdown(prompt_yt)

        dna = ler_dna_criador()
        memorias = banco_memoria.buscar_todas_notas()
        instrucao = f"""
        Você é a EXTENSÃO DO CÉREBRO do criador de conteúdo descrito abaixo.
        Pense, escreva e sugira ideias exatamente como ele faria, potencializado com conhecimento avançado de YouTube, retenção e engajamento.
        SEU DNA: {dna}
        MEMÓRIAS SALVAS: {memorias}
        DIRETRIZES: Responda sempre em português do Brasil. Use os bordões e tom de voz do criador. Inclua ideia de Thumbnail, Título de alto CTR, Gancho de 15s e CTA para comentários.
        """
        with st.chat_message("assistant"):
            with st.spinner("Pensando com o seu cérebro..."):
                resp = gerar_resposta(prompt_yt, st.session_state.hist_copiloto[:-1], instrucao, 0.8)
                st.markdown(resp)
        st.session_state.hist_copiloto.append({"role": "assistant", "content": resp})

# --- ABA 2: ATENDIMENTO ---
with aba2:
    st.caption("Simule ou responda mensagens de clientes usando as regras e produtos do seu negócio.")
    if "hist_atend" not in st.session_state:
        st.session_state.hist_atend = []

    for msg in st.session_state.hist_atend:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_cli := st.chat_input("Digite a mensagem do cliente aqui...", key="in_cli"):
        st.session_state.hist_atend.append({"role": "user", "content": prompt_cli})
        with st.chat_message("user"):
            st.markdown(prompt_cli)

        dna = ler_dna_criador()
        memorias = banco_memoria.buscar_todas_notas()
        instrucao = f"""
        Você é o assistente oficial do criador abaixo. Atenda clientes e inscritos com excelência, tire dúvidas, venda de forma consultiva e puxe engajamento no YouTube.
        DADOS DO NEGÓCIO: {dna}
        INFORMAÇÕES EXTRAS: {memorias}
        REGRAS: Responda em português do Brasil. Nunca invente preços ou links. Incentive o cliente a comentar no canal.
        """
        with st.chat_message("assistant"):
            with st.spinner("Escrevendo resposta..."):
                resp = gerar_resposta(prompt_cli, st.session_state.hist_atend[:-1], instrucao, 0.4)
                st.markdown(resp)
        st.session_state.hist_atend.append({"role": "assistant", "content": resp})

# --- ABA 3: MEMÓRIA ---
with aba3:
    st.caption("Ensine coisas novas para a sua IA. Ela salvará no banco de dados permanente.")
    categoria = st.selectbox("Categoria", ["Ideia de Vídeo", "Estilo e Gírias", "Novo Produto/Link", "Regra de Atendimento"])
    nova_nota = st.text_area("O que devo lembrar?", placeholder="Ex: Postei um vídeo hoje sobre como editar rápido...")
    if st.button("Salvar no Cérebro", type="primary"):
        if nova_nota.strip():
            banco_memoria.salvar_nota(categoria, nova_nota)
            st.success(f"✅ Salvo na memória ({categoria})! Já estou usando essa informação.")
        else:
            st.warning("⚠️ Escreva algo antes de salvar.")
