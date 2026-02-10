import pandas as pd
import re
import unidecode
from rapidfuzz import process, fuzz
import os

# =============================
# CAMINHOS
# =============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(BASE_DIR, "data")
os.makedirs(PASTA_DADOS, exist_ok=True)

CAMINHO_APRENDIZADO = os.path.join(PASTA_DADOS, "base_conhecimento.csv")

# =============================
# FUNÇÕES AUXILIARES
# =============================
def limpar_nome(texto):
    if pd.isna(texto):
        return ""
    texto = unidecode.unidecode(str(texto).upper())
    texto = re.sub(r'[^A-Z ]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def carregar_aprendizado():
    if os.path.exists(CAMINHO_APRENDIZADO):
        return pd.read_csv(CAMINHO_APRENDIZADO)
    return pd.DataFrame(columns=["SETOR_LIMPO", "COD_CORRETO"])


def salvar_aprendizado(df):
    df = df.drop_duplicates(subset=["SETOR_LIMPO"], keep="last")
    df.to_csv(CAMINHO_APRENDIZADO, index=False)


# =============================
# BUSCA INTELIGENTE
# =============================
def buscar_codigo(nome, base, mapa_aprendizado):
    if not nome:
        return None, None, "vazio"

    # 1️⃣ aprendizado manual (prioridade máxima)
    if nome in mapa_aprendizado:
        return mapa_aprendizado[nome], 100, "aprendido"

    # 2️⃣ fuzzy match
    match = process.extractOne(
        nome,
        base["LOJA_LIMPA"],
        scorer=fuzz.token_sort_ratio
    )

    if match:
        loja = match[0]
        score = match[1]
        cod = base.loc[base["LOJA_LIMPA"] == loja, "CÓD"].values[0]
        return cod, score, "fuzzy"

    return None, None, "nao_encontrado"


# =============================
# PROCESSAMENTO PRINCIPAL
# =============================
def processar_planilha(path_rh, path_base, output_path):
    df_rh = pd.read_excel(path_rh)
    df_base = pd.read_excel(path_base, sheet_name="LOJAS ATIVAS")

    df_rh["SETOR_LIMPO"] = df_rh["SETOR"].apply(limpar_nome)
    df_base["LOJA_LIMPA"] = df_base["LOJA"].apply(limpar_nome)

    aprendizado = carregar_aprendizado()
    mapa = dict(zip(aprendizado["SETOR_LIMPO"], aprendizado["COD_CORRETO"]))

    resultados = df_rh["SETOR_LIMPO"].apply(
        lambda x: buscar_codigo(x, df_base, mapa)
    )

    df_rh[["COD_LOJA_ENCONTRADO", "SCORE_MATCH", "ORIGEM_MATCH"]] = pd.DataFrame(
        resultados.tolist(), index=df_rh.index
    )

    df_rh["COD_CORRETO_MANUAL"] = ""

    df_rh.to_excel(output_path, index=False)


# =============================
# APRENDIZADO COM FEEDBACK
# =============================
def aprender_com_feedback(path_feedback):
    df = pd.read_excel(path_feedback)

    if "COD_CORRETO_MANUAL" not in df.columns:
        raise Exception("Coluna COD_CORRETO_MANUAL não encontrada")

    df = df[df["COD_CORRETO_MANUAL"].notna()]

    if df.empty:
        print("⚠️ Nenhum aprendizado novo")
        return

    novos = df[["SETOR_LIMPO", "COD_CORRETO_MANUAL"]]
    novos.columns = ["SETOR_LIMPO", "COD_CORRETO"]

    base = carregar_aprendizado()
    base = pd.concat([base, novos], ignore_index=True)

    salvar_aprendizado(base)

    return len(novos)


    print(f"✅ {len(novos)} aprendizados salvos")
