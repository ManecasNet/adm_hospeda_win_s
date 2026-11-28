"""Camada de banco de dados (SQLite). Não conhece a interface."""
import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS quartos(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL UNIQUE, capacidade INTEGER NOT NULL DEFAULT 2,
  diaria REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS hospedes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL, telefone TEXT, documento TEXT, email TEXT);
CREATE TABLE IF NOT EXISTS reservas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  quarto_id INTEGER NOT NULL REFERENCES quartos(id),
  hospede_id INTEGER NOT NULL REFERENCES hospedes(id),
  checkin TEXT NOT NULL, checkout TEXT NOT NULL,
  valor_diaria REAL NOT NULL DEFAULT 0, desconto REAL NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'Reservada', obs TEXT);
CREATE TABLE IF NOT EXISTS pagamentos(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reserva_id INTEGER NOT NULL REFERENCES reservas(id) ON DELETE CASCADE,
  data TEXT NOT NULL, valor REAL NOT NULL, forma TEXT);
CREATE TABLE IF NOT EXISTS despesas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data TEXT NOT NULL, descricao TEXT NOT NULL, categoria TEXT, valor REAL NOT NULL);
CREATE TABLE IF NOT EXISTS temporadas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL, inicio TEXT NOT NULL, fim TEXT NOT NULL,
  acrescimo REAL NOT NULL DEFAULT 0);  -- percentual sobre a diária base (pode ser negativo)
CREATE TABLE IF NOT EXISTS configuracoes(chave TEXT PRIMARY KEY, valor TEXT);
"""

# Colunas novas em bancos criados por versões anteriores
MIGRACOES = [
    ("reservas", "pessoas", "INTEGER NOT NULL DEFAULT 1"),
    ("reservas", "cafe", "INTEGER NOT NULL DEFAULT 0"),
    ("reservas", "valor_cafe", "REAL NOT NULL DEFAULT 0"),
    ("reservas", "usar_temporada", "INTEGER NOT NULL DEFAULT 0"),
]


def _migrar(con):
    for tabela, coluna, ddl in MIGRACOES:
        if coluna not in [r["name"] for r in con.execute(f"PRAGMA table_info({tabela})")]:
            con.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {ddl}")
    con.commit()


def caminho_padrao() -> Path:
  #  base = Path(os.environ.get("APPDATA", Path.home())) / "PousadaFamiliar"
  #  base.mkdir(parents=True, exist_ok=True)
    return "pousada.db"


def conectar(caminho=None) -> sqlite3.Connection:
    con = sqlite3.connect(caminho or caminho_padrao())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    _migrar(con)
    return con
