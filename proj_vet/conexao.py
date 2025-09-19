from flask import Flask, render_template, send_from_directory, send_file, request
import os
from pdf2image import convert_from_path

app = Flask(__name__)

# Pastas do projeto
PASTA_PDFS = os.path.join(os.path.dirname(__file__), 'pdfs')
PASTA_THUMBS = os.path.join(os.path.dirname(__file__), 'static', 'thumbs')

# Caminho fixo do Poppler
# Caminho do Poppler (pega da variável de ambiente ou deixa vazio)
POPPLER_PATH = os.getenv("POPPLER_PATH", "")


# Garante que a pasta de thumbs existe
os.makedirs(PASTA_THUMBS, exist_ok=True)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        return f"Usuário {nome} cadastrado com sucesso!"
    return render_template('cadastro.html')

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

@app.route('/central')
def central():
    return render_template('central_funcionalidades.html')

@app.route('/thumb/<nome>')
def thumb(nome):
    caminho_pdf = os.path.join(PASTA_PDFS, nome)
    caminho_thumb = os.path.join(PASTA_THUMBS, f"{nome}.png")

    if not os.path.exists(caminho_thumb):
        if POPPLER_PATH:
            # gera a primeira página como imagem usando Poppler
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

if __name__ == '__main__':
    app.run(debug=True)
