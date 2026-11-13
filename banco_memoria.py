import sqlite3

def iniciar_banco():
    conn = sqlite3.connect("memoria.db")
    cursor = conn.cursor()
    # Tabela para guardar notas permanentes que você ensinar à IA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notas_cerebro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT,
            conteudo TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_nota(categoria, conteudo):
    conn = sqlite3.connect("memoria.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notas_cerebro (categoria, conteudo) VALUES (?, ?)", (categoria, conteudo))
    conn.commit()
    conn.close()

def buscar_todas_notas():
    conn = sqlite3.connect("memoria.db")
    cursor = conn.cursor()
    cursor.execute("SELECT categoria, conteudo FROM notas_cerebro")
    dados = cursor.fetchall()
    conn.close()
    if not dados:
        return "Nenhuma memória adicional salva ainda."
    return "\n".join([f"[{cat.upper()}]: {cont}" for cat, cont in dados])
