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
    chave = st.secrets.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return None, "Configure a chave gratuita `GEMINI_API_KEY` (do Google AI Studio) nos Secrets do Streamlit."
    host = "".join(["generativelanguage", ".", "googleapis", ".", "com"])
    caminho = "/v1beta/models/gemini-2.5-flash-image:generateContent"
    url = f"https://{host}{caminho}?key={chave}"
    payload = {
        "contents": [{"parts": [{"text": f"Generate a high quality image of: {prompt_en}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            partes = r.json()["candidates"]["content"]["parts"]
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

def exibir_tela_configuracoes(ler_memorias_usuario, criar_nova_conversa):
    st.subheader("Central de Configurações — L.U.C.AI v3.3")
    cfg = st.session_state.cfg
    aba1, aba2, aba3, aba4, aba5 = st.tabs(["1. Personalidade", "2. Memória & Arquivos", "3. Ferramentas & Apps", "4. Atalhos Rápidos", "5. Privacidade & Segurança"])

    with aba1:
        cfg["system_prompt"] = st.text_area("Instruções personalizadas (System Prompt):", value=cfg["system_prompt"], placeholder="Ex: Sempre responda em tópicos...")
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
        st.markdown("#### Atalhos e Comandos Rápidos")
        for cmd, desc in list(cfg["atalhos"].items()):
            st.code(f"{cmd} -> {desc}")
        nc1, nc2 = st.columns([0.3, 0.7])
        novo_cmd = nc1.text_input("Novo comando (ex: /traduzir):")
        nova_acao = nc2.text_input("O que ele faz:")
        if st.button("Adicionar Atalho", icon=":material/bolt:"):
            if novo_cmd.startswith("/") and nova_acao.strip():
                cfg["atalhos"][novo_cmd.strip()] = nova_acao.strip()
                st.rerun()

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
