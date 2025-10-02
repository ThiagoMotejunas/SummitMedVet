from flask import Flask, render_template, send_from_directory, send_file, jsonify, request, redirect, url_for, flash ,session
import os
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from functools import wraps

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Necessário para usar session
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Edu1Sal2@localhost/SisMedVet'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ---- Decorador para proteger rotas ---- #
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'usuario_logado' not in session:
            print("🚫 Sessão não encontrada. Redirecionando.")
            return redirect(url_for('cadastro'))
        return f(*args, **kwargs)
    return wrapper

#----Modelo de Classe Usuario------#
class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    cargo = db.Column(db.Integer, nullable=False, default=0)

# ---- MODELO DE PALESTRAS ---- #
class Palestra(db.Model):
    __tablename__ = 'palestras'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    date = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.Text)

# ---- MODELO DE INSCRIÇÃO ---- #
class Inscricao(db.Model):
    __tablename__ = 'inscricoes'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    palestra_id = db.Column(db.Integer, db.ForeignKey('palestras.id'), nullable=False)
    palestra = db.relationship('Palestra', backref='inscricoes')

# ---------------- MODELO BULARIO ---------------- #
class Bulario(db.Model):
    __tablename__ = "bulario"
    id = db.Column(db.Integer, primary_key=True)
    nome_comercial = db.Column(db.String(255))
    nome_cientifico = db.Column(db.String(255))
    dosagem_geral = db.Column(db.Float, nullable=True)
    dosagem_doenca = db.Column(db.Float, nullable=True)
    doencas_relacionadas = db.Column(db.String(500), nullable=True)


# ---------------- ROTAS PRINCIPAIS ---------------- #

@app.route('/')
def index():
    return render_template('cadastro.html')

@app.route('/central')
@login_required
def central():
    return render_template('central_funcionalidades.html')

#LOGIN
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and bcrypt.check_password_hash(usuario.senha, senha):
            session['usuario_logado'] = usuario.email
            session['nome'] = usuario.nome  # ← Adiciona nome à sessão
            session['email'] = usuario.email  # ← Adiciona email à sessão
            session['cargo'] = usuario.cargo

            if usuario.cargo == 1:
                return render_template('admin.html', nome=usuario.nome)
            else:
                return render_template('central_funcionalidades.html', nome=usuario.nome)
        else:
            return render_template('cadastro.html', mensagem="Credenciais inválidas.")
    return render_template('cadastro.html')

# CADASTRO DE CONTA
@app.route('/criar_conta', methods=['GET', 'POST'])
def criar_conta():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')

        if Usuario.query.filter_by(email=email).first():
            return render_template('criar_conta.html', mensagem="E-mail já cadastrado.")

        senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
        novo_usuario = Usuario(nome=nome, email=email, senha=senha_hash, cargo=0)
        db.session.add(novo_usuario)
        db.session.commit()

        return render_template('cadastro.html', mensagem="Cadastro feito com sucesso! Logue na aplicação para validar")
    return render_template('criar_conta.html')

#---------- ROTAS DE ADMINISTRADOR------------#

#Carrega página Admn

@app.route('/admin')
@login_required
def admin_central():
    return render_template('admin.html')

@app.route('/api/me')
@login_required
def api_me():
    return jsonify({
        "nome": session.get("nome"),
        "email": session.get("email")
        
    })



# ---------------- ROTA ADMIN | PALESTRAS ---------------- #

#Listar todas palestras
@app.route('/admin/palestras', methods=['GET'])
@login_required
def admin_palestras_listar():
    mensagem = request.args.get('mensagem')
    eventos = Palestra.query.order_by(Palestra.date.asc()).all()
    inscricoes = Inscricao.query.order_by(Inscricao.id.asc()).all()
    return render_template('admin_palestras.html', eventos=eventos, inscricoes=inscricoes, mensagem=mensagem)


#Criar Palestra
@app.route('/admin/palestras', methods=['POST'])
@login_required
def admin_palestras():
    titulo = request.form.get('titulo')
    data = request.form.get('data')
    descricao = request.form.get('descricao')

    nova_palestra = Palestra(title=titulo, date=data, descricao=descricao)
    db.session.add(nova_palestra)
    db.session.commit()

    return redirect(url_for('admin_palestras_listar', mensagem="Palestra adicionada com sucesso!"))

#Editar Palestra
@app.route('/admin/palestras/editar/<int:evento_id>', methods=['GET', 'POST'])
@login_required
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

#Excluir Palestra
@app.route('/admin/palestras/excluir/<int:evento_id>', methods=['POST'])
@login_required
def admin_palestras_excluir(evento_id):
    evento = Palestra.query.get(evento_id)
    if evento:
        db.session.delete(evento)
        db.session.commit()
        return redirect(url_for('admin_palestras_listar', mensagem="Palestra excluída com sucesso!"))
    return redirect(url_for('admin_palestras_listar', mensagem="Palestra não encontrada."))

#-----------------Rota de ADM para poder consultar pessoas inscritas em um evento------------------------#

@app.route('/api/eventos/<int:evento_id>/inscritos', methods=['GET'])
@login_required
def listar_inscritos_evento(evento_id):
    evento = Palestra.query.get(evento_id)
    if not evento:
        return jsonify({"status": "erro", "mensagem": "Evento não encontrado."}), 404

    inscritos = Inscricao.query.filter_by(palestra_id=evento_id).all()
    lista = [{"nome": i.nome, "email": i.email} for i in inscritos]

    return jsonify({
        "status": "ok",
        "evento": evento.title,
        "quantidade": len(lista),
        "inscritos": lista
    })

#Palestra cadastradas
@app.route('/admin/palestras_cadastradas')
@login_required
def palestras_cadastradas():
    palestras = Palestra.query.all()
    resultado = []

    for palestra in palestras:
        qtd = Inscricao.query.filter_by(palestra_id=palestra.id).count()
        resultado.append({
            "id": palestra.id,
            "title": palestra.title,
            "descricao": palestra.descricao,
            "data": palestra.date.strftime('%d/%m/%Y'),
            "qtd_inscritos": qtd
        })

    return render_template('admin_palestras.html', palestras=resultado)


# ---------------- ADMIN  BULÁRIO (MEDICAMENTOS) ---------------- #
#Listar Med
@app.route('/admin/medicamentos', methods=['GET'])
@login_required
def admin_medicamentos_listar():
    mensagem = request.args.get('mensagem')
    medicamentos = Bulario.query.all()
    return render_template('admin_medicamentos.html', medicamentos=medicamentos, mensagem=mensagem)

#Criar Medicamento
@app.route('/admin/medicamentos', methods=['POST'])
@login_required
def admin_medicamentos_criar():
    novo_med = Bulario(
        nome_comercial=request.form.get('nome_comercial'),
        nome_cientifico=request.form.get('nome_cientifico'),
        dosagem_geral=float(request.form.get('dosagem_geral')) if request.form.get('dosagem_geral') else None,
        dosagem_doenca=float(request.form.get('dosagem_doenca')) if request.form.get('dosagem_doenca') else None,
        doencas_relacionadas=request.form.get('doencas_relacionadas')
    )
    db.session.add(novo_med)
    db.session.commit()
    return redirect(url_for('admin_medicamentos_listar', mensagem="✅ Medicamento cadastrado com sucesso!"))

#Alterar Med
@app.route('/admin/medicamentos/editar/<int:med_id>', methods=['POST'])
@login_required
def admin_medicamentos_editar(med_id):
    med = Bulario.query.get(med_id)
    if med:
        med.nome_comercial = request.form.get('nome_comercial')
        med.nome_cientifico = request.form.get('nome_cientifico')
        med.dosagem_geral = float(request.form.get('dosagem_geral')) if request.form.get('dosagem_geral') else None
        med.dosagem_doenca = float(request.form.get('dosagem_doenca')) if request.form.get('dosagem_doenca') else None
        med.doencas_relacionadas = request.form.get('doencas_relacionadas')
        db.session.commit()
    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento editado com sucesso!"))

#Excluir Med
@app.route('/admin/medicamentos/excluir/<int:med_id>', methods=['POST'])
@login_required
def admin_medicamentos_excluir(med_id):
    med = Bulario.query.get(med_id)
    if med:
        db.session.delete(med)
        db.session.commit()
    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento excluído com sucesso!"))

# ---------------- ADMIN DOCUMENTOS ---------------- #
#Listar documentos
@app.route('/admin/documentos', methods=['GET'])
@login_required
def admin_documentos_listar():
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]
    tipo = request.args.get("tipo")
    mensagem = request.args.get('mensagem')
    return render_template('admin_documentos.html', arquivos=arquivos, mensagem=mensagem, tipo=tipo)

# Tipos permitidos de doc
extensoes_permitidas = {"pdf"}

def extensoes(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensoes_permitidas

@app.route('/admin/upload_pdf', methods=['POST'])
@login_required
def upload_pdf():
    if "pdf" not in request.files:
        flash("Nenhum arquivo enviado.")
        return redirect(request.referrer)

    file = request.files["pdf"]

    if file.filename == "":
        flash("Nenhum arquivo selecionado.")
        return redirect(request.referrer)

    if file and extensoes(file.filename):
        filepath = os.path.join(PASTA_PDFS, file.filename)
        file.save(filepath)
        flash("PDF salvo com sucesso!", "success")
        return redirect(url_for("admin_documentos_listar", mensagem="PDF salvo com sucesso!"))
    else:
        return redirect(url_for("admin_documentos_listar", mensagem="Erro ao salvar PDF", tipo="error"))

@app.route('/admin/documentos/excluir/<nome>', methods=['POST'])
@login_required
def admin_documentos_excluir(nome):
    caminho = os.path.join(PASTA_PDFS, nome)
    if os.path.exists(caminho):
        os.remove(caminho)
        return redirect(url_for('admin_documentos_listar', mensagem="Documento excluído com sucesso!"))
    return redirect(url_for('admin_documentos_listar', mensagem=" Documento não encontrado."))



# ---------------- OUTRAS TELAS ---------------- #
@app.route('/calculadora')
@login_required
def calculadora():
    return render_template('calculadora.html')

@app.route('/componentes')
@login_required
def componentes():
    return render_template('componentes_liga.html')

# ---------------- BULÁRIO ---------------- #

@app.route('/bulario')
@login_required
def bulario():
    busca = request.args.get('busca', '').lower()
    filtro = request.args.get('filtro', 'comercial')

    query = Bulario.query
    if busca:
        if filtro == 'doenca':
            query = query.filter(Bulario.doencas_relacionadas.ilike(f"%{busca}%"))
        elif filtro == 'cientifico':
            query = query.filter(Bulario.nome_cientifico.ilike(f"%{busca}%"))
        else:  # comercial
            query = query.filter(Bulario.nome_comercial.ilike(f"%{busca}%"))

    medicamentos = query.all()
    return render_template('bulario.html', medicamentos=medicamentos, busca=busca, filtro=filtro)

# ---------------- DOCUMENTOS (PDF) ---------------- #
@app.route('/documentos')
@login_required
def documentos():
    busca = request.args.get('busca', '').lower()
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]

    if busca:
        arquivos = [f for f in arquivos if busca in f.lower()]

    return render_template('documentos.html', arquivos=arquivos)

@app.route('/abrir_pdf/<nome>')
@login_required
def abrir_pdf(nome):
    return send_from_directory(PASTA_PDFS, nome)

@app.route('/thumb/<nome>')
@login_required
def thumb(nome):
    caminho_pdf = os.path.join(PASTA_PDFS, nome)
    caminho_thumb = os.path.join(PASTA_THUMBS, f"{nome}.png")

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

#Carrega calendario
@app.route('/calendario')
@login_required
def calendario():
    # Exemplo: pegar usuário logado da sessão 
    user = {
        "nome": session.get("nome"),
        "email": session.get("email")
    }
    return render_template('calendario.html', user=user)

#Lista todas palestras
@app.route('/api/eventos', methods=['GET'])
@login_required
def listar_eventos():
    year = request.args.get('year')
    month = request.args.get('month')
    eventos_db = Palestra.query.all()

    eventos = [
        {
            "id": e.id,
            "title": e.title,
            "date": e.date.strftime('%Y-%m-%d'),
            "descricao": e.descricao
        }
        for e in eventos_db
    ]

    if year and month:
        filtrados = [e for e in eventos if e["date"].startswith(f"{year}-{month.zfill(2)}")]
        return jsonify(filtrados)

    return jsonify(eventos)

# ---- API: INSCRIÇÃO EM EVENTO ---- #

#Se inscreve em um evento, preenchendo manualmente e-mail e user( aqui daria para puxar do "usuario.e-mail" que mantem na session )
@app.route('/api/eventos/<int:evento_id>/inscrever', methods=['POST'])
@login_required
def inscrever_evento(evento_id):
    evento = Palestra.query.get(evento_id)
    if not evento:                                                                    # Confere se a palestra existe
        return jsonify({"status": "erro", "mensagem": "Evento não encontrado."}), 404 # Se não existe retorna

    nome = request.form.get('nome') or (request.json.get('nome') if request.is_json else None) # Puxa nome com base no que foi preenchido
    email = request.form.get('email') or (request.json.get('email') if request.is_json else None) # Puxa e-mail com base no que for preenchido

    if not nome or not email:                                                                  #Se não preencherem
        return jsonify({"status": "erro", "mensagem": "Nome e e-mail são obrigatórios."}), 400 #Erro pois esta vazio

    inscricao_existente = Inscricao.query.filter_by(email=email, palestra_id=evento_id).first() # Caso já exista uma inscricao no DB igual a esta
    if inscricao_existente:                                                                         
        return jsonify({"status": "erro", "mensagem": "Você já está inscrito."}), 409          # Retorna erro

    nova_inscricao = Inscricao(nome=nome, email=email, palestra_id=evento_id)
    db.session.add(nova_inscricao)
    db.session.commit()

    return jsonify({"status": "ok", "mensagem": f"Inscrição confirmada em: {evento.title}!"}) # Caso não commitamos no db a att e confirmamos ao cliente

# ---------------Rota para usuario comum consultar em quais eventos ele esta inscrito ----------------#
@app.route('/api/usuario/<string:email>/inscricoes', methods=['GET'])
@login_required
def eventos_do_usuario(email):
    inscricoes = Inscricao.query.filter_by(email=email.strip().lower()).all()
    eventos = [{"evento_id": i.palestra_id, "nome_evento": i.palestra.title} for i in inscricoes]
    return jsonify({
        "status": "ok",
        "email": email,
        "quantidade": len(eventos),
        "eventos": eventos
    })

#----------Rota que define qual consulta executar na tela do calendario-------#

@app.route('/api/minhas_inscricoes', methods=['GET'])
@login_required
def minhas_inscricoes():
    email = session.get("email")
    cargo = session.get("cargo")  # 0 = comum, 1 = admin

    if cargo == 1:
        # Admin: retorna todos os eventos com lista de inscritos
        eventos = Palestra.query.all()
        resultado = []
        for evento in eventos:
            inscritos = Inscricao.query.filter_by(palestra_id=evento.id).all()
            resultado.append({
                "id": evento.id,
                "title": evento.title,
                "date": evento.date.strftime('%Y-%m-%d'),
                "descricao": evento.descricao,
                "inscritos": [{"nome": i.nome, "email": i.email} for i in inscritos],
                "qtd_inscritos": len(inscritos)
            })
        return jsonify(resultado)

    else:
        # Usuário comum: retorna apenas eventos em que está inscrito
        inscricoes = Inscricao.query.filter_by(email=email).all()
        resultado = []
        for i in inscricoes:
            evento = Palestra.query.get(i.palestra_id)
            resultado.append({
                "id": evento.id,
                "title": evento.title,
                "date": evento.date.strftime('%Y-%m-%d'),
                "descricao": evento.descricao
            })
        return jsonify(resultado)


#----------Rota que  vai contar carneirinhos(inscricoes) por palestra-------#
@app.route('/api/eventos/<int:evento_id>/quantidade_inscritos', methods=['GET'])
@login_required
def contar_inscritos(evento_id):
    evento = Palestra.query.get(evento_id)
    if not evento:
        return jsonify({"status": "erro", "mensagem": "Evento não encontrado."}), 404

    quantidade = Inscricao.query.filter_by(palestra_id=evento_id).count()

    return jsonify({
        "status": "ok",
        "evento": evento.title,
        "quantidade_inscritos": quantidade
    })

# ---------------- MAIN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)


