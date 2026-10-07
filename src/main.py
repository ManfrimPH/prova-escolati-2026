from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    # Passa variáveis para o HTML processar
    return render_template('index.html', titulo="Flask + Docker", mensagem="Backend rodando com sucesso!")

if __name__ == '__main__':
    # host='0.0.0.0' é obrigatório para acessar a aplicação fora do container Docker
    app.run(host='0.0.0.0', port=9201, debug=True)