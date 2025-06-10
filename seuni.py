from flask import Flask, render_template, request
import pandas as pd
import os
from werkzeug.utils import secure_filename

# Configurações do Flask
app = Flask(__name__)

# Arquivos e pastas
ARQUIVO_CSV = 'inscricoes.csv'
UPLOAD_FOLDER_COMPROVANTES = 'comprovantes'
UPLOAD_FOLDER_SUBMISSOES   = 'submissoes'

# Certifique-se de que as pastas de upload existem
for folder in [UPLOAD_FOLDER_COMPROVANTES, UPLOAD_FOLDER_SUBMISSOES]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Extensões permitidas para uploads
ALLOWED_EXTENSIONS_COMPROVANTE = {'pdf', 'jpg', 'jpeg', 'png'}
ALLOWED_EXTENSIONS_RESUMO      = {'docx'}

# Lista completa dos Grupos de Trabalho (GT)
GRUPOS_TRABALHO = [
    "GT 1 - Matemática, Modelagem e Tecnologias Aplicadas",
    "GT 2 - Desafios Contemporâneos no Ensino e na Aprendizagem da Matemática",
    "GT 3 - Estágio, formação de professores e prática docente",
    "GT 4 - Gestão Contábil e Financeira",
    "GT 5 - Contabilidade Aplicada ao Setor Público e Terceiro Setor",
    "GT 6 - Estágio supervisionado na formação contábil",
    "GT 7 - Práticas de linguagem, letramentos e estudos do discurso",
    "GT 8 - Percepções da prosa contemporânea em literaturas de Língua Portuguesa",
    "GT 9 - Políticas e práticas de Formação de profissionais da educação no contexto da era digital",
    "GT 10 - Tecnologia, gestão e inclusão na educação"
]

# Função auxiliar para validar extensão de arquivo
def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

# Conta quantas inscrições cada minicurso/oficina já possui
def contar_vagas():
    if not os.path.exists(ARQUIVO_CSV):
        return {}
    df = pd.read_csv(ARQUIVO_CSV)
    return df['minicurso_oficina'].value_counts().to_dict()

@app.route('/', methods=['GET', 'POST'])
def formulario():
    erros = {}
    vagas_ocupadas = contar_vagas()

    if __name__ == '__main__':
        # Railway injeta a variável PORT; usa 5000 localmente
        import os
        port = int(os.environ.get("PORT", 5000))
        app.run(host='0.0.0.0', port=port)
