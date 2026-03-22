import sqlite3


# =========================
# 🔌 CONEXÃO
# =========================
def conectar():
    return sqlite3.connect("voos.db", check_same_thread=False)


# =========================
# 🏗️ CRIAR TABELAS
# =========================
def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()

    # tabela de preços
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS precos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem TEXT,
        destino TEXT,
        data_voo TEXT,
        preco REAL,
        duracao REAL,
        companhia TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # tabela de alertas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origem TEXT,
        destino TEXT,
        preco REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# =========================
# 💾 SALVAR PREÇO
# =========================
def salvar_preco(origem, destino, data_voo, preco, duracao, companhia):
    try:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO precos (origem, destino, data_voo, preco, duracao, companhia)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (origem, destino, data_voo, preco, duracao, companhia))

        conn.commit()
        conn.close()

    except Exception as e:
        print("Erro ao salvar_preco:", e)


# =========================
# 📊 MÉDIA E DESVIO (SEGURO)
# =========================
def obter_stats(origem, destino):
    try:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT preco FROM precos
        WHERE origem = ? AND destino = ?
        """, (origem, destino))

        dados = cursor.fetchall()
        conn.close()

        if not dados:
            return None, 0

        precos = [d[0] for d in dados]

        media = sum(precos) / len(precos)

        variancia = sum((p - media) ** 2 for p in precos) / len(precos)
        desvio = variancia ** 0.5

        return media, desvio

    except Exception as e:
        print("Erro ao obter_stats:", e)
        return None, 0


# =========================
# 📈 HISTÓRICO RECENTE
# =========================
def historico_recente(origem, destino, limite=10):
    try:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT preco FROM precos
        WHERE origem = ? AND destino = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (origem, destino, limite))

        dados = cursor.fetchall()
        conn.close()

        return [d[0] for d in dados]

    except Exception as e:
        print("Erro ao historico_recente:", e)
        return []


# =========================
# 🚫 EVITAR DUPLICADOS
# =========================
def ja_enviado(origem, destino, preco):
    try:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT 1 FROM alertas
        WHERE origem = ? AND destino = ? AND preco = ?
        """, (origem, destino, preco))

        resultado = cursor.fetchone()
        conn.close()

        return resultado is not None

    except Exception as e:
        print("Erro ao ja_enviado:", e)
        return False


# =========================
# 📩 REGISTRAR ALERTA
# =========================
def registrar_alerta(origem, destino, preco):
    try:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO alertas (origem, destino, preco)
        VALUES (?, ?, ?)
        """, (origem, destino, preco))

        conn.commit()
        conn.close()

    except Exception as e:
        print("Erro ao registrar_alerta:", e)
