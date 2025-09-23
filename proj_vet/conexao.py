from flask import Flask, render_template, send_from_directory, send_file, jsonify, request, redirect, url_for
import os
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# ---------------- CONFIGURAÇÕES DE PASTA ---------------- #

# Caminho para a pasta onde os PDFs estão armazenados
PASTA_PDFS = os.path.join(os.path.dirname(__file__), 'pdfs')

# Caminho para a pasta onde as miniaturas (thumbs) serão salvas
PASTA_THUMBS = os.path.join(os.path.dirname(__file__), 'static', 'thumbs')

# Caminho do Poppler (usado pelo pdf2image para converter PDFs em imagens)
POPPLER_PATH = os.getenv("POPPLER_PATH", "")

# Garante que a pasta de thumbs existe
os.makedirs(PASTA_THUMBS, exist_ok=True)

# ---------------- CONEXÃO COM POSTGRESQL ---------------- #

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Configuração da string de conexão com o banco PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:020504@localhost/SisMedVet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---------------- MODELOS DE BANCO ---------------- #

#----Modelo de Classe Usuario------#
class Usuario(db.Model):
    __tablename__ = 'usuarios'  # ← Nome da tabela no banco, agora em minúsculo para compatibilidade com PostgreSQL

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)

# ---- MODELO DE PALESTRAS ---- #
class Palestra(db.Model):
    __tablename__ = 'palestras'  # ← Nome da tabela no banco, em minúsculo

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.Text)

# ---- MODELO DE INSCRIÇÃO ( INTERMEDIÁRIO DE PALESTRAS ) ---- #
class Inscricao(db.Model):
    __tablename__ = 'inscricoes'  # ← Nome da tabela no banco, em minúsculo

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    palestra_id = db.Column(db.Integer, db.ForeignKey('palestras.id'), nullable=False)

# ---------------- ROTAS PRINCIPAIS ---------------- #

@app.route('/')
def index():
    # Página inicial redireciona para tela de login
    return render_template('cadastro.html')

@app.route('/central')
def central():
    # Tela principal após login
    return render_template('central_funcionalidades.html')

#LOGIN
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # Recebe dados do formulário
        email = request.form.get('email')
        senha = request.form.get('senha')

        # Busca usuário no banco
        usuario = Usuario.query.filter_by(email=email).first()

        # Checagem com bcrypt usando a hash
        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            # Login bem-sucedido
            return render_template('central_funcionalidades.html', nome=usuario.nome)
        else:
            # Retorna a tela com mensagem de erro
            return render_template('cadastro.html', mensagem="Credenciais inválidas.")
            #Deu certo vamos para tela de login com a mensagem
    return render_template('cadastro.html')

# CADASTRO DE CONTA
@app.route('/criar_conta', methods=['GET', 'POST'])
def criar_conta():
    if request.method == 'POST':
        # Recebe dados do formulário
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')

        # Verifica se o e-mail já existe
        if Usuario.query.filter_by(email=email).first():
            # Retorna a tela com mensagem de erro
            return render_template('criar_conta.html', mensagem="E-mail já cadastrado.")

        # Criptografa a senha
        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')

        # Cria e salva o usuário
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash)
        db.session.add(novo_usuario)
        db.session.commit()

        # Retorna a tela de login com mensagem de sucesso
        return render_template('cadastro.html', mensagem="Cadastro feito com sucesso! Logue na aplicação para validar")
    return render_template('criar_conta.html')

#BULÁRIO
@app.route('/bulario')
def bulario():
    return render_template('bulario.html')

#CALCULADORA DE DOSE
@app.route('/calculadora')
def calculadora():
    return render_template('calculadora.html')

#COMPONENTES DA LIGA
@app.route('/componentes')
def componentes():
    return render_template('componentes_liga.html')

#DOCUMENTOS PDF
@app.route('/documentos')
def documentos():
    # Busca por nome de arquivo
    busca = request.args.get('busca', '').lower()
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]

    if busca:
        arquivos = [f for f in arquivos if busca in f.lower()]

    return render_template('documentos.html', arquivos=arquivos)

#ABRIR PDF
@app.route('/abrir_pdf/<nome>')
def abrir_pdf(nome):
    return send_from_directory(PASTA_PDFS, nome)

#GERAR THUMBNAIL DO PDF
@app.route('/thumb/<nome>')
def thumb(nome):
    caminho_pdf = os.path.join(PASTA_PDFS, nome)
    caminho_thumb = os.path.join(PASTA_THUMBS, f"{nome}.png")

    # Gera a miniatura se ainda não existir
    if not os.path.exists(caminho_thumb):
        paginas = convert_from_path(
            caminho_pdf,
            dpi=100,
            first_page=1,
            last_page=1,
            poppler_path=POPPLER_PATH if POPPLER_PATH else None
        )
        paginas[0].save(caminho_thumb, 'PNG')

    return send_file(caminho_thumb, mimetype='image/png')

# ---------------- CALENDÁRIO ---------------- #

# ROTA CALENDARIO HTML
@app.route('/calendario')
def calendario():
    return render_template('calendario.html')

# ---- API: LISTAR EVENTOS POR MÊS ---- #
@app.route('/api/eventos', methods=['GET'])
def listar_eventos():
    # Recebe ano e mês da URL
    year = request.args.get('year')
    month = request.args.get('month')

    # Filtra eventos por mês/ano
    if year and month:
        eventos = Palestra.query.filter(
            db.extract('year', Palestra.date) == int(year),
            db.extract('month', Palestra.date) == int(month)
        ).all()
    else:
        eventos = Palestra.query.all()

    # Formata resposta JSON
    resultado = [
        {
            "id": e.id,
            "title": e.title,
            "date": e.date.strftime('%Y-%m-%d'),
            "descricao": e.descricao
        }
        for e in eventos
    ]
    return jsonify(resultado)

# ---- API: INSCRIÇÃO EM EVENTO ---- #
@app.route('/api/eventos/<int:evento_id>/inscrever', methods=['POST'])
def inscrever_evento(evento_id):
    # Busca evento pelo ID
    evento = Palestra.query.get(evento_id)
    if not evento:
        return jsonify({"status": "erro", "mensagem": "Evento não encontrado."}), 404

    # Recebe dados do formulário ou JSON
    nome = request.form.get('nome') or (request.json.get('nome') if request.is_json else None)
    email = request.form.get('email') or (request.json.get('email') if request.is_json else None)

    # Validação básica
    if not nome or not email:
        return jsonify({"status": "erro", "mensagem": "Nome e e-mail são obrigatórios."}), 400

    # Cria e salva inscrição
    nova_inscricao = Inscricao(nome=nome, email=email, palestra_id=evento_id)
    db.session.add(nova_inscricao)
    db.session.commit()

    return jsonify({"status": "ok", "mensagem": f"Inscrição confirmada em: {evento.title}!"})

# ---------------- MAIN ---------------- #

# Inicia o servidor Flask em modo debug
if __name__ == '__main__':
    app.run(debug=True)
