import pandas as pd
import re
import unidecode
from rapidfuzz import process, fuzz
import os
import psycopg2

# =========================
# DB CONFIG (RENDER)
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

def conectar_db():
    return psycopg2.connect(DATABASE_URL)


# =========================
# LIMPEZA
# =========================
def limpar_nome(texto):
    if pd.isna(texto):
        return ""
    texto = unidecode.unidecode(str(texto).upper())
    texto = re.sub(r'[^A-Z ]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


# =========================
# INIT TABLE
# =========================
def init_db():
    conn = conectar_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS aprendizado (
            setor_limpo TEXT PRIMARY KEY,
            cod_correto TEXT
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


# =========================
# CARREGAR
# =========================
def carregar_aprendizado():
    conn = conectar_db()
    cur = conn.cursor()

    cur.execute("SELECT setor_limpo, cod_correto FROM aprendizado")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return dict(rows)


# =========================
# SALVAR
# =========================
def salvar_aprendizado(novos):
    conn = conectar_db()
    cur = conn.cursor()

    for setor, cod in novos.items():
        if not cod:
            continue

        cur.execute("""
            INSERT INTO aprendizado (setor_limpo, cod_correto)
            VALUES (%s, %s)
            ON CONFLICT (setor_limpo)
            DO UPDATE SET cod_correto = EXCLUDED.cod_correto
        """, (setor, cod))

    conn.commit()
    cur.close()
    conn.close()


# =========================
# MATCH
# =========================
def buscar_codigo(nome, base, mapa_aprendizado):
    nome = limpar_nome(nome)

    if not nome:
        return None, None, "vazio"

    if nome in mapa_aprendizado:
        return mapa_aprendizado[nome], 100, "aprendido"

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


# =========================
# PROCESSAR
# =========================
def processar_planilha(path_rh, path_base, output_path):
    df_rh = pd.read_excel(path_rh)
    df_base = pd.read_excel(path_base, sheet_name="LOJAS ATIVAS")

    df_rh["SETOR_LIMPO"] = df_rh["SETOR"].apply(limpar_nome)
    df_base["LOJA_LIMPA"] = df_base["LOJA"].apply(limpar_nome)

    mapa = carregar_aprendizado()

    resultados = df_rh["SETOR_LIMPO"].apply(
        lambda x: buscar_codigo(x, df_base, mapa)
    )

    df_rh[["COD_LOJA_ENCONTRADO", "SCORE_MATCH", "ORIGEM_MATCH"]] = pd.DataFrame(
        resultados.tolist(), index=df_rh.index
    )

    df_rh["COD_CORRETO_MANUAL"] = ""

    df_rh.to_excel(output_path, index=False)


# =========================
# APRENDER
# =========================
def aprender_com_feedback(path_feedback):
    df = pd.read_excel(path_feedback)

    if "COD_CORRETO_MANUAL" not in df.columns:
        raise Exception("Coluna COD_CORRETO_MANUAL não encontrada")

    df = df[df["COD_CORRETO_MANUAL"].notna()]
    df = df[df["COD_CORRETO_MANUAL"].astype(str).str.strip() != ""]

    df["SETOR_LIMPO"] = df["SETOR_LIMPO"].apply(limpar_nome)

    novos = dict(zip(df["SETOR_LIMPO"], df["COD_CORRETO_MANUAL"]))

    if not novos:
        return 0

    salvar_aprendizado(novos)

    return len(novos)
