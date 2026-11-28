"""Funções puras de cálculo e formatação. Sem banco, sem interface."""
from datetime import date, datetime, timedelta


def parse_data(s) -> date:
    if isinstance(s, date):
        return s
    s = str(s).strip()
    for f in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(f"Data inválida: '{s}' (use dd/mm/aaaa)")


def para_iso(s) -> str:
    return parse_data(s).isoformat()


def para_br(s) -> str:
    return parse_data(s).strftime("%d/%m/%Y") if s else ""


def parse_valor(s) -> float:
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    t = str(s).replace("R$", "").strip()
    if not t:
        return 0.0
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        raise ValueError(f"Valor inválido: '{s}'")


def moeda(v) -> str:
    s = f"{float(v or 0):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def noites(checkin, checkout) -> int:
    return (parse_data(checkout) - parse_data(checkin)).days


def acrescimo_na_data(dia, temporadas) -> float:
    """Percentual de acréscimo vigente no dia (maior valor, se houver sobreposição)."""
    dia = parse_data(dia)
    vals = [float(t["acrescimo"]) for t in temporadas
            if parse_data(t["inicio"]) <= dia <= parse_data(t["fim"])]
    return max(vals) if vals else 0.0


def total_hospedagem(checkin, checkout, diaria_base, temporadas=()) -> float:
    """Soma noite a noite, aplicando a temporada de cada data."""
    d, fim, total = parse_data(checkin), parse_data(checkout), 0.0
    while d < fim:
        total += diaria_base * (1 + acrescimo_na_data(d, temporadas) / 100)
        d += timedelta(days=1)
    return round(total, 2)


def total_cafe(n_noites, pessoas, valor_por_pessoa) -> float:
    return round(n_noites * max(1, int(pessoas or 1)) * valor_por_pessoa, 2)


def cafes_no_dia(reservas, dia) -> int:
    """Cafés a servir no dia: quem dormiu na noite anterior (checkin < dia <= checkout)."""
    dia = parse_data(dia)
    return sum(int(r["pessoas"] or 1) for r in reservas
               if r["cafe"] and r["status"] != "Cancelada"
               and parse_data(r["checkin"]) < dia <= parse_data(r["checkout"]))


def total_reserva(hospedagem, cafe=0.0, desconto=0.0) -> float:
    return max(0.0, round(hospedagem + cafe - desconto, 2))


def saldo(total, pago) -> float:
    return round(total - pago, 2)


def periodos_conflitam(ci_a, co_a, ci_b, co_b) -> bool:
    """Check-out no mesmo dia do check-in de outro hóspede NÃO conflita."""
    return parse_data(ci_a) < parse_data(co_b) and parse_data(ci_b) < parse_data(co_a)


def noites_no_periodo(checkin, checkout, ini, fim) -> int:
    """Noites da estadia que caem em [ini, fim] (ambos inclusive)."""
    a = max(parse_data(checkin), parse_data(ini))
    b = min(parse_data(checkout), parse_data(fim) + timedelta(days=1))
    return max(0, (b - a).days)


def taxa_ocupacao(noites_ocupadas, qtd_quartos, ini, fim) -> float:
    dias = (parse_data(fim) - parse_data(ini)).days + 1
    cap = qtd_quartos * dias
    return 0.0 if cap <= 0 else min(100.0, noites_ocupadas / cap * 100)
