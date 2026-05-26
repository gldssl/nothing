import os
import sqlite3
import pandas as pd
from werkzeug.utils import secure_filename
from flask import Flask, redirect, render_template, request, url_for, send_file

app = Flask(__name__)
app.secret_key = "chave_secreta_para_o_trabalho"

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def iniciar_banco():
    caminho_banco = "database.db"
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT, documento TEXT, numero_prontuario TEXT, foto_url TEXT,
            familiar TEXT, motivo_prisao TEXT, faccao TEXT, cela_bloco TEXT, prontuario_medico TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE pessoas ADD COLUMN numero_prontuario TEXT;")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES ('admin', 'admin123')")
    except sqlite3.IntegrityError:
        pass 

    conn.commit()
    conn.close()

iniciar_banco()

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario_digitado = request.form.get("usuario")
        senha_digitada = request.form.get("senha")
        
        query = f"SELECT * FROM usuarios WHERE usuario = '{usuario_digitado}' AND senha = '{senha_digitada}'"
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            if cursor.fetchone():
                return redirect("/painel")
            else:
                erro = "Usuário ou senha incorretos"
        except Exception as e:
            erro = "Erro de conexão."
        conn.close()
    return render_template("login.html", erro=erro)

@app.route("/painel", methods=["GET"])
def painel():
    # 🔍 Captura o termo digitado na barra de pesquisa (o 'name="pesquisa"' do HTML)
    termo = request.args.get("pesquisa", "").strip()
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Se o usuário digitou algo na busca
    if termo:
        # Busca registros onde o nome OU o número do prontuário contenham o termo digitado
        query = "SELECT * FROM pessoas WHERE nome LIKE ? OR numero_prontuario LIKE ?"
        cursor.execute(query, (f"%{termo}%", f"%{termo}%"))
    else:
        # Se a barra de busca estiver vazia, traz todos os detentos normalmente
        cursor.execute("SELECT * FROM pessoas")
    
    # Busca todas as linhas
    dados = cursor.fetchall()
    # Busca os nomes das colunas
    colunas = [d[0] for d in cursor.description]
    
    # Cria a lista de dicionários
    lista_pessoas = []
    for linha in dados:
        lista_pessoas.append(dict(zip(colunas, linha)))
        
    conn.close()
    
    # Enviamos também a variável 'termo' de volta para o HTML para manter o texto na barra de busca
    return render_template("painel.html", pessoas=lista_pessoas, termo=termo)


@app.route("/detalhes/<int:id>", methods=["GET"])
def detalhes(id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pessoas WHERE id = ?", (id,))
    pessoa = cursor.fetchone()
    conn.close()
    if pessoa:
        return render_template("detalhes.html", pessoa=pessoa)
    return redirect("/painel")

# 🛠️ NOVA ROTA: Carregar a página de Edição ou Salvar as alterações
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == "POST":
        # Se o usuário enviou o formulário de edição, atualiza os dados no banco
        nome = request.form["nome"]
        documento = request.form["documento"]
        numero_prontuario = request.form["numero_prontuario"]
        familiar = request.form["familiar"]
        motivo_prisao = request.form["motivo_prisao"]
        faccao = request.form["faccao"]
        cela_bloco = request.form["cela_bloco"]
        prontuario_medico = request.form["prontuario_medico"]

        # Tratamento da foto na edição (se enviar uma nova, muda; se não, mantém a atual)
        foto = request.files.get("foto")
        if foto and foto.filename != '':
            nome_arq = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arq))
            foto_url = f"/static/uploads/{nome_arq}"
            cursor.execute("""
                UPDATE pessoas SET nome=?, documento=?, numero_prontuario=?, foto_url=?, familiar=?, motivo_prisao=?, faccao=?, cela_bloco=?, prontuario_medico=?
                WHERE id=?
            """, (nome, documento, numero_prontuario, foto_url, familiar, motivo_prisao, faccao, cela_bloco, prontuario_medico, id))
        else:
            cursor.execute("""
                UPDATE pessoas SET nome=?, documento=?, numero_prontuario=?, familiar=?, motivo_prisao=?, faccao=?, cela_bloco=?, prontuario_medico=?
                WHERE id=?
            """, (nome, documento, numero_prontuario, familiar, motivo_prisao, faccao, cela_bloco, prontuario_medico, id))
        
        conn.commit()
        conn.close()
        return redirect("/painel")

    # Se for GET, apenas busca os dados atuais para exibir nos campos do formulário
    cursor.execute("SELECT * FROM pessoas WHERE id = ?", (id,))
    pessoa = cursor.fetchone()
    conn.close()
    
    if pessoa:
        return render_template("editar.html", pessoa=pessoa)
    return redirect("/painel")

@app.route("/excluir/<int:id>", methods=["POST"])
def excluir(id):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pessoas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/painel")

@app.route("/exportar")
def exportar():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM pessoas", conn)
    conn.close()
    caminho = os.path.join(os.path.dirname(__file__), "relatorio_detentos.xlsx")
    df.to_excel(caminho, index=False)
    return send_file(caminho, as_attachment=True)

@app.route("/importar", methods=["POST"])
def importar():
    arquivo = request.files.get("planilha")
    if arquivo and arquivo.filename.endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(arquivo, header=1)
            # Remove espaços em branco e deixa tudo em maiúsculo para bater com seu arquivo real
            df.columns = df.columns.str.strip().str.upper()
            df = df.fillna('')
            
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            for index, row in df.iterrows():
                # 🚀 MAPEAMENTO AJUSTADO PARA O SEU ARQUIVO REAL (CCSJP)
                nome = str(row.get('CUSTODIADO', row.get('NOME', 'Desconhecido')))
                if nome == '' or nome.startswith(',,,,'): 
                    continue # Ignora linhas vazias ou quebradas do Excel
                
                unidade = str(row.get('UNIDADE', row.get('DOCUMENTO', 'CCSJP')))
                prontuario = str(row.get('PRONTUÁRIO', row.get('NUMERO_PRONTUARIO', '')))
                observacoes = str(row.get('OBSERVAÇÕES', ''))
                regime = str(row.get('REGIME', ''))
                
                # Juntando regime e observações para não perder informação na importação
                motivo = f"Regime: {regime}" if regime else "Não informado"
                
                cursor.execute("""
                    INSERT INTO pessoas (nome, documento, numero_prontuario, foto_url, familiar, motivo_prisao, faccao, cela_bloco, prontuario_medico) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome, unidade, prontuario,
                    'https://cdn-icons-png.flaticon.com/512/149/149071.png', 
                    '', motivo, '', '', observacoes
                ))
            conn.commit()
            conn.close()
            print("🚀 Planilha mapeada e importada com sucesso!")
        except Exception as e:
            print(f"❌ ERRO AO IMPORTAR EXCEL: {e}")
    return redirect("/painel")

@app.route("/cadastrar", methods=["GET", "POST"])
def cadastrar():
    if request.method == "POST":
        foto = request.files.get("foto")
        foto_url = "https://cdn-icons-png.flaticon.com/512/149/149071.png"
        if foto and foto.filename != '':
            nome_arq = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arq))
            foto_url = f"/static/uploads/{nome_arq}"

        dados = (request.form["nome"], request.form["documento"], request.form["numero_prontuario"], foto_url, request.form["familiar"], request.form["motivo_prisao"], request.form["faccao"], request.form["cela_bloco"], request.form["prontuario_medico"])
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pessoas (nome, documento, numero_prontuario, foto_url, familiar, motivo_prisao, faccao, cela_bloco, prontuario_medico) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", dados)
        conn.commit()
        conn.close()
        return redirect("/painel")
    return render_template("cadastrar.html")

if __name__ == "__main__":
    app.run(debug=True, port=8080)