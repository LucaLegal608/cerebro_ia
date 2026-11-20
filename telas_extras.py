import json
import uuid
import sqlite3
import base64
import requests
import streamlit as st

try:
    from pypdf import PdfReader
    TEM_PDF = True
except ImportError:
    TEM_PDF = False

def gerar_imagem_nano_banana(prompt_en):
    chave = st.secrets.get("GEMINI_API_KEY", "")
    if not chave:
        return None, "Configure a chave gratuita `GEMINI_API_KEY` (do Google AI Studio) nos Secrets do Streamlit."
    url = f"https://googleapis.com{chave}"
    payload = {
        "contents": [{"parts": [{"text": f"Generate a high quality image of: {prompt_en}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            partes = r.json()["candidates"][0]["content"]["parts"]
            for p in partes:
                if "inlineData" in p:
                    b64 = p["inlineData"]["data"]
                    return base64.b64decode(b64), None
            return None, "O modelo não retornou imagem."
        return None, f"Erro {r.status_code}: {r.text[:180]}"
    except Exception as e:
        return None, f"Erro de conexão: {e}"

def exibir_tela_creditos(obter_creditos, alterar_creditos, senha_criador):
    st.subheader("Central de Créditos 100% Gratuitos — L.U.C.AI ⚡")
    st.metric("Seu Saldo Atual", f"{obter_creditos()} créditos grátis ⚡", help="Todos os créditos da L.U.C.AI são totalmente gratuitos!")
    st.caption("Consumo por uso: Mensagem = **1 ⚡** | Pesquisa Web / Imagem / Arquivo = **2 ⚡**")

    st.info("🎁 **Os créditos são 100% de graça!** Peça um **Código de Recarga Gratuito** diretamente para o criador **Luca Legal** (nos comentários do YouTube, redes sociais ou mensagem) e ative abaixo sem pagar nada!")

    with st.form("form_resgate_gratis"):
        cod_input = st.text_input("Digite o Código Gratuito que você recebeu do criador:")
        if st.form_submit_button("Resgatar Créditos de Graça", icon=":material/redeem:", type="primary"):
            cod = cod_input.strip().upper()
            if cod:
                conn = sqlite3.connect("memoria.db")
                row = conn.execute("SELECT valor, usado FROM codigos_pagos WHERE codigo=?", (cod,)).fetchone()
                if not row:
                    conn.close()
                    st.error("Código inválido. Peça um código gratuito válido ao criador Luca Legal.")
                elif row[1] == 1:
                    conn.close()
                    st.error("Este código já foi usado anteriormente. Peça um novo código ao criador!")
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
        if s_cred == senha_criador:
            col_g1, col_g2 = st.columns(2)
            pacote_gerar = col_g1.selectbox("Quantidade de créditos grátis:", [50, 100, 300, 500, 1000])
            if col_g2.button("Gerar Código Grátis Agora", icon=":material/key:"):
                novo_cod = f"LUCA-{pacote_gerar}-{str(uuid.uuid4())[:6].upper()}"
                conn = sqlite3.connect("memoria.db")
                conn.execute("INSERT INTO codigos_pagos (codigo, valor, usado) VALUES (?, ?, 0)", (novo_cod, pacote_gerar))
                conn.commit()
                conn.close()
                st.success("Código gratuito gerado! Copie e envie para o usuário (uso único):")
                st.code(novo_cod, language="text")

            st.divider()
            u_alvo = st.text_input("Nome de usuário (sem @):")
            qtd_add = st.number_input("Quantidade de créditos grátis:", min_value=10, max_value=50000, value=100)
            if st.button("Creditar Grátis Diretamente", icon=":material/send:"):
                conn = sqlite3.connect("memoria.db")
                conn.execute("UPDATE usuarios SET creditos = COALESCE(creditos, 10) + ? WHERE usuario=?", (qtd_add, u_alvo.strip()))
                conn.commit()
                conn.close()
                st.success(f"+{qtd_add} créditos gratuitos enviados para @{u_alvo.strip()}!")

