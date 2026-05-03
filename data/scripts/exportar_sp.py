"""
Exporta tabelas do BigQuery (filtradas para SP) para DuckDB local.
Roda uma única vez. Depois o dashboard lê do arquivo local.
"""
import os
import sys
import duckdb
from google.cloud import bigquery

PROJECT = "project-a8f8452a-3033-4dd8-99a"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "sp_mvp.duckdb")

client = bigquery.Client(project=PROJECT)


def bq(sql):
    return client.query(sql).to_dataframe()


def normalizar_tipos(df):
    """Converte tipos de data do BigQuery (dbdate) para string, que o DuckDB entende."""
    for col in df.columns:
        if hasattr(df[col], 'dtype') and 'date' in str(df[col].dtype).lower():
            df[col] = df[col].astype(str)
    return df


def salvar(con, table, df):
    df = normalizar_tipos(df)
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(f"CREATE TABLE {table} AS SELECT * FROM df")
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  [{table}] {n:,} linhas salvas", flush=True)


def exportar_por_ano(con, table, dataset):
    """Exporta tabela grande ano a ano para não estourar memória."""
    anos = bq(f"""
        SELECT DISTINCT ano
        FROM `{PROJECT}.{dataset}.{table}`
        WHERE sigla_uf = 'SP'
        ORDER BY ano
    """)["ano"].tolist()
    print(f"  Anos: {anos}", flush=True)

    first = True
    for ano in anos:
        print(f"  {table} {ano}...", flush=True)
        df = bq(f"""
            SELECT * FROM `{PROJECT}.{dataset}.{table}`
            WHERE sigla_uf = 'SP' AND ano = {ano}
        """)
        print(f"    {len(df):,} linhas", flush=True)
        df = normalizar_tipos(df)
        if first:
            con.execute(f"DROP TABLE IF EXISTS {table}")
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM df")
            first = False
        else:
            con.execute(f"INSERT INTO {table} SELECT * FROM df")

    total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  [{table}] TOTAL: {total:,} linhas", flush=True)


def main():
    # Conecta no arquivo existente (retomando de onde parou)
    con = duckdb.connect(DB_PATH)
    print(f"DuckDB: {DB_PATH}\n")
    print("Retomando exportacao a partir de fct_empresas...\n")

    # 3. fct_empresas — ~475k linhas
    print("\n3/5 fct_empresas...")
    df = bq(f"""
        SELECT * FROM `{PROJECT}.raw_facts.fct_empresas`
        WHERE sigla_uf = 'SP'
    """)
    salvar(con, "fct_empresas", df)

    # 4. fct_empregos — 13M linhas, exportar por ano
    print("\n4/5 fct_empregos (por ano)...")
    exportar_por_ano(con, "fct_empregos", "raw_facts")

    # 5. fct_mercado_superior — ~775k linhas, exportar por ano
    print("\n5/5 fct_mercado_superior (por ano)...")
    exportar_por_ano(con, "fct_mercado_superior", "raw_facts")

    # Resumo final
    print("\n=== RESUMO FINAL ===")
    for t in ["dim_municipio", "fct_empregos", "fct_estabelecimentos", "fct_empresas", "fct_mercado_superior"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,}")

    tamanho_mb = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"\nArquivo: {DB_PATH}")
    print(f"Tamanho: {tamanho_mb:.0f} MB")
    print("\nExportacao concluida!")
    con.close()


if __name__ == "__main__":
    main()
