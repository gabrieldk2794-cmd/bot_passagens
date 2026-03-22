import sqlite3

def conectar():
    return sqlite3.connect("voos.db")


def criar_tabela():
    conn = conectar()
    cursor = conn.cursor()

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


def salvar_preco(origem, destino, data_voo, preco, duracao, companhia):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO precos (origem, destino, data_voo, preco, duracao, companhia)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (origem, destino, data_voo, preco, duracao, companhia))

    conn.commit()
    conn.close()


def obter_stats(origem, destino):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT AVG(preco), 
           (AVG(preco * preco) - AVG(preco) * AVG(preco))
    FROM precos
    WHERE origem = ? AND destino = ?
    """, (origem, destino))

    resultado = cursor.fetchone()
    conn.close()

    media = resultado[0] if resultado[0] else None
    variancia = resultado[1] if resultado[1] else 0
    desvio = variancia ** 0.5 if variancia > 0 else 0

    return media, desvio


def historico_recente(origem, destino, limite=10):
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


def ja_enviado(origem, destino, preco):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 1 FROM alertas
    WHERE origem = ? AND destino = ? AND preco = ?
    """, (origem, destino, preco))

    resultado = cursor.fetchone()
    conn.close()

    return resultado is not None


def registrar_alerta(origem, destino, preco):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO alertas (origem, destino, preco)
    VALUES (?, ?, ?)
    """, (origem, destino, preco))

    conn.commit()
    conn.close()
