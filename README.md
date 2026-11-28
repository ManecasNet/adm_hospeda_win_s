# Pousada Familiar

App desktop para Windows (Python 3.9+, sem dependências externas).

## Estrutura
- `core/database.py` – SQLite e esquema (banco em 
`pousada.db` criar o db aqui OU
`%APPDATA%\PousadaFamiliar\pousada.db`)
- `core/calculos.py` – funções puras: noites, totais, saldo, conflitos, ocupação, formatos
- `core/servicos.py` – regras de negócio e CRUD (classe `Pousada`)
- `core/importexport.py` – CSV (`;`, UTF-8, abre no Excel), backup e restauração
- `ui/app.py` – interface Tkinter; não contém regras
- `main.py` – ponto de entrada

## Recursos
- **Temporadas:** acréscimo (ou desconto, se negativo) em % sobre a diária base, aplicado noite a noite.
  Em sobreposição vale o maior acréscimo. Alterar uma temporada recalcula as reservas que a usam.
- **Café da manhã:** por reserva (pessoas x noites x valor). Valor padrão em Configurações.
- **Calendário:** quartos x dias do mês, com cafés a servir por dia e destaque de alta/baixa temporada.

## Uso
`python main.py`  |  Gerar .exe: execute `gerar_exe.bat`

### Gerar .exe: execute
pip install pyinstaller
pyinstaller --onefile --windowed --icon=logo.ico --name adm_hospeda main.py

###
CSV de importação (cabeçalho obrigatório): quartos `nome;capacidade;diaria`,
hóspedes `nome;telefone;documento;email`, despesas `data;descricao;categoria;valor`,
temporadas `nome;inicio;fim;acrescimo`.
