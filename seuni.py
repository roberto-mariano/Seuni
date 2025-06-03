from flask import Flask, render_template, request
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
ARQUIVO = 'inscricoes.csv'
LIMITES = {'OF1': 2, 'OF2': 2, 'MN1': 2, 'MN2': 2}
UPLOAD_FOLDER = 'comprovantes'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def contar_vagas():
    if not os.path.exists(ARQUIVO):
        return {}
    df = pd.read_csv(ARQUIVO)
    return df['minicurso_oficina'].value_counts().to_dict()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def formulario():
    erros = {}
    vagas_ocupadas = contar_vagas()

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        categoria = request.form['categoria']
        gt = request.form['gt']
        instituicao = request.form['instituicao']
        area = request.form['area']
        minicurso_oficina = request.form['minicurso_oficina']

        comprovante = request.files['comprovante']
        if comprovante and allowed_file(comprovante.filename):
            filename = secure_filename(f"{nome}_{comprovante.filename}")
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            comprovante.save(path)
        else:
            erros['comprovante'] = "Arquivo inválido. Envie imagem ou PDF."
            return render_template('formulario.html', vagas=vagas_ocupadas, erros=erros, limites=LIMITES)

        # Salva os dados em CSV
        df = pd.DataFrame([{
            'nome': nome,
            'email': email,
            'instituicao': instituicao,
            'area': area,
            'categoria': categoria,
            'gt': gt,
            'minicurso_oficina': minicurso_oficina
        }])
        df.to_csv(ARQUIVO, mode='a', header=not os.path.exists(ARQUIVO), index=False)
        return "<h2>Inscrição realizada com sucesso! Comprovante recebido.</h2>"

    return render_template('formulario.html', vagas=vagas_ocupadas, erros=erros, limites=LIMITES)

if __name__ == '__main__':
    app.run(debug=True)
