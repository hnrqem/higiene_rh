from flask import Flask, render_template, request, send_file
import os
import uuid
from higiene_rh import processar_planilha, aprender_com_feedback, init_db

BASE_DIR = os.getcwd()

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)

# 🔥 inicializa DB ao subir
from higiene_rh import init_db

# roda uma vez ao iniciar o container
try:
    init_db()
    print("✅ Banco inicializado")
except Exception as e:
    print("❌ Erro ao inicializar banco:", e)



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        arquivo_rh = request.files.get('rh')
        arquivo_base = request.files.get('base')

        if not arquivo_rh or not arquivo_base:
            return render_template('index.html', msg='⚠️ Envie os dois arquivos')

        nome_rh = f"{uuid.uuid4()}_{arquivo_rh.filename}"
        nome_base = f"{uuid.uuid4()}_{arquivo_base.filename}"

        path_rh = os.path.join(UPLOAD_FOLDER, nome_rh)
        path_base = os.path.join(UPLOAD_FOLDER, nome_base)

        arquivo_rh.save(path_rh)
        arquivo_base.save(path_base)

        output_path = os.path.join(OUTPUT_FOLDER, 'PLANILHA_HIGIENIZADA.xlsx')

        processar_planilha(path_rh, path_base, output_path)

        return render_template('resultado.html', msg='✅ Arquivo higienizado com sucesso!')

    return render_template('index.html')


@app.route('/download')
def download():
    return send_file(
        os.path.join(OUTPUT_FOLDER, 'PLANILHA_HIGIENIZADA.xlsx'),
        as_attachment=True
    )


@app.route('/aprender', methods=['GET', 'POST'])
def aprender():
    if request.method == 'POST':
        arquivo = request.files.get('feedback')

        if not arquivo or arquivo.filename == '':
            return render_template('aprender.html', msg='⚠️ Nenhum arquivo enviado')

        nome = f"{uuid.uuid4()}_{arquivo.filename}"
        caminho = os.path.join(UPLOAD_FOLDER, nome)
        arquivo.save(caminho)

        qtd = aprender_com_feedback(caminho)

        return render_template('aprender.html', msg=f'✅ {qtd} aprendizados aplicados')

    return render_template('aprender.html')


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
