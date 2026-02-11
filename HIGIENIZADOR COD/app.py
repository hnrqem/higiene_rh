from flask import Flask, render_template, request, send_file
import os
from higiene_rh import processar_planilha, aprender_com_feedback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        arquivo_rh = request.files.get('rh')
        arquivo_base = request.files.get('base')

        if not arquivo_rh or not arquivo_base:
            return render_template(
                'index.html',
                msg='⚠️ Envie os dois arquivos'
            )

        path_rh = os.path.join(UPLOAD_FOLDER, arquivo_rh.filename)
        path_base = os.path.join(UPLOAD_FOLDER, arquivo_base.filename)

        arquivo_rh.save(path_rh)
        arquivo_base.save(path_base)

        output_path = os.path.join(OUTPUT_FOLDER, 'RH_HIGIENIZADO.xlsx')

        processar_planilha(path_rh, path_base, output_path)

        return render_template(
            'resultado.html',
            msg='✅ Arquivo higienizado com sucesso!'
        )

    return render_template('index.html')



@app.route('/download')
def download():
    return send_file(
        os.path.join(OUTPUT_FOLDER, 'RH_HIGIENIZADO.xlsx'),
        as_attachment=True
    )

@app.route('/aprender', methods=['GET', 'POST'])
def aprender():
    if request.method == 'POST':
        arquivo = request.files.get('feedback')

        if not arquivo or arquivo.filename == '':
            return render_template(
                'aprender.html',
                msg='⚠️ Nenhum arquivo enviado'
            )

        caminho = os.path.join(UPLOAD_FOLDER, arquivo.filename)
        arquivo.save(caminho)

        aprender_com_feedback(caminho)

        return render_template(
            'aprender.html',
            msg='✅ Aprendizado aplicado com sucesso'
        )

    return render_template('aprender.html')


if __name__ == '__main__':
    app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

