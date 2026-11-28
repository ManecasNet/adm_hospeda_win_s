"""Interface Tkinter. Só apresenta e coleta dados; toda regra fica em core/."""
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk

from core import calculos as c
from core import importexport as ie
from core.database import caminho_padrao
from core.servicos import STATUS, TABELAS, Pousada

# (chave, rótulo, tipo)  tipo: txt | int | money | date
CAMPOS = {
    "quartos": [("nome", "Nome", "txt"), ("capacidade", "Capacidade", "int"), ("diaria", "Diária", "money")],
    "hospedes": [("nome", "Nome", "txt"), ("telefone", "Telefone", "txt"),
                 ("documento", "Documento", "txt"), ("email", "E-mail", "txt")],
    "despesas": [("data", "Data", "date"), ("descricao", "Descrição", "txt"),
                 ("categoria", "Categoria", "txt"), ("valor", "Valor", "money")],
    "temporadas": [("nome", "Nome", "txt"), ("inicio", "Início", "date"),
                   ("fim", "Fim", "date"), ("acrescimo", "Acréscimo (%)", "pct")],
}
SALVAR = {"quartos": "salvar_quarto", "hospedes": "salvar_hospede", "despesas": "salvar_despesa",
          "temporadas": "salvar_temporada"}
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
         "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES = {"Reservada": "#f4c26b", "Hospedado": "#7bc67e", "Finalizada": "#c9c9c9"}
COR_ALTA, COR_BAIXA = "#f8c9c4", "#c9ddf5"


def fmt(v, tipo):
    if tipo == "money":
        return c.moeda(v)
    if tipo == "date":
        return c.para_br(v)
    if tipo == "pct":
        return f"{float(v):+g}%"
    return "" if v is None else v


def erro(e):
    messagebox.showerror("Atenção", str(e))


class CrudTab(ttk.Frame):
    """Aba genérica de cadastro (quartos, hóspedes, despesas)."""

    def __init__(self, master, pousada, tabela):
        super().__init__(master, padding=8)
        self.p, self.tabela, self.campos, self.sel = pousada, tabela, CAMPOS[tabela], None
        form = ttk.LabelFrame(self, text="Cadastro", padding=8)
        form.pack(fill="x")
        self.vars = {}
        for i, (k, rot, _) in enumerate(self.campos):
            ttk.Label(form, text=rot).grid(row=0, column=i, sticky="w", padx=4)
            self.vars[k] = tk.StringVar()
            ttk.Entry(form, textvariable=self.vars[k], width=22).grid(row=1, column=i, padx=4)
        bt = ttk.Frame(form)
        bt.grid(row=2, column=0, columnspan=len(self.campos), pady=(8, 0), sticky="w")
        ttk.Button(bt, text="Salvar", command=self.salvar).pack(side="left", padx=2)
        ttk.Button(bt, text="Novo", command=self.limpar).pack(side="left", padx=2)
        ttk.Button(bt, text="Excluir", command=self.excluir).pack(side="left", padx=2)
        self.tv = ttk.Treeview(self, columns=[k for k, _, _ in self.campos], show="headings")
        for k, rot, _ in self.campos:
            self.tv.heading(k, text=rot)
            self.tv.column(k, width=140)
        self.tv.pack(fill="both", expand=True, pady=8)
        self.tv.bind("<<TreeviewSelect>>", self.selecionar)
        self.atualizar()

    def atualizar(self):
        self.tv.delete(*self.tv.get_children())
        for r in self.p.listar(self.tabela):
            self.tv.insert("", "end", iid=r["id"],
                           values=[fmt(r[k], t) for k, _, t in self.campos])

    def limpar(self):
        self.sel = None
        for v in self.vars.values():
            v.set("")

    def selecionar(self, _=None):
        if not self.tv.selection():
            return
        self.sel = int(self.tv.selection()[0])
        r = next(x for x in self.p.listar(self.tabela) if x["id"] == self.sel)
        for k, _, t in self.campos:
            self.vars[k].set(fmt(r[k], t) if t == "date" else ("" if r[k] is None else r[k]))

    def salvar(self):
        try:
            getattr(self.p, SALVAR[self.tabela])({k: v.get() for k, v in self.vars.items()}, self.sel)
        except Exception as e:
            return erro(e)
        self.limpar()
        self.atualizar()

    def excluir(self):
        if self.sel and messagebox.askyesno("Excluir", "Excluir o registro selecionado?"):
            try:
                self.p.excluir(self.tabela, self.sel)
            except ValueError as e:
                return erro(e)
            self.limpar()
            self.atualizar()


class ReservasTab(ttk.Frame):
    COLS = [("id", "Nº", 40), ("quarto", "Quarto", 90), ("hospede", "Hóspede", 140),
            ("checkin", "Check-in", 80), ("checkout", "Check-out", 80), ("noites", "Noites", 50),
            ("cafe", "Café", 50), ("total", "Total", 90), ("pago", "Pago", 90),
            ("saldo", "Saldo", 90), ("status", "Status", 85)]

    def __init__(self, master, pousada):
        super().__init__(master, padding=8)
        self.p, self.sel = pousada, None
        f = ttk.LabelFrame(self, text="Reserva", padding=8)
        f.pack(fill="x")
        self.v = {k: tk.StringVar() for k in ("quarto", "hospede", "checkin", "checkout", "valor_diaria",
                                              "desconto", "status", "obs", "pessoas", "valor_cafe")}
        self.v["cafe"], self.v["usar_temporada"] = tk.IntVar(), tk.IntVar(value=1)
        rots = [("quarto", "Quarto"), ("hospede", "Hóspede"), ("checkin", "Check-in (dd/mm/aaaa)"),
                ("checkout", "Check-out"), ("valor_diaria", "Diária base (R$)"), ("desconto", "Desconto (R$)"),
                ("status", "Status"), ("obs", "Observações"), ("pessoas", "Pessoas"),
                ("valor_cafe", "Café por pessoa/dia (R$)")]
        self.cb = {}
        for i, (k, r) in enumerate(rots):
            ttk.Label(f, text=r).grid(row=(i // 4) * 2, column=i % 4, sticky="w", padx=4)
            if k in ("quarto", "hospede", "status"):
                w = ttk.Combobox(f, textvariable=self.v[k], state="readonly", width=24,
                                 values=STATUS if k == "status" else [])
                self.cb[k] = w
            else:
                w = ttk.Entry(f, textvariable=self.v[k], width=26)
            w.grid(row=(i // 4) * 2 + 1, column=i % 4, padx=4, pady=(0, 4))
        ttk.Checkbutton(f, text="Café da manhã incluso", variable=self.v["cafe"]).grid(
            row=5, column=2, sticky="w", padx=4)
        ttk.Checkbutton(f, text="Aplicar diárias de temporada", variable=self.v["usar_temporada"]).grid(
            row=5, column=3, sticky="w", padx=4)
        self.cb["quarto"].bind("<<ComboboxSelected>>", self.preencher_diaria)
        bt = ttk.Frame(f)
        bt.grid(row=6, column=0, columnspan=4, sticky="w", pady=4)
        for t, cmd in [("Salvar", self.salvar), ("Novo", self.limpar), ("Excluir", self.excluir),
                       ("Registrar pagamento", self.pagar)]:
            ttk.Button(bt, text=t, command=cmd).pack(side="left", padx=2)
        self.previa = ttk.Label(f, font=("Segoe UI", 10, "bold"))
        self.previa.grid(row=7, column=0, columnspan=4, sticky="w", padx=4)
        self.tv = ttk.Treeview(self, columns=[k for k, _, _ in self.COLS], show="headings")
        for k, r, w in self.COLS:
            self.tv.heading(k, text=r)
            self.tv.column(k, width=w)
        self.tv.pack(fill="both", expand=True, pady=8)
        self.tv.bind("<<TreeviewSelect>>", self.selecionar)
        self.atualizar()
        for var in self.v.values():
            var.trace_add("write", self.prever)
        self.limpar()

    def _dados(self):
        d = {k: v.get() for k, v in self.v.items()}
        q = self.quartos.get(d["quarto"])
        d["quarto_id"] = q["id"] if q else None
        d["hospede_id"] = self.hospedes.get(d["hospede"])
        return d

    def prever(self, *_):
        try:
            r = self.p.calcular_reserva(self._dados())
            t = f"{r['noites']} noite(s)  |  Hospedagem {c.moeda(r['hospedagem'])}"
            if r["cafe_total"]:
                t += f"  |  Café {c.moeda(r['cafe_total'])}"
            t += f"  |  TOTAL {c.moeda(r['total'])}"
        except Exception:
            t = ""
        self.previa.config(text=t)

    def atualizar(self):
        self.quartos = {q["nome"]: q for q in self.p.listar("quartos", "nome")}
        self.hospedes = {f'{h["nome"]} (#{h["id"]})': h["id"] for h in self.p.listar("hospedes", "nome")}
        self.cb["quarto"]["values"] = list(self.quartos)
        self.cb["hospede"]["values"] = list(self.hospedes)
        self.tv.delete(*self.tv.get_children())
        self.reservas = {r["id"]: r for r in self.p.listar_reservas()}
        for r in self.reservas.values():
            vals = [r["id"], r["quarto"], r["hospede"], c.para_br(r["checkin"]), c.para_br(r["checkout"]),
                    r["noites"], f'{r["pessoas"]}p' if r["cafe"] else "", c.moeda(r["total"]),
                    c.moeda(r["pago"]), c.moeda(r["saldo"]), r["status"]]
            self.tv.insert("", "end", iid=r["id"], values=vals)

    def preencher_diaria(self, _=None):
        q = self.quartos.get(self.v["quarto"].get())
        if q:
            self.v["valor_diaria"].set(f'{q["diaria"]:.2f}'.replace(".", ","))

    def limpar(self):
        self.sel = None
        cafe = f'{c.parse_valor(self.p.config("cafe_valor", "0")):.2f}'.replace(".", ",")
        padrao = {"status": STATUS[0], "pessoas": "1", "valor_cafe": cafe, "cafe": 0, "usar_temporada": 1}
        for k, v in self.v.items():
            v.set(padrao.get(k, ""))

    def selecionar(self, _=None):
        if not self.tv.selection():
            return
        self.sel = int(self.tv.selection()[0])
        r = self.reservas[self.sel]
        self.v["quarto"].set(r["quarto"])
        self.v["hospede"].set(next((k for k, i in self.hospedes.items() if i == r["hospede_id"]), ""))
        for k in ("valor_diaria", "desconto", "status", "obs", "pessoas", "valor_cafe"):
            self.v[k].set(r[k] if r[k] is not None else "")
        self.v["cafe"].set(int(r["cafe"]))
        self.v["usar_temporada"].set(int(r["usar_temporada"]))
        self.v["checkin"].set(c.para_br(r["checkin"]))
        self.v["checkout"].set(c.para_br(r["checkout"]))

    def salvar(self):
        try:
            self.p.salvar_reserva(self._dados(), self.sel)
        except Exception as e:
            return erro(e)
        self.limpar()
        self.atualizar()

    def excluir(self):
        if self.sel and messagebox.askyesno("Excluir", "Excluir a reserva e seus pagamentos?"):
            self.p.excluir_reserva(self.sel)
            self.limpar()
            self.atualizar()

    def pagar(self):
        if not self.sel:
            return erro("Selecione uma reserva na lista.")
        r = self.reservas[self.sel]
        val = simpledialog.askstring("Pagamento", f"Saldo: {c.moeda(r['saldo'])}\nValor pago (R$):")
        if not val:
            return
        forma = simpledialog.askstring("Pagamento", "Forma (Pix, dinheiro, cartão...):") or ""
        try:
            self.p.registrar_pagamento(self.sel, date.today(), val, forma)
        except Exception as e:
            return erro(e)
        self.atualizar()


class CalendarioTab(ttk.Frame):
    """Grade quartos x dias do mês, com cafés do dia e destaque das temporadas."""
    NOME, LARG, ALT, TOPO = 120, 27, 28, 38

    def __init__(self, master, pousada):
        super().__init__(master, padding=8)
        self.p = pousada
        hoje = date.today()
        self.ano, self.mes = hoje.year, hoje.month
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="<", width=3, command=lambda: self.mover(-1)).pack(side="left")
        self.titulo = ttk.Label(top, font=("Segoe UI", 12, "bold"), width=20, anchor="center")
        self.titulo.pack(side="left", padx=6)
        ttk.Button(top, text=">", width=3, command=lambda: self.mover(1)).pack(side="left")
        ttk.Button(top, text="Hoje", command=self.hoje).pack(side="left", padx=8)
        for txt, cor in [("Baixa temporada", COR_BAIXA), ("Alta temporada", COR_ALTA),
                         *[(k, v) for k, v in reversed(list(CORES.items()))]]:
            tk.Label(top, text=f" {txt} ", bg=cor).pack(side="right", padx=2)
        self.cv = tk.Canvas(self, bg="white", highlightthickness=0)
        self.cv.pack(fill="x", pady=8)
        self.info = ttk.Label(self, text="Clique em uma reserva para ver os detalhes.")
        self.info.pack(anchor="w")

    def mover(self, delta):
        m = self.mes - 1 + delta
        self.ano, self.mes = self.ano + m // 12, m % 12 + 1
        self.atualizar()

    def hoje(self):
        self.ano, self.mes = date.today().year, date.today().month
        self.atualizar()

    def detalhe(self, r):
        cafe = f" | café para {r['pessoas']}" if r["cafe"] else ""
        self.info.config(text=(f"#{r['id']} {r['hospede']} - {r['quarto']} | {c.para_br(r['checkin'])} a "
                               f"{c.para_br(r['checkout'])} | Total {c.moeda(r['total'])} | "
                               f"Saldo {c.moeda(r['saldo'])} | {r['status']}{cafe}"))

    def atualizar(self):
        m = self.p.mapa_ocupacao(self.ano, self.mes)
        self.titulo.config(text=f"{MESES[self.mes - 1]} {self.ano}")
        cv, N, L, A, T = self.cv, self.NOME, self.LARG, self.ALT, self.TOPO
        cv.delete("all")
        linhas = len(m["quartos"]) + 1
        cv.config(width=N + L * len(m["dias"]), height=T + A * linhas + 2)
        hoje, sem = date.today(), "SEGTERQUAQUISEXSABDOM"
        for d in m["dias"]:
            x, acr = N + (d.day - 1) * L, m["acrescimos"][d.day]
            cv.create_rectangle(x, 0, x + L, T, fill=COR_ALTA if acr > 0 else COR_BAIXA if acr < 0 else "#f0f0f0",
                                outline="#d00" if d == hoje else "#ccc", width=2 if d == hoje else 1)
            cv.create_text(x + L / 2, 12, text=str(d.day), font=("Segoe UI", 9, "bold"))
            cv.create_text(x + L / 2, 27, text=sem[d.weekday() * 3:d.weekday() * 3 + 3], font=("Segoe UI", 6))
        textos = []
        for i, q in enumerate(m["quartos"]):
            y = T + i * A
            cv.create_text(6, y + A / 2, text=q["nome"], anchor="w", font=("Segoe UI", 9, "bold"))
            for d in m["dias"]:
                x, cel = N + (d.day - 1) * L, q["celulas"].get(d.day)
                tag = f"r{cel['id']}" if cel else ""
                cv.create_rectangle(x, y, x + L, y + A, outline="#ddd",
                                    fill=CORES.get(cel["status"], "#eee") if cel else "white", tags=(tag,))
                if cel:
                    cv.tag_bind(tag, "<Button-1>", lambda e, r=cel: self.detalhe(r))
                    if d.day == 1 or c.para_iso(d) == cel["checkin"]:
                        textos.append((x + 3, y + A / 2, cel["hospede"].split()[0], tag))
        for x, y, t, tag in textos:  # nomes por cima das células
            cv.create_text(x, y, text=t, anchor="w", font=("Segoe UI", 8), tags=(tag,))
        y = T + (linhas - 1) * A
        cv.create_text(6, y + A / 2, text="Cafés a servir", anchor="w", font=("Segoe UI", 9, "bold"))
        for d in m["dias"]:
            x, n = N + (d.day - 1) * L, m["cafes"][d.day]
            cv.create_rectangle(x, y, x + L, y + A, outline="#ddd", fill="#fff4d6")
            if n:
                cv.create_text(x + L / 2, y + A / 2, text=str(n))


class RelatorioTab(ttk.Frame):
    def __init__(self, master, pousada):
        super().__init__(master, padding=12)
        self.p = pousada
        hoje = date.today()
        self.ini = tk.StringVar(value=hoje.replace(day=1).strftime("%d/%m/%Y"))
        self.fim = tk.StringVar(value=hoje.strftime("%d/%m/%Y"))
        top = ttk.Frame(self)
        top.pack(anchor="w")
        for t, v in (("De", self.ini), ("até", self.fim)):
            ttk.Label(top, text=t).pack(side="left", padx=4)
            ttk.Entry(top, textvariable=v, width=12).pack(side="left")
        ttk.Button(top, text="Calcular", command=self.atualizar).pack(side="left", padx=8)
        self.saida = tk.Label(self, justify="left", font=("Segoe UI", 13), anchor="nw")
        self.saida.pack(fill="x", pady=16)
        self.atualizar()

    def atualizar(self):
        try:
            r = self.p.relatorio(self.ini.get(), self.fim.get())
        except Exception as e:
            return erro(e)
        self.saida.config(text=(
            f"Receitas recebidas:  {c.moeda(r['receitas'])}\n"
            f"Despesas:                 {c.moeda(r['despesas'])}\n"
            f"Lucro:                      {c.moeda(r['lucro'])}\n\n"
            f"Ocupação:               {r['ocupacao']:.1f}%  ({r['noites_ocupadas']} noites)\n"
            f"A receber (reservas):  {c.moeda(r['a_receber'])}"))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pousada Familiar - Gestão")
        self.geometry("1000x620")
        self.p = Pousada()
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.abas = {
            "Reservas": ReservasTab(nb, self.p), "Calendário": CalendarioTab(nb, self.p),
            "Quartos": CrudTab(nb, self.p, "quartos"), "Hóspedes": CrudTab(nb, self.p, "hospedes"),
            "Temporadas": CrudTab(nb, self.p, "temporadas"), "Despesas": CrudTab(nb, self.p, "despesas"),
            "Relatório": RelatorioTab(nb, self.p)}
        for nome, aba in self.abas.items():
            nb.add(aba, text=nome)
        nb.bind("<<NotebookTabChanged>>", lambda e: self.abas[nb.tab(nb.select(), "text")].atualizar())
        m = tk.Menu(self)
        arq = tk.Menu(m, tearoff=0)
        arq.add_command(label="Exportar CSV...", command=self.exportar)
        arq.add_command(label="Importar CSV...", command=self.importar)
        arq.add_separator()
        arq.add_command(label="Fazer backup...", command=self.backup)
        arq.add_command(label="Sair", command=self.destroy)
        m.add_cascade(label="Arquivo", menu=arq)
        cfg = tk.Menu(m, tearoff=0)
        cfg.add_command(label="Valor padrão do café da manhã...", command=self.config_cafe)
        m.add_cascade(label="Configurações", menu=cfg)
        self.config(menu=m)

    def config_cafe(self):
        atual = self.p.config("cafe_valor", "0")
        v = simpledialog.askstring("Café da manhã", "Valor por pessoa/dia (R$):", initialvalue=atual)
        if v:
            try:
                self.p.definir_config("cafe_valor", c.parse_valor(v))
            except ValueError as e:
                return erro(e)
            messagebox.showinfo("Café da manhã", "Valor salvo. Será sugerido nas próximas reservas.")

    def _tabela(self, opcoes):
        t = simpledialog.askstring("Tabela", "Qual tabela? (" + ", ".join(opcoes) + ")")
        return t.strip().lower() if t else None

    def exportar(self):
        t = self._tabela(list(ie.EXPORTAVEIS))
        if t not in ie.EXPORTAVEIS:
            return
        f = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"{t}.csv")
        if f:
            n = ie.exportar_csv(self.p, t, f)
            messagebox.showinfo("Exportação", f"{n} registros exportados.")

    def importar(self):
        t = self._tabela(list(TABELAS))
        if t not in TABELAS:
            return
        f = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if f:
            try:
                n = ie.importar_csv(self.p, t, f)
                messagebox.showinfo("Importação", f"{n} registros importados.")
            except Exception as e:
                return erro(e)
            for a in self.abas.values():
                a.atualizar()

    def backup(self):
        f = filedialog.asksaveasfilename(defaultextension=".db",
                                         initialfile=f"backup_pousada_{date.today():%Y%m%d}.db")
        if f:
            ie.backup(self.p, f)
            messagebox.showinfo("Backup", f"Backup salvo.\nBanco em uso: {caminho_padrao()}")
