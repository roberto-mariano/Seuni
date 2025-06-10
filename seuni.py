from flask import Flask, render_template, request
import pandas as pd
import os
from werkzeug.utils import secure_filename

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO BÁSICA
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)

ARQUIVO_CSV = 'inscricoes.csv'
UPLOAD_FOLDER_COMPROVANTES = 'comprovantes'
UPLOAD_FOLDER_SUBMISSOES   = 'submissoes'

# Extensões aceitas
ALLOWED_EXTENSIONS_COMPROVANTE = {'pdf', 'jpg', 'jpeg', 'png'}
ALLOWED_EXTENSIONS_RESUMO      = {'docx'}

# Grupos de Trabalho
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

# Modalidades possíveis
MODALIDADES = ["Comunicação Oral", "Banner"]

# ──────────────────────────────────────────────────────────────────────────────
# PREPARO DE PASTAS
# ──────────────────────────────────────────────────────────────────────────────
# Pasta de comprovantes
os.makedirs(UPLOAD_FOLDER_COMPROVANTES, exist_ok=True)

# Pasta base de submissões + subpastas Modalidade/GT
for modalidade in MODALIDADES:
    pasta_mod = os.path.join(UPLOAD_FOLDER_SUBMISSOES,
                             modalidade.replace('ç','c').replace('ã','a').replace('í','i'))
    for gt in GRUPOS_TRABALHO:
        pasta_gt = os.path.join(pasta_mod, gt.replace('/', '-').replace(':', ''))
        os.makedirs(pasta_gt, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str, allowed_set: set) -> bool:
    """Verifica extensão do arquivo."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set


def contar_vagas():
    """Conta quantos inscritos cada minicurso/oficina já tem.
    Se o arquivo não existir **ou** estiver vazio, devolve {} para evitar
    pandas.errors.EmptyDataError.
    """
    if not os.path.exists(ARQUIVO_CSV) or os.path.getsize(ARQUIVO_CSV) == 0:
        return {}
    try:
        df = pd.read_csv(ARQUIVO_CSV)
    except pd.errors.EmptyDataError:
        # Arquivo existe mas está vazio (sem colunas ou só quebras de linha)
        return {}
    return df['minicurso_oficina'].value_counts().to_dict()

# Limites fixos (2 vagas)
LIMITES_MINICURSO = {'OF1': 2, 'OF2': 2, 'MN1': 2, 'MN2': 2}

# ──────────────────────────────────────────────────────────────────────────────
# ROTA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def formulario():
    erros = {}
    vagas_ocupadas = contar_vagas()

    if request.method == 'POST':
        # Dados comuns
        tipo_participacao = request.form.get('tipo_participacao')  # sem ou com
        nome        = request.form.get('nome', '').strip()
        email       = request.form.get('email', '').strip()
        instituicao = request.form.get('instituicao', '').strip()
        area        = request.form.get('area')
        categoria   = request.form.get('categoria')
        minicurso   = request.form.get('minicurso_oficina')

        # Limite de vagas
        if vagas_ocupadas.get(minicurso, 0) >= LIMITES_MINICURSO[minicurso]:
            erros['minicurso'] = f"A opção {minicurso} já está lotada. Escolha outra."

        # Comprovante de pagamento
        comprovante = request.files.get('comprovante')
        caminho_comprovante = ''
        if comprovante and allowed_file(comprovante.filename, ALLOWED_EXTENSIONS_COMPROVANTE):
            filename_comp = secure_filename(f"{nome}_{comprovante.filename}")
            caminho_comprovante = os.path.join(UPLOAD_FOLDER_COMPROVANTES, filename_comp)
            comprovante.save(caminho_comprovante)
        else:
            erros['comprovante'] = "Envie comprovante em PDF ou imagem (jpg/jpeg/png)."

        # Se for submissão
        titulo = autores = modalidade = gt = caminho_resumo = ''
        if tipo_participacao == 'com':
            titulo     = request.form.get('titulo_trabalho', '').strip()
            autores    = request.form.get('autores', '').strip()
            modalidade = request.form.get('modalidade')
            gt         = request.form.get('gt')

            if not titulo:
                erros['titulo_trabalho'] = "Título obrigatório."
            if not autores:
                erros['autores'] = "Autores obrigatórios."
            if modalidade not in MODALIDADES:
                erros['modalidade'] = "Modalidade inválida."
            if gt not in GRUPOS_TRABALHO:
                erros['gt'] = "GT inválido."

            resumo = request.files.get('resumo_doc')
            if resumo and allowed_file(resumo.filename, ALLOWED_EXTENSIONS_RESUMO):
                fname_resumo = secure_filename(f"{nome}_{resumo.filename}")
                pasta_dest   = os.path.join(UPLOAD_FOLDER_SUBMISSOES,
                                           modalidade.replace('ç','c').replace('ã','a').replace('í','i'),
                                           gt.replace('/', '-').replace(':', ''))
                caminho_resumo = os.path.join(pasta_dest, fname_resumo)
                resumo.save(caminho_resumo)
            else:
                erros['resumo_doc'] = "Envie o resumo em formato .docx."

        # Se houver erros, reexibe formulário
        if erros:
            return render_template('formulario.html', vagas=vagas_ocupadas, erros=erros,
                                   limites=LIMITES_MINICURSO, grupos_trabalho=GRUPOS_TRABALHO)

        # Salva em CSV
        registro = {
            'tipo_participacao': tipo_participacao,
            'nome': nome,
            'email': email,
            'instituicao': instituicao,
            'area': area,
            'categoria': categoria,
            'minicurso_oficina': minicurso,
            'titulo_trabalho': titulo,
            'autores': autores,
            'modalidade': modalidade,
            'grupo_trabalho': gt,
            'caminho_resumo': caminho_resumo,
            'caminho_comprovante': caminho_comprovante
        }
        pd.DataFrame([registro]).to_csv(ARQUIVO_CSV, mode='a', header=not os.path.exists(ARQUIVO_CSV), index=False)
        return "<h2>Inscrição realizada com sucesso!</h2>"

    # GET → renderiza formulário
    return render_template('formulario.html', vagas=vagas_ocupadas, erros={},
                           limites=LIMITES_MINICURSO, grupos_trabalho=GRUPOS_TRABALHO)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN (usa porta indicada pelo Railway)
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)