from flask import Flask, render_template, send_from_directory, send_file, jsonify, request
import os
from pdf2image import convert_from_path

app = Flask(__name__)

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
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        return f"Usuário {nome} cadastrado com sucesso!"
    return render_template('cadastro.html')

@app.route('/criar_conta')
def criar_conta():
    return render_template('criar_conta.html')

@app.route('/bulario')
def bulario():
    return render_template('bulario.html')

@app.route('/calculadora')
def calculadora():
    return render_template('calculadora.html')

@app.route('/componentes')
def componentes():
    return render_template('componentes_liga.html')

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

# Exemplo de “banco” em memória (substitua por DB depois)
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
