import os, json, base64, re, tempfile, datetime
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import gspread, pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ── Config constantes ──────────────────────────────────────────────
LIMITES_MINICURSO = {'OF1':2, 'OF2':2, 'MN1':2, 'MN2':2}
MODALIDADES = ["Comunicação Oral", "Banner"]
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

# ── Helper: credenciais Google ─────────────────────────────────────
def google_creds():
    if os.path.exists("seuni-bot.json"):
        return Credentials.from_service_account_file(
            "seuni-bot.json",
            scopes=[
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets"
            ])
    data = base64.b64decode(os.environ["GOOGLE_CREDS_B64"])
    return Credentials.from_service_account_info(
        json.loads(data),
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ])

creds  = google_creds()
gc     = gspread.authorize(creds)
sheet  = gc.open(os.getenv("SHEET_NAME", "1nBhye9-YHQP9eZA7-erwjpmgo2XhkdNkuwZTEKKhKpE/edit?gid=0#gid=0")).worksheet("inscricoes")
drive  = build('drive', 'v3', credentials=creds)

FOLDER_COMPROVANTES = os.environ["DRIVE_COMPROVANTES_ID"]
FOLDER_RESUMOS      = os.environ["DRIVE_RESUMOS_ID"]

# ── Utils ──────────────────────────────────────────────────────────
def sanitize(text: str) -> str:
    """Remove caracteres problemáticos para nomes de arquivo."""
    return re.sub(r"[^\w\s.-]", "_", text, flags=re.UNICODE)

def upload(local_path: str, parent_id: str) -> str:
    """Faz upload ao Drive e retorna link compartilhável."""
    meta = {"name": os.path.basename(local_path), "parents": [parent_id]}
    media = MediaFileUpload(local_path, resumable=False)
    file = drive.files().create(body=meta, media_body=media, fields="webViewLink,id").execute()
    return file["webViewLink"]

def get_subfolder(modalidade: str, gt: str) -> str:
    """Garante subpasta modalidade/gt dentro de FOLDER_RESUMOS e retorna o ID."""
    # 1º nível = modalidade
    mod_id = find_or_create(sanitize(modalidade), FOLDER_RESUMOS)
    # 2º nível = GT
    return find_or_create(sanitize(gt), mod_id)

def find_or_create(name: str, parent: str) -> str:
    q = (f"mimeType='application/vnd.google-apps.folder' and trashed=false and "
         f"name='{name}' and '{parent}' in parents")
    results = drive.files().list(q=q, fields="files(id)", pageSize=1).execute()
    items = results.get("files", [])
    if items:
        return items[0]["id"]
    meta = {"name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent]}
    return drive.files().create(body=meta, fields="id").execute()["id"]

def contar_vagas():
    """Conta inscrições por minicurso diretamente na planilha (coluna 7)."""
    try:
        col7 = sheet.col_values(7)[1:]  # pula cabeçalho
    except Exception:
        return {}
    return pd.Series(col7).value_counts().to_dict()

# ── App Flask ──────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def formulario():
    erros = {}
    vagas = contar_vagas()

    if request.method == "POST":
        # Campos comuns
        tipo = request.form.get("tipo_participacao")
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        inst = request.form.get("instituicao", "").strip()
        area = request.form.get("area")
        cat  = request.form.get("categoria")
        mini = request.form.get("minicurso_oficina")

        if vagas.get(mini, 0) >= LIMITES_MINICURSO[mini]:
            erros["minicurso"] = f"{mini} esgotado."

        # Comprovante
        comp = request.files.get("comprovante")
        comp_link = ""
        if comp and comp.filename:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                comp.save(tmp.name)
                comp_link = upload(tmp.name, FOLDER_COMPROVANTES)
        else:
            erros["comprovante"] = "Envie comprovante."

        # Se submissão
        titulo = autores = modalidade = gt = resumo_link = ""
        if tipo == "com":
            titulo     = request.form.get("titulo_trabalho", "").strip()
            autores    = request.form.get("autores", "").strip()
            modalidade = request.form.get("modalidade")
            gt         = request.form.get("gt")

            if not titulo:  erros["titulo_trabalho"] = "Título obrigatório"
            if not autores: erros["autores"] = "Autores obrigatórios"
            if modalidade not in MODALIDADES:
                erros["modalidade"] = "Modalidade inválida"
            if gt not in GRUPOS_TRABALHO:
                erros["gt"] = "GT inválido"

            resumo = request.files.get("resumo_doc")
            if resumo and resumo.filename.endswith(".docx"):
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    resumo.save(tmp.name)
                    folder = get_subfolder(modalidade, gt)
                    resumo_link = upload(tmp.name, folder)
            else:
                erros["resumo_doc"] = "Envie .docx"

        if erros:
            return render_template("formulario.html", vagas=vagas, erros=erros,
                                   limites=LIMITES_MINICURSO, grupos_trabalho=GRUPOS_TRABALHO)

        # Grava na planilha
        linha = [
            nome, email, inst, area, cat, tipo, mini,
            titulo, autores, modalidade, gt,
            comp_link, resumo_link,
            datetime.datetime.now().isoformat(timespec="seconds")
        ]
        sheet.append_row(linha, value_input_option="USER_ENTERED")

        return "<h2>Inscrição registrada com sucesso!</h2>"

    return render_template("formulario.html", vagas=vagas, erros={},
                           limites=LIMITES_MINICURSO, grupos_trabalho=GRUPOS_TRABALHO)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
