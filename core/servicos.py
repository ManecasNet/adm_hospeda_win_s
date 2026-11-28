"""Regras de negócio e acesso aos dados. Usada pela interface, mas independente dela."""
import calendar
from datetime import date

from . import calculos as c
from .database import conectar

STATUS = ["Reservada", "Hospedado", "Finalizada", "Cancelada"]
TABELAS = {  # tabela -> campos editáveis
    "quartos": ["nome", "capacidade", "diaria"],
    "hospedes": ["nome", "telefone", "documento", "email"],
    "despesas": ["data", "descricao", "categoria", "valor"],
    "temporadas": ["nome", "inicio", "fim", "acrescimo"],
}


class Pousada:
    def __init__(self, caminho=None):
        self.con = conectar(caminho)

    # ---------- CRUD genérico ----------
    def listar(self, tabela, ordem="id"):
        return [dict(r) for r in self.con.execute(f"SELECT * FROM {tabela} ORDER BY {ordem}")]

    def salvar(self, tabela, dados: dict, id=None):
        campos = TABELAS[tabela]
        valores = [dados.get(k) for k in campos]
        with self.con:
            if id:
                sets = ",".join(f"{k}=?" for k in campos)
                self.con.execute(f"UPDATE {tabela} SET {sets} WHERE id=?", valores + [id])
                return id
            marc = ",".join("?" * len(campos))
            cur = self.con.execute(
                f"INSERT INTO {tabela}({','.join(campos)}) VALUES({marc})", valores)
            return cur.lastrowid

    def excluir(self, tabela, id):
        try:
            with self.con:
                self.con.execute(f"DELETE FROM {tabela} WHERE id=?", (id,))
        except Exception as e:
            raise ValueError("Não foi possível excluir: há registros vinculados.") from e

    # ---------- Validações específicas ----------
    def salvar_quarto(self, d, id=None):
        if not str(d.get("nome", "")).strip():
            raise ValueError("Informe o nome do quarto.")
        d["capacidade"] = int(d.get("capacidade") or 1)
        d["diaria"] = c.parse_valor(d.get("diaria"))
        return self.salvar("quartos", d, id)

    def salvar_hospede(self, d, id=None):
        if not str(d.get("nome", "")).strip():
            raise ValueError("Informe o nome do hóspede.")
        return self.salvar("hospedes", d, id)

    def salvar_despesa(self, d, id=None):
        d["data"] = c.para_iso(d.get("data"))
        d["valor"] = c.parse_valor(d.get("valor"))
        if not str(d.get("descricao", "")).strip():
            raise ValueError("Informe a descrição.")
        return self.salvar("despesas", d, id)

    def salvar_temporada(self, d, id=None):
        if not str(d.get("nome", "")).strip():
            raise ValueError("Informe o nome da temporada.")
        ini, fim = c.para_iso(d.get("inicio")), c.para_iso(d.get("fim"))
        if fim < ini:
            raise ValueError("O fim deve ser igual ou posterior ao início.")
        d = {**d, "inicio": ini, "fim": fim, "acrescimo": c.parse_valor(d.get("acrescimo"))}
        return self.salvar("temporadas", d, id)

    # ---------- Configurações ----------
    def config(self, chave, padrao=""):
        r = self.con.execute("SELECT valor FROM configuracoes WHERE chave=?", (chave,)).fetchone()
        return r["valor"] if r else padrao

    def definir_config(self, chave, valor):
        with self.con:
            self.con.execute("INSERT OR REPLACE INTO configuracoes(chave,valor) VALUES(?,?)",
                             (chave, str(valor)))

    # ---------- Reservas ----------
    def calcular_reserva(self, d, temporadas=None):
        """Hospedagem (com temporadas) + café - desconto. Usada no salvar, na lista e na prévia."""
        ci, co = c.para_iso(d["checkin"]), c.para_iso(d["checkout"])
        n = c.noites(ci, co)
        usar = int(d.get("usar_temporada") or 0)
        if temporadas is None:
            temporadas = self.listar("temporadas")
        hosp = c.total_hospedagem(ci, co, c.parse_valor(d.get("valor_diaria")),
                                  temporadas if usar else [])
        cafe = (c.total_cafe(n, d.get("pessoas"), c.parse_valor(d.get("valor_cafe")))
                if int(d.get("cafe") or 0) else 0.0)
        return {"noites": n, "hospedagem": hosp, "cafe_total": cafe,
                "total": c.total_reserva(hosp, cafe, c.parse_valor(d.get("desconto")))}

    def quarto_disponivel(self, quarto_id, ci, co, ignorar_id=None):
        q = ("SELECT checkin, checkout FROM reservas "
             "WHERE quarto_id=? AND status!='Cancelada' AND id IS NOT ?")
        return not any(c.periodos_conflitam(ci, co, r["checkin"], r["checkout"])
                       for r in self.con.execute(q, (quarto_id, ignorar_id)))

    def salvar_reserva(self, d, id=None):
        ci, co = c.para_iso(d["checkin"]), c.para_iso(d["checkout"])
        if c.noites(ci, co) < 1:
            raise ValueError("O check-out deve ser após o check-in.")
        if not d.get("quarto_id") or not d.get("hospede_id"):
            raise ValueError("Selecione quarto e hóspede.")
        status = d.get("status", "Reservada")
        if status != "Cancelada" and not self.quarto_disponivel(d["quarto_id"], ci, co, id):
            raise ValueError("Quarto já reservado neste período.")
        try:
            pessoas = max(1, int(d.get("pessoas") or 1))
        except ValueError:
            raise ValueError("Número de pessoas inválido.")
        vals = (d["quarto_id"], d["hospede_id"], ci, co, c.parse_valor(d.get("valor_diaria")),
                c.parse_valor(d.get("desconto")), status, d.get("obs", ""), pessoas,
                int(bool(d.get("cafe"))), c.parse_valor(d.get("valor_cafe")),
                int(bool(d.get("usar_temporada"))))
        cols = ("quarto_id,hospede_id,checkin,checkout,valor_diaria,desconto,status,obs,"
                "pessoas,cafe,valor_cafe,usar_temporada").split(",")
        with self.con:
            if id:
                self.con.execute(f"UPDATE reservas SET {','.join(k + '=?' for k in cols)} WHERE id=?",
                                 vals + (id,))
                return id
            return self.con.execute(
                f"INSERT INTO reservas({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                vals).lastrowid

    def listar_reservas(self):
        sql = ("SELECT r.*, q.nome AS quarto, h.nome AS hospede, "
               "COALESCE((SELECT SUM(valor) FROM pagamentos WHERE reserva_id=r.id),0) AS pago "
               "FROM reservas r JOIN quartos q ON q.id=r.quarto_id "
               "JOIN hospedes h ON h.id=r.hospede_id ORDER BY r.checkin DESC")
        out, temps = [], self.listar("temporadas")
        for r in self.con.execute(sql):
            d = dict(r)
            d.update(self.calcular_reserva(d, temps))
            d["saldo"] = c.saldo(d["total"], d["pago"])
            out.append(d)
        return out

    def excluir_reserva(self, id):
        self.excluir("reservas", id)

    def registrar_pagamento(self, reserva_id, data, valor, forma=""):
        valor = c.parse_valor(valor)
        if valor <= 0:
            raise ValueError("O valor deve ser maior que zero.")
        with self.con:
            self.con.execute("INSERT INTO pagamentos(reserva_id,data,valor,forma) VALUES(?,?,?,?)",
                             (reserva_id, c.para_iso(data), valor, forma))

    # ---------- Relatório ----------
    def relatorio(self, ini, fim):
        ini, fim = c.para_iso(ini), c.para_iso(fim)
        rec = self.con.execute("SELECT COALESCE(SUM(valor),0) FROM pagamentos "
                               "WHERE data BETWEEN ? AND ?", (ini, fim)).fetchone()[0]
        desp = self.con.execute("SELECT COALESCE(SUM(valor),0) FROM despesas "
                                "WHERE data BETWEEN ? AND ?", (ini, fim)).fetchone()[0]
        rs = [r for r in self.listar_reservas() if r["status"] != "Cancelada"]
        n_ocup = sum(c.noites_no_periodo(r["checkin"], r["checkout"], ini, fim) for r in rs)
        n_q = self.con.execute("SELECT COUNT(*) FROM quartos").fetchone()[0]
        a_receber = sum(r["saldo"] for r in rs if r["saldo"] > 0)
        return {"receitas": rec, "despesas": desp, "lucro": rec - desp,
                "ocupacao": c.taxa_ocupacao(n_ocup, n_q, ini, fim),
                "noites_ocupadas": n_ocup, "a_receber": a_receber}

    # ---------- Calendário de ocupação ----------
    def mapa_ocupacao(self, ano, mes):
        """Dados do calendário: ocupação por quarto/dia, cafés por dia e acréscimo de temporada."""
        dias = [date(ano, mes, i) for i in range(1, calendar.monthrange(ano, mes)[1] + 1)]
        reservas = [r for r in self.listar_reservas() if r["status"] != "Cancelada"]
        temps = self.listar("temporadas")
        quartos = []
        for q in self.listar("quartos", "nome"):
            celulas = {}
            for r in (x for x in reservas if x["quarto_id"] == q["id"]):
                ci, co = c.parse_data(r["checkin"]), c.parse_data(r["checkout"])
                for d in dias:
                    if ci <= d < co:  # noite ocupada; no dia do check-out o quarto fica livre
                        celulas[d.day] = {k: r[k] for k in ("id", "hospede", "quarto", "status", "checkin",
                                                            "checkout", "total", "saldo", "cafe", "pessoas")}
            quartos.append({"nome": q["nome"], "celulas": celulas})
        return {"dias": dias, "quartos": quartos,
                "cafes": {d.day: c.cafes_no_dia(reservas, d) for d in dias},
                "acrescimos": {d.day: c.acrescimo_na_data(d, temps) for d in dias}}
