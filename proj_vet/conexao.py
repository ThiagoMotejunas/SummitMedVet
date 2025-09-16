from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        # Aqui você pode salvar os dados ou apenas exibir uma mensagem
        return f"Usuário {nome} cadastrado com sucesso!"
    return render_template('cadastro.html')

if __name__ == '__main__':
    app.run(debug=True)
