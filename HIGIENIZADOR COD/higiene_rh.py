import pandas as pd
import re
import unidecode
from rapidfuzz import process, fuzz
import os
import psycopg2

# =========================
# DB CONFIG
# =========================
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def conectar_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL não configurada")

    return psycopg2.connect(DATABASE_URL, sslmode='require')


# =========================
# TRATAR CÓDIGO
# =========================
def tratar_codigo(valor):
    if pd.isna(valor):
        return None
    try:
        return str(int(float(valor)))
    except:
        return str(valor).strip()


# =========================
# LIMPEZA BASE
# =========================
def limpar_nome(texto):
    if pd.isna(texto):
        return ""
    texto = unidecode.unidecode(str(texto).upper())
    texto = re.sub(r'[^A-Z ]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


# =========================
# 🔥 SEMÂNTICA
# =========================
def normalizar_semantico(texto):
    texto = limpar_nome(texto)

    if not texto:
        return ""

    stopwords = {"LOJA", "FILIAL", "UNIDADE", "STORE"}
    estados = {"SP", "RJ", "MG", "RS", "SC", "PR"}

    tokens = texto.split()

    tokens_filtrados = []

    for t in tokens:
        t = t.strip()

        # remove stopwords
        if t in stopwords:
            continue

        # remove estados isolados
        if t in estados:
            continue

        # remove estados grudados (SPITAQUERA)
        for uf in estados:
            if t.startswith(uf):
                t = t.replace(uf, "")

        if t:
            tokens_filtrados.append(t)

    # remove duplicados
    tokens_filtrados = list(set(tokens_filtrados))

    tokens_filtrados.sort()

    return " ".join(tokens_filtrados)


# =========================
# INIT DB
# =========================
def init_db():
    conn = conectar_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS aprendizado (
            chave TEXT PRIMARY KEY,
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

    try:
        # tenta estrutura nova
        cur.execute("SELECT chave, cod_correto FROM aprendizado")
        rows = cur.fetchall()
    except:
        conn.rollback() 
        # fallback estrutura antiga
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

    for chave, cod in novos.items():
        if not cod:
            continue

        cod = tratar_codigo(cod)

        try:
            # estrutura nova
            cur.execute("""
                INSERT INTO aprendizado (chave, cod_correto)
                VALUES (%s, %s)
                ON CONFLICT (chave)
                DO UPDATE SET cod_correto = EXCLUDED.cod_correto
            """, (chave, cod))
        except:
            conn.rollback()
            # estrutura antiga
            cur.execute("""
                INSERT INTO aprendizado (setor_limpo, cod_correto)
                VALUES (%s, %s)
                ON CONFLICT (setor_limpo)
                DO UPDATE SET cod_correto = EXCLUDED.cod_correto
            """, (chave, cod))

    conn.commit()
    cur.close()
    conn.close()


# =========================
# MATCH
# =========================
def buscar_codigo(nome, base, mapa_aprendizado):
    nome_limpo = limpar_nome(nome)
    nome_semantico = normalizar_semantico(nome)

    if not nome_limpo:
        return None, None, "vazio"

    # aprendizado direto
    if nome_semantico in mapa_aprendizado:
        return mapa_aprendizado[nome_semantico], 100, "aprendido_semantico"

    # fuzzy no aprendizado
    if mapa_aprendizado:
        match_ap = process.extractOne(
            nome_semantico,
            list(mapa_aprendizado.keys()),
            scorer=fuzz.token_sort_ratio
        )

        if match_ap and match_ap[1] >= 90:
            return mapa_aprendizado[match_ap[0]], match_ap[1], "aprendido_fuzzy"

    # fuzzy base
    match = process.extractOne(
        nome_limpo,
        base["LOJA_LIMPA"].dropna(),
        scorer=fuzz.token_sort_ratio
    )

    if match:
        loja = match[0]
        score = match[1]

        coluna_cod = "CÓD" if "CÓD" in base.columns else "COD"

        linha = base.loc[base["LOJA_LIMPA"] == loja]

        if linha.empty:
            return None, score, "fuzzy_erro"

        cod = tratar_codigo(linha.iloc[0][coluna_cod])

        return cod, score, "fuzzy_base"

    return None, None, "nao_encontrado"

# =========================
# PROCESSAR
# =========================
def processar_planilha(path_rh, path_base, output_path):
    df_rh = pd.read_excel(path_rh)
    df_base = pd.read_excel(path_base, sheet_name="LOJAS ATIVAS")

    df_rh["SETOR_LIMPO"] = df_rh["SETOR"].apply(limpar_nome)
    df_base["LOJA_LIMPA"] = df_base["LOJA"].apply(limpar_nome)

    df_base["CÓD"] = df_base["CÓD"].apply(tratar_codigo)

    mapa = carregar_aprendizado()

    resultados = df_rh["SETOR"].apply(
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

    df["CHAVE"] = df["SETOR"].apply(normalizar_semantico)
    df["COD_CORRETO_MANUAL"] = df["COD_CORRETO_MANUAL"].apply(tratar_codigo)

    df_group = df.groupby("CHAVE")["COD_CORRETO_MANUAL"].agg(lambda x: x.mode()[0])
    novos = df_group.to_dict()

    if not novos:
        return 0

    salvar_aprendizado(novos)

    return len(novos)
