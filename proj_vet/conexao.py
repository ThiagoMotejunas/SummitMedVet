from flask import Flask, render_template, send_from_directory, send_file, jsonify, request, redirect, url_for, flash
import psycopg2
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

# ---------------- ROTAS PRINCIPAIS ---------------- #

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
        return f"Usuário {email} cadastrado com sucesso!"
    
    return render_template('cadastro.html')


# ---------------- ROTAS DO ADMIN ---------------- #

@app.route('/admin')
def admin():
    return render_template('admin.html')

# ---------------- ADMIN  PALESTRAS ---------------- #

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

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas FROM bulario")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    medicamentos = [
        {
            "id": r[0],
            "nome_comercial": r[1],
            "nome_cientifico": r[2],
            "dosagem_geral": r[3],
            "dosagem_doenca": r[4],
            "doencas_relacionadas": r[5]
        } for r in rows
    ]

    return render_template('admin_medicamentos.html', medicamentos=medicamentos, mensagem=mensagem)


@app.route('/admin/medicamentos', methods=['POST'])
def admin_medicamentos_criar():
    nome_comercial = request.form.get('nome_comercial')
    nome_cientifico = request.form.get('nome_cientifico')
    dosagem_geral = request.form.get('dosagem_geral')
    dosagem_doenca = request.form.get('dosagem_doenca')
    doencas_relacionadas = request.form.get('doencas_relacionadas')

    dosagem_geral = float(dosagem_geral) if dosagem_geral else None
    dosagem_doenca = float(dosagem_doenca) if dosagem_doenca else None

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bulario (nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas)
        VALUES (%s, %s, %s, %s, %s)
    """, (nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin_medicamentos_listar', mensagem="✅ Medicamento cadastrado com sucesso!"))


@app.route('/admin/medicamentos/editar/<int:med_id>', methods=['POST'])
def admin_medicamentos_editar(med_id):
    nome_comercial = request.form.get('nome_comercial')
    nome_cientifico = request.form.get('nome_cientifico')
    dosagem_geral = request.form.get('dosagem_geral')
    dosagem_doenca = request.form.get('dosagem_doenca')
    doencas_relacionadas = request.form.get('doencas_relacionadas')

    # Converte valores numéricos corretamente
    dosagem_geral = float(dosagem_geral) if dosagem_geral else None
    dosagem_doenca = float(dosagem_doenca) if dosagem_doenca else None

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE bulario
        SET nome_comercial = %s,
            nome_cientifico = %s,
            dosagem_geral = %s,
            dosagem_doenca = %s,
            doencas_relacionadas = %s
        WHERE id = %s
    """, (nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas, med_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('admin_medicamentos_listar', mensagem="Medicamento editado com sucesso!"))

@app.route('/admin/medicamentos/excluir/<int:med_id>', methods=['POST'])
def admin_medicamentos_excluir(med_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM bulario WHERE id = %s", (med_id,))
    conn.commit()

    cur.close()
    conn.close()

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

# valida se o formato do arquivo para upload é .pdf
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

@app.route('/bulario')
def bulario():
    busca = request.args.get('busca', '').lower()
    filtro = request.args.get('filtro', 'comercial')

    conn = get_db_connection()
    cur = conn.cursor()

    if busca:
        if filtro == 'doenca':
            cur.execute("""
                SELECT id, nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas
                FROM bulario
                WHERE LOWER(COALESCE(doencas_relacionadas, '')) LIKE %s
            """, (f"%{busca}%",))
        elif filtro == 'cientifico':
            cur.execute("""
                SELECT id, nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas
                FROM bulario
                WHERE LOWER(COALESCE(nome_cientifico, '')) LIKE %s
            """, (f"%{busca}%",))
        else:  # comercial (default)
            cur.execute("""
                SELECT id, nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas
                FROM bulario
                WHERE LOWER(COALESCE(nome_comercial, '')) LIKE %s
            """, (f"%{busca}%",))
    else:
        cur.execute("""
            SELECT id, nome_comercial, nome_cientifico, dosagem_geral, dosagem_doenca, doencas_relacionadas
            FROM bulario
        """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    medicamentos = [
        {
            "id": r[0],
            "nome_comercial": r[1],
            "nome_cientifico": r[2],
            "dosagem_geral": r[3],
            "dosagem_doenca": r[4],
            "doencas_relacionadas": r[5]
        } for r in rows
    ]

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
    nome = request.form.get('nome') or request.json.get('nome') if request.is_json else None
    email = request.form.get('email') or request.json.get('email') if request.is_json else None
    return jsonify({"status": "ok", "mensagem": f"Inscrição confirmada em: {evento['title']}!"})

# ---------------- MAIN ---------------- #

if __name__ == '__main__':
    app.run(debug=True)

