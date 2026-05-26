import os
import sqlite3
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "chave_secreta_para_o_trabalho"

# ==========================================================
# BANCO DE DADOS COMPLETO (COM PRONTUÁRIO DETALHADO)
# ==========================================================
def iniciar_banco():
    caminho_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(caminho_atual, "database.db")
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()

    # Tabela 1: Usuários autorizados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            senha TEXT
        )
    """)

    # Tabela 2: Prontuário detalhado dos detentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            documento TEXT,
            foto_url TEXT,
            familiar TEXT,
            motivo_prisao TEXT,
            faccao TEXT,
            cela_bloco TEXT,
            prontuario_medico TEXT
        )
    """)

    try:
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES ('admin', 'admin123')")
    except sqlite3.IntegrityError:
        pass 

    # Insere dados fictícios já no formato novo e detalhado
    cursor.execute("SELECT COUNT(*) FROM personas" if False else "SELECT COUNT(*) FROM pessoas")
    if cursor.fetchone()[0] == 0:
        dados_ficticios = [
            ("João Silva", "111.222.333-44", "https://avatar.iran.liara.run/public/1", "Maria Silva (Mãe)", "Artigo 157 - Roubo Qualificado", "Nenhuma (Neutro)", "Bloco A - Cela 02", "Hipertenso, Tipo Sanguíneo O+, Alergia a Dipirona"),
            ("João Souza", "555.666.777-88", "https://avatar.iran.liara.run/public/2", "Pedro Souza (Pai)", "Artigo 155 - Furto", "Primeiro Comando", "Bloco A - Cela 05", "Sem restrições médicas, Tipo Sanguíneo A-"),
            ("Maria Oliveira", "222.333.444-55", "https://avatar.iran.liara.run/public/55", "Carlos Oliveira (Irmão)", "Artigo 33 - Tráfico de Drogas", "Comando Vermelho", "Bloco B - Cela 12", "Asmática (Usa bombinha), Tipo Sanguíneo AB+"),
        ]
        cursor.executemany("""
            INSERT INTO pessoas (nome, documento, foto_url, familiar, motivo_prisao, faccao, cela_bloco, prontuario_medico) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, dados_ficticios)

    conn.commit()
    conn.close()

iniciar_banco()


# ==========================================================
# ROTAS E LÓGICA DAS PÁGINAS
# ==========================================================

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario_digitado = request.form["usuario"]
        senha_digitada = request.form["senha"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (usuario_digitado, senha_digitada))
        usuario_valido = cursor.fetchone()
        conn.close()

        if usuario_valido:
            return redirect(url_for("painel"))
        else:
            return render_template("login.html", erro="Usuário ou senha incorretos!")

    return render_template("login.html", erro=erro)

@app.route("/painel", methods=["GET"])
def painel():
    termo_busca = request.args.get("pesquisa", "")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if termo_busca:
        # Mantendo a vulnerabilidade de SQL Injection solicitada para a demonstração
        query = f"SELECT * FROM pessoas WHERE nome LIKE '%{termo_busca}%'"
        cursor.execute(query)
    else:
        cursor.execute("SELECT * FROM pessoas")

    resultados = cursor.fetchall()
    conn.close()
    return render_template("painel.html", pessoas=resultados, termo=termo_busca)

# ROTA DE CADASTRO COM TODOS OS NOVOS CAMPOS DO PRONTUÁRIO
@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    sucesso = False
    if request.method == "POST":
        nome_novo = request.form["nome"]
        doc_novo = request.form["documento"]
        foto_nova = request.form["foto_url"]
        familiar_novo = request.form["familiar"]
        motivo_novo = request.form["motivo_prisao"]
        faccao_nova = request.form["faccao"]
        cela_nova = request.form["cela_bloco"]
        medico_novo = request.form["prontuario_medico"]

        caminho_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_banco = os.path.join(caminho_atual, "database.db")
        conn = sqlite3.connect(caminho_banco)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO pessoas (nome, documento, foto_url, familiar, motivo_prisao, faccao, cela_bloco, prontuario_medico) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome_novo, doc_novo, foto_nova, familiar_novo, motivo_novo, faccao_nova, cela_nova, medico_novo))
        
        conn.commit()
        conn.close()
        sucesso = True

    return render_template("cadastrar.html", sucesso=sucesso)

# ROTA DE DETALHES CARREGANDO O PRONTUÁRIO DO BANCO
@app.route("/detalhes/<int:id_pessoa>")
def detalhes(id_pessoa):
    caminho_atual = os.path.dirname(os.path.abspath(__file__))
    caminho_banco = os.path.join(caminho_atual, "database.db")
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM pessoas WHERE id = ?", (id_pessoa,))
    pessoa_encontrada = cursor.fetchone()
    conn.close()
    
    if pessoa_encontrada:
        return render_template("detalhes.html", pessoa=pessoa_encontrada)
    else:
        return "Erro: Registro de prontuário não encontrado.", 404

if __name__ == "__main__":
    app.run(debug=True, port=8080)