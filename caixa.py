import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import sqlite3
import os
import platform
from tkcalendar import DateEntry
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- Banco de dados ---
conn = sqlite3.connect('caixa.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS caixa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,
        descricao TEXT NOT NULL,
        valor REAL NOT NULL,
        data TEXT NOT NULL,
        forma_pgto TEXT
    )
''')
try:
    cursor.execute("ALTER TABLE caixa ADD COLUMN forma_pgto TEXT")
except sqlite3.OperationalError:
    pass  # coluna já existe
conn.commit()

# --- Utilitários ---
def converter_data(data_str):
    try:
        # Este formato bate com o que o DateEntry retorna
        return datetime.strptime(data_str, "%d-%m-%Y").date()
    except ValueError:
        messagebox.showerror("Erro", f"Data inválida: {data_str}")
        return None

def inserir_lancamento(tipo, descricao, valor, data_lanc, forma_pgto):
    cursor.execute('INSERT INTO caixa (tipo, descricao, valor, data, forma_pgto) VALUES (?, ?, ?, ?, ?)',
                   (tipo, descricao, valor, data_lanc, forma_pgto))
    conn.commit()

def atualizar_lancamento(id_lanc, tipo, descricao, valor, forma_pgto):
    cursor.execute('UPDATE caixa SET tipo=?, descricao=?, valor=?, forma_pgto=? WHERE id=?',
                   (tipo, descricao, valor, forma_pgto, id_lanc))
    conn.commit()

def excluir_lancamento(id_lanc):
    cursor.execute('DELETE FROM caixa WHERE id=?', (id_lanc,))
    conn.commit()

def buscar_lancamentos(data_inicio, data_fim):
    cursor.execute('SELECT id, data, tipo, descricao, valor FROM caixa WHERE data BETWEEN ? AND ?',
                   (data_inicio, data_fim))
    return cursor.fetchall()

# --- Interface Gráfica ---
root = tk.Tk()
root.title("Controle de Caixa Diário - V1")
root.geometry("750x500")

btn_style = {'width': 13, 'height': 1, 'padx': 3, 'pady': 2}

# Estilos para Combobox
style = ttk.Style()
style.map("Entrada.TCombobox",
          foreground=[('readonly', 'blue')],
          fieldbackground=[('readonly', 'white')])
style.map("Saida.TCombobox",
          foreground=[('readonly', 'red')],
          fieldbackground=[('readonly', 'white')])

frame_topo = tk.Frame(root)
frame_topo.pack(pady=10)

tk.Label(frame_topo, text="Data Início:").pack(side='left')
entry_data_inicio = DateEntry(frame_topo, width=12, background='darkblue', foreground='white',
                              borderwidth=2, date_pattern='dd-mm-yyyy')
entry_data_inicio.set_date(date.today())
entry_data_inicio.pack(side='left')

tk.Label(frame_topo, text="  Data Fim:").pack(side='left')
entry_data_fim = DateEntry(frame_topo, width=12, background='darkblue', foreground='white',
                           borderwidth=2, date_pattern='dd-mm-yyyy')
entry_data_fim.set_date(date.today())
entry_data_fim.pack(side='left')

tk.Button(frame_topo, text="Filtrar", command=lambda: atualizar_lista(),
          bg="orange", fg="black", **btn_style).pack(side='left', padx=5)
tk.Button(frame_topo, text="RELATORIO", command=lambda: gerar_pdf(),
          bg="purple", fg="white", **btn_style).pack(side='left', padx=5)
btn_fechar = tk.Button(frame_topo, text="✖", command=root.quit,
                       bg="#408", fg="red", font=("Arial", 10, "bold"),
                       width=3, height=1)
btn_fechar.pack(side="left", anchor="w", padx=0)

# Tabela
columns = ('ID', "data",'Tipo', 'Descrição', 'Valor')
tree = ttk.Treeview(root, columns=columns, show='headings')

tree.heading('ID', text='ID')
tree.column('ID', width=20, anchor='center')

tree.heading('data', text='Data')
tree.column('data', width=40, anchor='center')

tree.heading('Tipo', text='Tipo')
tree.column('Tipo', width=40, anchor='center')

tree.heading('Descrição', text='Descrição do Lançamento')
tree.column('Descrição', width=370)

tree.heading('Valor', text='Valor')
tree.column('Valor', width=100, anchor='e')

if tree.get_children():
    tree.see(tree.get_children()[-1])  # Mostra o último item da lista

tree.pack(fill='both', expand=True, padx=10, pady=10)

# Totais
# Totais com cores
frame_totais = tk.Frame(root)
frame_totais.pack()

# Totais alinhados à direita inferior
frame_totais = tk.Frame(root)
frame_totais.pack(fill='x', side='bottom', pady=5)

label_saldo = tk.Label(frame_totais, text="Saldo Geral: R$ 0.00", fg="blue", font=("Segoe UI", 10, "bold"))
label_saldo.pack(side='right', padx=10)

label_saidas = tk.Label(frame_totais, text="Saídas: R$ 0.00", fg="red", font=("Segoe UI", 10, "bold"))
label_saidas.pack(side='right', padx=10)

label_entradas = tk.Label(frame_totais, text="Entradas: R$ 0.00", fg="green", font=("Segoe UI", 10, "bold"))
label_entradas.pack(side='right', padx=10)

# Botões
frame_botoes = tk.Frame(root)
frame_botoes.pack(pady=10, anchor='w', padx=10)

def atualizar_lista():
    data_inicio = converter_data(entry_data_inicio.get())
    data_fim = converter_data(entry_data_fim.get())
    for item in tree.get_children():
        tree.delete(item)
    lancamentos = buscar_lancamentos(data_inicio, data_fim)
    total_entradas = total_saidas = 0
    for lanc in lancamentos:
        id_lanc, data_inicio, tipo, desc, valor = lanc
        tree.insert('', 'end', iid=id_lanc, values=(id_lanc, data_inicio, tipo, desc, f'R$ {valor:.2f}'))
        if tipo == 'ENTRADA':
            total_entradas += valor
        else:
            total_saidas += valor
    label_entradas.config(text=f"Entradas: R$ {total_entradas:.2f}")
    label_saidas.config(text=f"Saídas: R$ {total_saidas:.2f}")
    label_saldo.config(text=f"Saldo: R$ {(total_entradas - total_saidas):.2f}")

# Rola para o último item
    if tree.get_children():
        tree.see(tree.get_children()[-1])



# INCLUIR O LANCAMENTO
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from datetime import date

def incluir_lancamento():
    def salvar():
        tipo = var_tipo.get()
        forma_pgto = var_pagamento.get()
        desc = entry_desc.get().strip()
        try:
            valor = float(entry_valor.get().replace(",", "."))
        except:
            messagebox.showerror("Erro", "Valor inválido")
            return
        if not forma_pgto:
            messagebox.showerror("Erro", "Selecione uma forma de pagamento")
            return
        data_lanc = converter_data(entry_data_inicio.get())
        if not data_lanc:
            return
        data_lanc = data_lanc.strftime('%Y-%m-%d')
        if not data_lanc:
            return

        inserir_lancamento(tipo, desc, valor, data_lanc, forma_pgto)
        top.destroy()
        atualizar_lista()

    def atualizar_cor(*args):
        estilo = "ENTRADA.TCombobox" if var_tipo.get() == "ENTRADA" else "SAÍDA.TCombobox"
        combo_tipo.configure(style=estilo)

    top = tk.Toplevel(root)
    top.title("NOVO Lançamento de Caixa")
    top.geometry("600x220")
    top.resizable(False, False)
    top.configure(bg="#2c2c2c")

    fonte = ('Segoe UI', 10)

    # Linha 0 - Data
    tk.Label(top, text="Data:", font=fonte, bg="#2c2c2c", fg="white").grid(row=0, column=0, padx=10, pady=5, sticky="e")
    entry_data_inicio = DateEntry(top, width=12, background='darkblue', foreground='white',
                                  borderwidth=2, date_pattern='dd-mm-yyyy')
    entry_data_inicio.set_date(date.today())
    entry_data_inicio.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    # Linha 1 - Tipo e Forma de Pagamento
    tk.Label(top, text="Tipo:", font=fonte, bg="#2c2c2c", fg="white").grid(row=1, column=0, padx=10, pady=8, sticky="e")
    var_tipo = tk.StringVar(value="ENTRADA")
    combo_tipo = ttk.Combobox(top, textvariable=var_tipo, values=["ENTRADA", "SAÍDA"], state="readonly", width=15)
    combo_tipo.grid(row=1, column=1, padx=5, pady=8, sticky="w")
    var_tipo.trace_add("write", atualizar_cor)
    atualizar_cor()

    tk.Label(top, text="Forma Pgto:", font=fonte, bg="#2c2c2c", fg="white").grid(row=1, column=2, padx=10, pady=8, sticky="e")
    var_pagamento = tk.StringVar()
    combo_pgto = ttk.Combobox(top, textvariable=var_pagamento, values=[
        "DINHEIRO", "PIX", "CARTÃO", "CHEQUE", "CREDIÁRIO", "BOLETO"
    ], state="readonly", width=17)
    combo_pgto.grid(row=1, column=3, padx=5, pady=8, sticky="w")
    combo_pgto.set("DINHEIRO")

    # Linha 2 - Descrição
    tk.Label(top, text="Descrição:", font=fonte, bg="#2c2c2c", fg="white").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_desc = tk.Entry(top, width=70)
    entry_desc.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="w")
    entry_desc.focus_set()

    # Linha 3 - Valor
    tk.Label(top, text="Valor (R$):", font=fonte, bg="#2c2c2c", fg="white").grid(row=3, column=0, padx=10, pady=5, sticky="e")
    entry_valor = tk.Entry(top, width=15)
    entry_valor.grid(row=3, column=1, padx=5, pady=5, sticky="w")

    # Linha 4 - Botões
    frame_botoes = tk.Frame(top, bg="#2c2c2c")
    frame_botoes.grid(row=4, column=0, columnspan=4, pady=10)

    btn_salvar = tk.Button(frame_botoes, text="💾 Salvar", command=salvar, bg="#28a745", fg="white", width=12)
    btn_salvar.pack(side="left", padx=10)

    btn_fechar = tk.Button(top, text="✖", command=top.destroy,
                           bg="#444", fg="white", width=2, height=1,
                           font=("Arial", 10, "bold"), bd=0, relief="flat")
    btn_fechar.place(relx=1.0, x=-10, y=10, anchor="ne")

    top.bind('<Return>', lambda e: salvar())
    top.bind('<Escape>', lambda e: top.destroy())






# EDITAR O LANCAMENTO
def editar_lancamento():
    selecionado = tree.selection()
    if not selecionado:
        messagebox.showinfo("Aviso", "Selecione um lançamento para editar.")
        return

    id_lanc = int(selecionado[0])
    valores = tree.item(id_lanc, 'values')
    if len(valores) < 4:
        messagebox.showerror("Erro", "O lançamento selecionado não possui todos os dados necessários.")
        return

    tipo_atual = valores[1]
    desc_atual = valores[2]

    valor_texto = valores[3].replace("R$", "").strip()
    try:
        valor_atual = float(valor_texto)
    except ValueError:
        messagebox.showerror("Erro", f"Valor inválido: {valores[3]}")
        return

    forma_pgto_atual = valores[4] if len(valores) > 4 else "DINHEIRO"

    def salvar_edicao():
        tipo = var_tipo.get()
        desc = entry_desc.get().strip()
        forma_pgto = var_pagamento.get()
        try:
            valor = float(entry_valor.get().replace(".", "").replace(",", "."))
        except:
            messagebox.showerror("Erro", "Valor inválido")
            return

        if not forma_pgto:
            messagebox.showerror("Erro", "Selecione a forma de pagamento")
            return

        atualizar_lancamento(id_lanc, tipo, desc, valor, forma_pgto)
        top.destroy()
        atualizar_lista()

    def atualizar_cor(*args):
        estilo = "Entrada.TCombobox" if var_tipo.get() == "ENTRADA" else "SAÍDA.TCombobox"
        combo_tipo.configure(style=estilo)

    top = tk.Toplevel(root)
    top.title("EDITANDO Lançamento de Caixa")
    top.geometry("600x200")
    top.resizable(False, False)
    top.configure(bg="#2c2c2c")

    fonte = ("Segoe UI", 10)

    # Linha 1 - Tipo e Forma de Pagamento
    tk.Label(top, text="Tipo:", font=fonte, bg="#2c2c2c", fg="white").grid(row=0, column=0, padx=10, pady=8, sticky="e")
    var_tipo = tk.StringVar(value=tipo_atual)
    combo_tipo = ttk.Combobox(top, textvariable=var_tipo, values=["ENTRADA", "SAÍDA"], state="readonly", width=15)
    combo_tipo.grid(row=0, column=1, padx=5, pady=8, sticky="w")
    var_tipo.trace_add("write", atualizar_cor)
    atualizar_cor()

    tk.Label(top, text="Forma Pgto:", font=fonte, bg="#2c2c2c", fg="white").grid(row=0, column=2, padx=10, pady=8, sticky="e")
    var_pagamento = tk.StringVar(value=forma_pgto_atual)
    combo_pgto = ttk.Combobox(top, textvariable=var_pagamento, values=[
        "DINHEIRO", "PIX", "CARTÃO", "CHEQUE", "CREDIÁRIO", "BOLETO"
    ], state="readonly", width=17)
    combo_pgto.grid(row=0, column=3, padx=5, pady=8, sticky="w")

    # Linha 2 - Descrição (campo largo)
    tk.Label(top, text="Descrição:", font=fonte, bg="#2c2c2c", fg="white").grid(row=1, column=0, padx=10, pady=5, sticky="e")
    entry_desc = tk.Entry(top, width=70)
    entry_desc.insert(0, desc_atual)
    entry_desc.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="w")

    # Linha 3 - Valor
    tk.Label(top, text="Valor (R$):", font=fonte, bg="#2c2c2c", fg="white").grid(row=2, column=0, padx=10, pady=5, sticky="e")
    entry_valor = tk.Entry(top, justify="right", width=15)
    entry_valor.insert(0, f"{valor_atual:,.2f}".replace(".", "X").replace(",", ".").replace("X", ","))
    entry_valor.grid(row=2, column=1, padx=5, pady=5, sticky="w")
    entry_valor.focus_set()
    entry_valor.select_range(0, tk.END)

    # Linha 4 - Botões
    frame_botoes = tk.Frame(top, bg="#2c2c2c")
    frame_botoes.grid(row=3, column=0, columnspan=4, pady=10, sticky="e")

    btn_salvar = tk.Button(frame_botoes, text="💾 Salvar", command=salvar_edicao, bg="blue", fg="white", width=12)
    btn_salvar.pack(side="left", padx=10)

    btn_fechar = tk.Button(top, text="✖", command=top.destroy,
                       bg="#444", fg="white", width=2, height=1,
                       font=("Arial", 10, "bold"), bd=0, relief="flat")
    btn_fechar.place(relx=1.0, x=-10, y=10, anchor="ne")

    top.bind('<Return>', lambda e: salvar_edicao())
    top.bind('<Escape>', lambda e: top.destroy())















def deletar_lancamento():
    selecionado = tree.selection()
    if not selecionado:
        messagebox.showinfo("Aviso", "Selecione um lançamento.")
        return
    id_lanc = selecionado[0]
    if messagebox.askyesno("Confirmação", "Deseja realmente excluir este lançamento?"):
        excluir_lancamento(id_lanc)
        atualizar_lista()



# GERANDO O RELATORIO EM PDF DO CAIXA
def gerar_pdf():
    c = canvas.Canvas("relatorio_caixa.pdf", pagesize=A4)
    largura, altura = A4
    y = altura - 50

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Relatório de Caixa: {entry_data_inicio.get()} a {entry_data_fim.get()}")
    y -= 30

    # Cabeçalhos
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "ID")
    c.drawString(85, y, "Data")
    c.drawString(150, y, "Descrição")
    c.drawString(380, y, "Tipo")
    c.drawRightString(500, y, "Valor (R$)")
    y -= 15
    c.line(50, y, 550, y)
    y -= 15

    c.setFont("Helvetica", 11)
    total_entradas = total_saidas = 0

    for item in tree.get_children():
        valores = tree.item(item)["values"]

        # Assumindo que as colunas estão nessa ordem na treeview:
        # ID, Data, Descrição, Tipo, Valor
        id_lanc = valores[0]
        data_lanc = valores[1]
        descricao = valores[3]
        tipo = valores[2]
        valor_str = valores[4]

        # Converter valor de "R$ 123,45" para float
        valor = float(valor_str.replace("R$", "").replace(".", "").replace(",", ".").strip())

        # Soma valores
        if tipo == "Entrada":
            total_entradas += valor
        else:
            total_saidas += valor

        c.drawString(50, y, str(id_lanc))
        c.drawString(85, y, data_lanc)
        c.drawString(150, y, descricao[:32])
        c.drawString(380, y, tipo)
        c.drawRightString(500, y, valor_str)

        y -= 20
        if y < 100:
            c.showPage()
            y = altura - 50

    # Totais
    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Total Entradas:")
    c.drawRightString(500, y, f"R$ {total_entradas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 20
    c.drawString(50, y, "Total Saídas:")
    c.drawRightString(500, y, f"R$ {total_saidas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 20
    c.drawString(50, y, "Saldo Geral:")
    saldo = total_entradas - total_saidas
    c.drawRightString(500, y, f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    c.save()

    # Abrir PDF
    if platform.system() == 'Windows':
        os.startfile("relatorio_caixa.pdf")
    elif platform.system() == 'Darwin':
        os.system("open relatorio_caixa.pdf")
    else:
        os.system("xdg-open relatorio_caixa.pdf")







# Botões finais
tk.Button(frame_botoes, text="NOVO", command=incluir_lancamento, bg="green", fg="white", **btn_style).pack(side='left', padx=5)
tk.Button(frame_botoes, text="Editar", command=editar_lancamento, bg="blue", fg="white", **btn_style).pack(side='left', padx=5)
tk.Button(frame_botoes, text="Excluir", command=deletar_lancamento, bg="red", fg="white", **btn_style).pack(side='left', padx=5)

# Inicialização
atualizar_lista()
root.mainloop()
