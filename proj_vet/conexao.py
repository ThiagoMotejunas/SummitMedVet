
from flask import Flask, render_template, send_from_directory, send_file, jsonify, request, redirect, url_for
import os
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Caminho para a pasta onde os PDFs estão armazenados
PASTA_PDFS = os.path.join(os.path.dirname(__file__), 'pdfs')

# Caminho para a pasta onde as miniaturas (thumbs) serão salvas
PASTA_THUMBS = os.path.join(os.path.dirname(__file__), 'static', 'thumbs')

# Caminho do Poppler (usado pelo pdf2image para converter PDFs em imagens)
POPPLER_PATH = os.getenv("POPPLER_PATH", "")

# Garante que a pasta de thumbs existe
os.makedirs(PASTA_THUMBS, exist_ok=True)

# Configuração da string de conexão com o banco PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:020504@localhost/SisMedVet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#----Modelo de Classe Usuario------#

class Usuario(db.Model):
    __tablename__ = 'usuarios'  # ← Nome da tabela no banco, agora em minúsculo para compatibilidade com PostgreSQL

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    cargo = db.Column(db.Integer, nullable=False, default=0)  # 0 = comum, 1 = admin


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

#Rota para iniciar o flask no cadastro
@app.route('/')
def index():
    # Página inicial redireciona para tela de login
    return render_template('cadastro.html')


#----------------- Func LOGIN/CADASTRO -------------#
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
           # Verifica o cargo do usuário
            if usuario.cargo == 1:
                # Redireciona administrador caso cargo seja admn(1)
                return render_template('admin.html', nome=usuario.nome)
            else:
                # Redireciona usuário comum caso não seja adm e funcione o login
                return render_template('central_funcionalidades.html', nome=usuario.nome)
        else:
            # Retorna a tela com mensagem de erro caso dê errado
            return render_template('cadastro.html', mensagem="Credenciais inválidas.")
            #Renderiza a mesma tela de cadastro novamente
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
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash, cargo=0)
        db.session.add(novo_usuario)
        print(f"Registrando usuário: {nome}, {email}, cargo=0")

        db.session.commit()

        # Retorna a tela de login com mensagem de sucesso
        return render_template('cadastro.html', mensagem="Cadastro feito com sucesso! Logue na aplicação para validar")
    return render_template('criar_conta.html')



# ---------------- ROTA ADMIN PALESTRAS ---------------- #

# Listar palestras
@app.route('/admin/palestras', methods=['GET'])
def admin_palestras_listar():
    mensagem = request.args.get('mensagem')
    eventos = Palestra.query.order_by(Palestra.date.asc()).all()
    return render_template('admin_palestras.html', eventos=eventos, mensagem=mensagem)


# Criar nova palestra
@app.route('/admin/palestras', methods=['POST'])
def admin_palestras():
    titulo = request.form.get('titulo')
    data = request.form.get('data')
    descricao = request.form.get('descricao')

    nova_palestra = Palestra(title=titulo, date=data, descricao=descricao)
    db.session.add(nova_palestra)
    db.session.commit()

    return redirect(url_for('admin_palestras_listar', mensagem="Palestra adicionada com sucesso!"))


# Editar palestra
@app.route('/admin/palestras/editar/<int:evento_id>', methods=['GET', 'POST'])
def admin_palestras_editar(evento_id):
    evento = Palestra.query.get(evento_id)
    if not evento:
        return redirect(url_for('admin_palestras_listar', mensagem="Palestra não encontrada."))

    if request.method == 'POST':
        evento.title = request.form.get('titulo')
        evento.date = request.form.get('data')
        evento.descricao = request.form.get('descricao')
        db.session.commit()
        return redirect(url_for('admin_palestras_listar', mensagem="Palestra editada com sucesso!"))

    return render_template('admin_palestras.html', evento=evento)


# Excluir palestra
@app.route('/admin/palestras/excluir/<int:evento_id>', methods=['POST'])
def admin_palestras_excluir(evento_id):
    evento = Palestra.query.get(evento_id)
    if evento:
        db.session.delete(evento)
        db.session.commit()
        return redirect(url_for('admin_palestras_listar', mensagem="Palestra excluída com sucesso!"))
    return redirect(url_for('admin_palestras_listar', mensagem="Palestra não encontrada."))


# ---------------- ADMIN  BULÁRIO (MEDICAMENTOS) ---------------- #
@app.route('/admin/medicamentos', methods=['GET'])
def admin_medicamentos_listar():
    mensagem = request.args.get('mensagem')
    return render_template('admin_medicamentos.html', medicamentos=medicamentos, mensagem=mensagem)

@app.route('/admin/medicamentos', methods=['POST'])
def admin_medicamentos_criar():
    nome_comercial = request.form.get('nome_comercial')
    nome_cientifico = request.form.get('nome_cientifico')
    dosagem_geral = request.form.get('dosagem_geral')
    dosagem_doenca = request.form.get('dosagem_doenca')
    doencas_relacionadas = request.form.get('doencas_relacionadas')

    novo_id = len(medicamentos) + 1
    medicamentos.append({
        "id": novo_id,
        "nome_comercial": nome_comercial,
        "nome_cientifico": nome_cientifico,
        "dosagem_geral": dosagem_geral,
        "dosagem_doenca": dosagem_doenca,
        "doencas_relacionadas": doencas_relacionadas
    })

    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento cadastrado com sucesso!"))

@app.route('/admin/medicamentos/editar/<int:med_id>', methods=['POST'])
def admin_medicamentos_editar(med_id):
    med = next((m for m in medicamentos if m["id"] == med_id), None)
    if not med:
        return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento não encontrado."))

    med["nome_comercial"] = request.form.get('nome_comercial')
    med["nome_cientifico"] = request.form.get('nome_cientifico')
    med["dosagem_geral"] = request.form.get('dosagem_geral')
    med["dosagem_doenca"] = request.form.get('dosagem_doenca')
    med["doencas_relacionadas"] = request.form.get('doencas_relacionadas')

    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento editado com sucesso!"))

@app.route('/admin/medicamentos/excluir/<int:med_id>', methods=['POST'])
def admin_medicamentos_excluir(med_id):
    global medicamentos
    medicamentos = [m for m in medicamentos if m["id"] != med_id]
    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento excluído com sucesso!"))

# ---------------- ADMIN  DOCUMENTOS ---------------- #

@app.route('/admin/documentos', methods=['GET'])
def admin_documentos_listar():
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]
    mensagem = request.args.get('mensagem')
    return render_template('admin_documentos.html', arquivos=arquivos, mensagem=mensagem)

@app.route('/admin/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return redirect(url_for('admin_documentos_listar', mensagem="Nenhum arquivo enviado."))
    file = request.files['pdf']
    if file.filename == '':
        return redirect(url_for('admin_documentos_listar', mensagem=" Nome de arquivo inválido."))

    filename = secure_filename(file.filename)
    file.save(os.path.join(PASTA_PDFS, filename))

    return redirect(url_for('admin_documentos_listar', mensagem="PDF enviado com sucesso!"))

@app.route('/admin/documentos/excluir/<nome>', methods=['POST'])
def admin_documentos_excluir(nome):
    caminho = os.path.join(PASTA_PDFS, nome)
    if os.path.exists(caminho):
        os.remove(caminho)
        return redirect(url_for('admin_documentos_listar', mensagem="Documento excluído com sucesso!"))
    return redirect(url_for('admin_documentos_listar', mensagem=" Documento não encontrado."))


# ---------------- OUTRAS TELAS ---------------- #

@app.route('/calculadora')
def calculadora():
    return render_template('calculadora.html')

#COMPONENTES DA LIGA
@app.route('/componentes')
def componentes():
    return render_template('componentes_liga.html')


# ---------------- BULÁRIO ---------------- #
medicamentos = []
@app.route('/bulario')
def bulario():
    busca = request.args.get('busca', '').lower()
    filtro = request.args.get('filtro', 'comercial')  # padrão: nome comercial

    resultados = medicamentos

    if busca:
        if filtro == 'doenca':
            resultados = [m for m in medicamentos if busca in m.get("doencas_relacionadas", "").lower()]
        elif filtro == 'cientifico':
            resultados = [m for m in medicamentos if busca in m.get("nome_cientifico", "").lower()]
        else:  # comercial
            resultados = [m for m in medicamentos if busca in m.get("nome_comercial", "").lower()]

    return render_template('bulario.html', medicamentos=resultados, busca=busca, filtro=filtro)

# ---------------- DOCUMENTOS (PDF) ---------------- #

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

# ---- API: LISTAR EVENTOS POR MÊS ---- #
@app.route('/api/eventos', methods=['GET'])
def listar_eventos():
    # Recebe ano e mês da URL
    year = request.args.get('year')
    month = request.args.get('month')

    # Busca todos os eventos do banco
    eventos_db = Palestra.query.all()

    # Converte para lista de dicionários
    eventos = [
        {
            "id": e.id,
            "title": e.title,
            "date": e.date.strftime('%Y-%m-%d'),
            "descricao": e.descricao
        }
        for e in eventos_db
    ]

    # Filtra por ano e mês se fornecidos
    if year and month:
        filtrados = [e for e in eventos if e["date"].startswith(f"{year}-{month.zfill(2)}")]
        return jsonify(filtrados)

    return jsonify(eventos)


# ---- API: INSCRIÇÃO EM EVENTO ---- #

@app.route('/api/eventos/<int:evento_id>/inscrever', methods=['POST'])
def inscrever_evento(evento_id):
    # Busca evento no banco
    evento = Palestra.query.get(evento_id)
    if not evento:
        return jsonify({"status": "erro", "mensagem": "Evento não encontrado."}), 404
    
    # Recebe dados do formulário ou JSON
    nome = request.form.get('nome') or (request.json.get('nome') if request.is_json else None)
    email = request.form.get('email') or (request.json.get('email') if request.is_json else None)

    # Validação básica
    if not nome or not email:
        return jsonify({"status": "erro", "mensagem": "Nome e e-mail são obrigatórios."}), 400

    # Cria e salva nova inscrição
    inscricao_existente = Inscricao.query.filter_by(email=email, palestra_id=evento_id).first()
    if inscricao_existente:
        return jsonify({"status": "erro", "mensagem": "Você já está inscrito."}), 409

    nova_inscricao = Inscricao(nome=nome, email=email, palestra_id=evento_id)
    db.session.add(nova_inscricao)
    db.session.commit()

    return jsonify({"status": "ok", "mensagem": f"Inscrição confirmada em: {evento.title}!"})

# ---------------- MAIN ---------------- #

# Inicia o servidor Flask em modo debug
if __name__ == '__main__':
    app.run(debug=True)
