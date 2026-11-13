import os
from groq import Groq
import streamlit as st
import banco_memoria

# 1. Configura a página e o banco de memória
st.set_page_config(page_title="IA Oficial — Luca Legal", page_icon="🦸‍♂️", layout="wide")
banco_memoria.iniciar_banco()

# Puxa a chave do cofre secreto do Streamlit Cloud com segurança:
CHAVE_API = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=CHAVE_API)

# SENHA PARA ACESSAR AS ABAS PRIVADAS DO CRIADOR:
SENHA_CRIADOR = "947298688"

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
            return resposta.choices.message.content
        except Exception:
            continue

    return "⚠️ O sistema está recebendo muitas mensagens agora. Tente novamente em alguns segundos!"

# Interface Principal
st.title("🦸‍♂️ IA Oficial — Luca Legal")

aba_publica, aba_criador, aba_memoria = st.tabs([
    "💬 Fale com a IA do Canal (Público)", 
    "🎬 Estúdio do Criador (Restrito)", 
    "💾 Treinar IA (Restrito)"
])

# --- ABA 1: PÚBLICA (Para inscritos, fãs e clientes) ---
with aba_publica:
    st.caption("Tire dúvidas sobre defesa pessoal, cultura pop, vídeos do canal ou nossos produtos!")
    if "hist_publico" not in st.session_state:
        st.session_state.hist_publico = []

    for msg in st.session_state.hist_publico:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt_pub := st.chat_input("Mande sua pergunta aqui...", key="in_pub"):
        st.session_state.hist_publico.append({"role": "user", "content": prompt_pub})
        with st.chat_message("user"):
            st.markdown(prompt_pub)

        dna = ler_dna_criador()
        memorias = banco_memoria.buscar_todas_notas()
        instrucao = f"""
        Você é a Inteligência Artificial Oficial do canal e comunidade 'Luca Legal'.
        Você está conversando com um inscrito, fã ou cliente que acessou o site oficial do canal.
        
        CONHECIMENTO SOBRE O CANAL E PRODUTOS:
        {dna}
        
        ATUALIZAÇÕES E REGRAS SALVAS:
        {memorias}
        
        REGRAS OBRIGATÓRIAS DE COMPORTAMENTO:
        - NUNCA trate a pessoa como se ela fosse o dono do canal. PROIBIDO dizer "seu canal", "sua IA", "seus vídeos" ou "como extensão do seu cérebro".
        - Fale sempre como a IA Oficial da comunidade Luca Legal atendendo um visitante (ex: "Bem-vindo à comunidade Luca Legal!", "Aqui no canal do Luca...").
        - Mantenha o estilo divertido, direto e energético do Luca Legal (adequado para todas as idades).
        - Ajude com dúvidas sobre defesa pessoal, análises de cultura pop, tire dúvidas sobre produtos/links e incentive a pessoa a se inscrever e comentar nos vídeos do YouTube.
        """
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                resp = gerar_resposta(prompt_pub, st.session_state.hist_publico[:-1], instrucao, 0.6)
                st.markdown(resp)
        st.session_state.hist_publico.append({"role": "assistant", "content": resp})

# --- ABA 2: ESTÚDIO DO CRIADOR (Protegido por senha) ---
with aba_criador:
    senha_digitada = st.text_input("Digite a senha do criador para liberar o estúdio:", type="password", key="pwd_est")
    if senha_digitada == SENHA_CRIADOR:
        st.success("Acesso liberado, Luca! Modo estrategista de YouTube ativado.")
        if "hist_copiloto" not in st.session_state:
            st.session_state.hist_copiloto = []

        for msg in st.session_state.hist_copiloto:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt_yt := st.chat_input("Peça uma ideia de vídeo, título ou roteiro...", key="in_yt"):
            st.session_state.hist_copiloto.append({"role": "user", "content": prompt_yt})
            with st.chat_message("user"):
                st.markdown(prompt_yt)

            dna = ler_dna_criador()
            memorias = banco_memoria.buscar_todas_notas()
            instrucao = f"""
            Você está conversando diretamente com o criador Luca Legal nos bastidores.
            Ajude a criar títulos de alto CTR, ganchos de 15s, roteiros virais e estratégias de engajamento.
            SEU DNA: {dna}
            MEMÓRIAS SALVAS: {memorias}
            """
            with st.chat_message("assistant"):
                with st.spinner("Criando estratégia..."):
                    resp = gerar_resposta(prompt_yt, st.session_state.hist_copiloto[:-1], instrucao, 0.8)
                    st.markdown(resp)
            st.session_state.hist_copiloto.append({"role": "assistant", "content": resp})
    elif senha_digitada:
        st.error("Senha incorreta.")

# --- ABA 3: TREINAR IA (Protegido por senha) ---
with aba_memoria:
    senha_mem = st.text_input("Digite a senha do criador para treinar a IA:", type="password", key="pwd_mem")
    if senha_mem == SENHA_CRIADOR:
        st.caption("Adicione informações públicas que a IA deve saber para responder aos inscritos.")
        categoria = st.selectbox("Categoria", ["Vídeo Novo", "Produto/Link", "Curiosidade do Canal", "Regra de Resposta"])
        nova_nota = st.text_area("O que a IA deve aprender?", placeholder="Ex: Acabamos de lançar o vídeo sobre o John Wick! Recomende para quem gosta de filmes de ação.")
        if st.button("Salvar Conhecimento", type="primary"):
            if nova_nota.strip():
                banco_memoria.salvar_nota(categoria, nova_nota)
                st.success(f"✅ Aprendido ({categoria})! Todos os usuários já receberão essa informação.")
            else:
                st.warning("⚠️ Escreva algo antes de salvar.")
    elif senha_mem:
        st.error("Senha incorreta.")
