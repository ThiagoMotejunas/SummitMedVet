from flask import Flask, render_template, send_from_directory, send_file, jsonify, request, redirect, url_for
import os
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Pastas do projeto
PASTA_PDFS = os.path.join(os.path.dirname(__file__), 'pdfs')
PASTA_THUMBS = os.path.join(os.path.dirname(__file__), 'static', 'thumbs')

# Caminho do Poppler (pega da variável de ambiente ou deixa vazio)
POPPLER_PATH = os.getenv("POPPLER_PATH", "")

# Garante que a pasta de thumbs existe
os.makedirs(PASTA_THUMBS, exist_ok=True)

# ---------------- ROTAS PRINCIPAIS ---------------- #

@app.route('/')
def index():
    return render_template('cadastro.html')

@app.route('/central')
def central():
    return render_template('central_funcionalidades.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        # Se for admin, redireciona para painel de administração
        if email == "admin" and senha == "123admin":
            return redirect(url_for('admin'))

        # Caso contrário, fluxo normal de cadastro
        return render_template('central_funcionalidades.html')
    
    return render_template('cadastro.html')


# ---------------- ROTAS DO ADMIN ---------------- #

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ---------------- ADMIN  PALESTRAS ---------------- #

@app.route('/admin/palestras', methods=['GET'])
def admin_palestras_listar():
    mensagem = request.args.get('mensagem')

    # Enriquecer inscrições com título da palestra
    inscricoes_enriquecidas = []
    for ins in inscricoes:
        evento = next((e for e in eventos if e["id"] == ins["palestra_id"]), None)
        inscricoes_enriquecidas.append({
            **ins,
            "palestra": {"title": evento["title"]} if evento else None
        })

    return render_template(
        'admin_palestras.html',
        eventos=eventos,
        inscricoes=inscricoes_enriquecidas,
        mensagem=mensagem
    )

@app.route('/admin/palestras', methods=['POST'])
def admin_palestras():
    titulo = request.form.get('titulo')
    data = request.form.get('data')
    descricao = request.form.get('descricao')

    novo_id = max([e["id"] for e in eventos]) + 1 if eventos else 1
    eventos.append({"id": novo_id, "title": titulo, "date": data, "descricao": descricao})

    # redireciona para o GET, passando mensagem via querystring
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

    # GET → renderiza tela de edição
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

@app.route('/criar_conta')
def criar_conta():
    return render_template('criar_conta.html')

@app.route('/calculadora')
def calculadora():
    return render_template('calculadora.html')

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
            paginas = convert_from_path(
                caminho_pdf,
                dpi=100,
                first_page=1,
                last_page=1,
                poppler_path=POPPLER_PATH
            )
        else:
            paginas = convert_from_path(
                caminho_pdf,
                dpi=100,
                first_page=1,
                last_page=1
            )
        paginas[0].save(caminho_thumb, 'PNG')
        
    return send_file(caminho_thumb, mimetype='image/png')

# ---------------- CALENDÁRIO ---------------- #

eventos = [
    {"id": 1, "title": "Palestra sobre Nutrição Animal", "date": "2025-09-15", "descricao": "Conceitos e atualizações"},
    {"id": 2, "title": "Cuidados com Animais Silvestres", "date": "2025-09-20", "descricao": "Protocolos e legislação"},
    {"id": 3, "title": "Anestesia em Pequenos Animais", "date": "2025-10-05", "descricao": "Boas práticas e segurança"}
]

inscricoes = [
    {"id": 1, "nome": "Ana Souza", "email": "ana@email.com", "palestra_id": 1}
]

# Usuário simulado (pra preencher automaticamente no form)
usuario_fake = {"nome": "Usuário Teste", "email": "teste@email.com"}


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

    data = request.get_json() or {}
    nome = data.get("nome")
    email = data.get("email")

    if not nome or not email:
        return jsonify({"status": "erro", "mensagem": "Nome e e-mail são obrigatórios."}), 400

    # Verifica duplicidade
    existente = next((i for i in inscricoes if i["email"] == email and i["palestra_id"] == evento_id), None)
    if existente:
        return jsonify({"status": "erro", "mensagem": "Você já está inscrito neste evento."}), 409

    novo_id = len(inscricoes) + 1
    inscricoes.append({
        "id": novo_id,
        "nome": nome,
        "email": email,
        "palestra_id": evento_id
    })

    return jsonify({"status": "ok", "mensagem": f"Inscrição confirmada em: {evento['title']}!"})


@app.route('/api/eventos/<int:evento_id>/quantidade_inscritos', methods=['GET'])
def quantidade_inscritos(evento_id):
    qtd = len([i for i in inscricoes if i["palestra_id"] == evento_id])
    return jsonify({"quantidade_inscritos": qtd})

@app.route('/api/inscricoes', methods=['GET'])
def api_inscricoes():
    # Enriquecer com título da palestra
    resultado = []
    for ins in inscricoes:
        evento = next((e for e in eventos if e["id"] == ins["palestra_id"]), None)
        resultado.append({
            "id": ins["id"],
            "nome": ins["nome"],
            "email": ins["email"],
            "palestra_id": ins["palestra_id"],
            "palestra_title": evento["title"] if evento else '---'
        })
    return jsonify(resultado)


@app.route('/api/minhas_inscricoes', methods=['GET'])
def minhas_inscricoes():
    # Aqui estou filtrando pelo email do usuario_fake
    email = usuario_fake["email"]
    minhas = [i for i in inscricoes if i["email"] == email]

    # Enriquecer com dados da palestra
    resultado = []
    for ins in minhas:
        evento = next((e for e in eventos if e["id"] == ins["palestra_id"]), None)
        if evento:
            resultado.append({
                "title": evento["title"],
                "date": evento["date"],
                "descricao": evento.get("descricao", "")
            })
    return jsonify(resultado)


@app.route('/api/me', methods=['GET'])
def api_me():
    return jsonify(usuario_fake)


# ---------------- MAIN ---------------- #

if __name__ == '__main__':
    app.run(debug=True)
