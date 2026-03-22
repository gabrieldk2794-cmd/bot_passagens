import sqlite3
import statistics

DB_NAME = "dados.db"


def conectar():
    return sqlite3.connect(DB_NAME)


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
        SELECT preco FROM precos
        WHERE origem = ? AND destino = ?
        AND timestamp >= datetime('now', '-30 days')
    """, (origem, destino))

    precos = [row[0] for row in cursor.fetchall()]
    conn.close()

    if len(precos) < 5:
        return None, None

    media = sum(precos) / len(precos)
    desvio = statistics.stdev(precos) if len(precos) > 1 else 0

    return media, desvio


def ja_enviado(origem, destino, preco):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM alertas
        WHERE origem = ? AND destino = ? AND preco = ?
        AND timestamp >= datetime('now', '-6 hours')
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