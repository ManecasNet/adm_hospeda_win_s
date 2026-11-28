"""Importação/exportação CSV (compatível com Excel BR: ';' + UTF-8 BOM) e backup."""
import csv
import shutil
import sqlite3
from . import calculos as c
from .servicos import TABELAS, Pousada

EXPORTAVEIS = {**{t: ["id"] + cs for t, cs in TABELAS.items()},
               "reservas": ["id", "quarto", "hospede", "checkin", "checkout", "noites",
                            "pessoas", "cafe", "valor_diaria", "hospedagem", "cafe_total",
                            "desconto", "total", "pago", "saldo", "status"]}


def exportar_csv(p: Pousada, tabela: str, caminho: str) -> int:
    campos = EXPORTAVEIS[tabela]
    linhas = p.listar_reservas() if tabela == "reservas" else p.listar(tabela)
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            l = dict(l)
            for k in ("data", "checkin", "checkout", "inicio", "fim"):
                if l.get(k):
                    l[k] = c.para_br(l[k])
            w.writerow(l)
    return len(linhas)


def importar_csv(p: Pousada, tabela: str, caminho: str) -> int:
    if tabela not in TABELAS:
        raise ValueError("Importação disponível para: " + ", ".join(TABELAS))
    salvar = {"quartos": p.salvar_quarto, "hospedes": p.salvar_hospede,
              "despesas": p.salvar_despesa, "temporadas": p.salvar_temporada}[tabela]
    n = 0
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        for i, linha in enumerate(csv.DictReader(f, delimiter=";"), start=2):
            try:
                salvar({k: (linha.get(k) or "").strip() for k in TABELAS[tabela]})
                n += 1
            except (ValueError, sqlite3.IntegrityError) as e:
                raise ValueError(f"Linha {i}: {e}") from e
    return n


def backup(p: Pousada, destino: str):
    dest = sqlite3.connect(destino)
    with dest:
        p.con.backup(dest)
    dest.close()


def restaurar(origem: str, destino_db: str):
    shutil.copyfile(origem, destino_db)
