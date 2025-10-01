from flask import Flask, render_template, send_from_directory, send_file, jsonify, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "minha_chave_super_secreta_123"

# Pastas do projeto
PASTA_PDFS = os.path.join(os.path.dirname(__file__), 'pdfs')
PASTA_THUMBS = os.path.join(os.path.dirname(__file__), 'static', 'thumbs')

# Caminho do Poppler (pega da variável de ambiente ou deixa vazio)
POPPLER_PATH = os.getenv("POPPLER_PATH", "")

# Garante que a pasta de thumbs existe
os.makedirs(PASTA_THUMBS, exist_ok=True)

# ---------------- CONFIGURAÇÃO BANCO ---------------- #
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Edu1Sal2@localhost:5432/SisMedVet"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- MODELOS ---------------- #
class Bulario(db.Model):
    __tablename__ = "bulario"
    id = db.Column(db.Integer, primary_key=True)
    nome_comercial = db.Column(db.String(255))
    nome_cientifico = db.Column(db.String(255))
    dosagem_geral = db.Column(db.Float, nullable=True)
    dosagem_doenca = db.Column(db.Float, nullable=True)
    doencas_relacionadas = db.Column(db.String(500), nullable=True)


# ---------------- ROTAS PRINCIPAIS ---------------- #

@app.route('/central')
def central():
    return render_template('central_funcionalidades.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        if email == "admin" and senha == "123admin":
            return redirect(url_for('admin'))

        return f"Usuário {email} cadastrado com sucesso!"
    
    return render_template('cadastro.html')


# ---------------- ROTAS DO ADMIN ---------------- #

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ---------------- ADMIN  PALESTRAS ---------------- #
eventos = [
    {"id": 1, "title": "Palestra sobre Nutrição Animal", "date": "2025-09-15", "descricao": "Conceitos e atualizações"},
    {"id": 2, "title": "Cuidados com Animais Silvestres", "date": "2025-09-20", "descricao": "Protocolos e legislação"},
    {"id": 3, "title": "Anestesia em Pequenos Animais", "date": "2025-10-05", "descricao": "Boas práticas e segurança"}
]

@app.route('/admin/palestras', methods=['GET'])
def admin_palestras_listar():
    mensagem = request.args.get('mensagem')
    return render_template('admin_palestras.html', eventos=eventos, mensagem=mensagem)

@app.route('/admin/palestras', methods=['POST'])
def admin_palestras():
    titulo = request.form.get('titulo')
    data = request.form.get('data')
    descricao = request.form.get('descricao')

    novo_id = max([e["id"] for e in eventos]) + 1 if eventos else 1
    eventos.append({"id": novo_id, "title": titulo, "date": data, "descricao": descricao})

    return redirect(url_for('admin_palestras_listar', mensagem="Palestra adicionada com sucesso!"))

@app.route('/admin/palestras/editar/<int:evento_id>', methods=['GET', 'POST'])
def admin_palestras_editar(evento_id):
    evento = next((e for e in eventos if e["id"] == evento_id), None)
    if not evento:
        return redirect(url_for('admin_palestras_listar', mensagem=" Palestra não encontrada."))

    if request.method == 'POST':
        evento["title"] = request.form.get('titulo')
        evento["date"] = request.form.get('data')
        evento["descricao"] = request.form.get('descricao')
        return redirect(url_for('admin_palestras_listar', mensagem="Palestra editada com sucesso!"))

    return render_template('admin_palestras.html', evento=evento)

@app.route('/admin/palestras/excluir/<int:evento_id>', methods=['POST'])
def admin_palestras_excluir(evento_id):
    global eventos
    eventos = [e for e in eventos if e["id"] != evento_id]
    return redirect(url_for('admin_palestras_listar', mensagem="Palestra excluída com sucesso!"))


# ---------------- ADMIN  BULÁRIO (MEDICAMENTOS) ---------------- #
@app.route('/admin/medicamentos', methods=['GET'])
def admin_medicamentos_listar():
    mensagem = request.args.get('mensagem')
    medicamentos = Bulario.query.all()
    return render_template('admin_medicamentos.html', medicamentos=medicamentos, mensagem=mensagem)

@app.route('/admin/medicamentos', methods=['POST'])
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

@app.route('/admin/medicamentos/editar/<int:med_id>', methods=['POST'])
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

@app.route('/admin/medicamentos/excluir/<int:med_id>', methods=['POST'])
def admin_medicamentos_excluir(med_id):
    med = Bulario.query.get(med_id)
    if med:
        db.session.delete(med)
        db.session.commit()
    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento excluído com sucesso!"))


# ---------------- ADMIN  DOCUMENTOS ---------------- #

@app.route('/admin/documentos', methods=['GET'])
def admin_documentos_listar():
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]
    tipo = request.args.get("tipo")
    mensagem = request.args.get('mensagem')
    return render_template('admin_documentos.html', arquivos=arquivos, mensagem=mensagem, tipo=tipo)

# Tipos permitidos
extensoes_permitidas = {"pdf"}

def extensoes(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensoes_permitidas

@app.route('/admin/upload_pdf', methods=['POST'])
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
def admin_documentos_excluir(nome):
    caminho = os.path.join(PASTA_PDFS, nome)
    if os.path.exists(caminho):
        os.remove(caminho)
        return redirect(url_for('admin_documentos_listar', mensagem="Documento excluído com sucesso!"))
    return redirect(url_for('admin_documentos_listar', mensagem=" Documento não encontrado."))


# ---------------- BULÁRIO ---------------- #
@app.route('/bulario')
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
def documentos():
    busca = request.args.get('busca', '').lower()
    arquivos = [f for f in os.listdir(PASTA_PDFS) if f.endswith('.pdf')]

    if busca:
        arquivos = [f for f in arquivos if busca in f.lower()]

    return render_template('documentos.html', arquivos=arquivos)

@app.route('/abrir_pdf/<nome>')
def abrir_pdf(nome):
    return send_from_directory(PASTA_PDFS, nome)

@app.route('/thumb/<nome>')
def thumb(nome):
    caminho_pdf = os.path.join(PASTA_PDFS, nome)
    caminho_thumb = os.path.join(PASTA_THUMBS, f"{nome}.png")

    if not os.path.exists(caminho_thumb):
        if POPPLER_PATH:
            paginas = convert_from_path(caminho_pdf, dpi=100, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
        else:
            paginas = convert_from_path(caminho_pdf, dpi=100, first_page=1, last_page=1)
        paginas[0].save(caminho_thumb, 'PNG')
        
    return send_file(caminho_thumb, mimetype='image/png')


# ---------------- CALENDÁRIO ---------------- #
@app.route('/calendario')
def calendario():
    return render_template('calendario.html')

@app.route('/api/eventos', methods=['GET'])
def listar_eventos():
    year = request.args.get('year')
    month = request.args.get('month')
    if year and month:
        filtrados = [e for e in eventos if e["date"].startswith(f"{year}-{month:0>2}")]
        return jsonify(filtrados)
    return jsonify(eventos)

@app.route('/api/eventos/<int:evento_id>/inscrever', methods=['POST'])
def inscrever_evento(evento_id):
    evento = next((e for e in eventos if e["id"] == evento_id), None)
    if not evento:
        return jsonify({"status": "erro", "mensagem": "Evento não encontrado."}), 404
    nome = request.form.get('nome') or (request.json.get('nome') if request.is_json else None)
    email = request.form.get('email') or (request.json.get('email') if request.is_json else None)
    return jsonify({"status": "ok", "mensagem": f"Inscrição confirmada em: {evento['title']}!"})


# ---------------- MAIN ---------------- #
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # cria tabelas se não existirem
    app.run(debug=True)
