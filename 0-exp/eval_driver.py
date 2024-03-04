import duckdb
import polars as pl
import pandas as pd


def attr_evaluation(toml_dict, dataset_city, dataset_name):
    print("\n Evaluate per attribute")

    evaluation_config = toml_dict['evaluation']
    eval_attrs = evaluation_config['eval_attrs']

    # connection
    user = "holouser"
    pwd = "holopass"
    host = "localhost"
    port = "5432"
    db = f"holodb_hc_{dataset_name}"
    polars_conn = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

    # read database
    pdf_dirty = pl.read_database(f"SELECT * FROM {dataset_name}", polars_conn)
    pdf_repair = pl.read_database(f"SELECT * FROM {dataset_name}_repaired", polars_conn)
    pdf_clean_hc = pl.read_database(f"SELECT * FROM {dataset_name}_clean", polars_conn)

    # zip table together
    repair_column_rename = ", ".join([f"t2.{attr} as {attr}_repair" for attr in eval_attrs])
    sql = f"SELECT t1.*, {repair_column_rename} FROM pdf_dirty t1, pdf_repair t2 WHERE t1._tid_ = t2._tid_"
    pdf2 = duckdb.query(sql).pl()

    pdf_clean = pdf_clean_hc.pivot(index="_tid_", columns="_attribute_", values="_value_")
    gt_column_rename = ", ".join([f"t2.{attr} as {attr}_gt" for attr in eval_attrs])
    sql = f"SELECT t1.*, {gt_column_rename} FROM pdf2 t1, pdf_clean t2 WHERE t1._tid_ = t2._tid_"
    pdf_eval = duckdb.query(sql).pl()

    null_count = 0
    wrong_count = 0
    error_count = 0
    repair_count = 0
    correct_repair_count = 0
    eval_stat = []

    for attr in eval_attrs:
        sql_null = f"SELECT count(1) FROM pdf_eval WHERE {attr} = '_nan_'"
        sql_wrong = f"SELECT count(1) FROM pdf_eval WHERE {attr} <> '_nan_' AND {attr} <> {attr}_gt"
        attr_null_count = duckdb.query(sql_null).fetchone()[0]
        attr_wrong_count = duckdb.query(sql_wrong).fetchone()[0]

        sql_error = f"SELECT count(1) FROM pdf_eval WHERE {attr} <> {attr}_gt"
        sql_repair = f"SELECT count(1) FROM pdf_eval WHERE {attr} <> {attr}_repair"
        sql_correct_repair = f"SELECT count(1) FROM pdf_eval WHERE {attr} <> {attr}_repair AND {attr}_repair = {attr}_gt"
        attr_error_count = duckdb.query(sql_error).fetchone()[0]
        attr_repair_count = duckdb.query(sql_repair).fetchone()[0]
        attr_correct_repair_count = duckdb.query(sql_correct_repair).fetchone()[0]

        null_count += attr_null_count
        wrong_count += attr_wrong_count
        error_count += attr_error_count
        repair_count += attr_repair_count
        correct_repair_count += attr_correct_repair_count

        attr_stat = {
            "attr": attr,
            "null_count": attr_null_count,
            "wrong_count": attr_wrong_count,
            "error_count": attr_error_count,
            "repair_count": attr_repair_count,
            "correct_repair_count": attr_correct_repair_count,
            "precision": attr_correct_repair_count / attr_repair_count if attr_repair_count > 0 else 0,
            "recall": attr_correct_repair_count / attr_error_count if attr_error_count > 0 else 0,
            "f1": 2 * attr_correct_repair_count / (attr_repair_count + attr_error_count) if (attr_repair_count + attr_error_count) > 0 else 0
        }
        eval_stat.append(attr_stat)

    overall_stat = {
        "attr": "overall",
        "null_count": null_count,
        "wrong_count": wrong_count,
        "error_count": error_count,
        "repair_count": repair_count,
        "correct_repair_count": correct_repair_count,
        "precision": correct_repair_count / repair_count if repair_count > 0 else 0,
        "recall": correct_repair_count / error_count if error_count > 0 else 0,
        "f1": 2 * correct_repair_count / (repair_count + error_count) if (repair_count + error_count) > 0 else 0
    }
    eval_stat.append(overall_stat)

    df_eval_stat = pd.DataFrame(eval_stat)
    df_eval_stat = df_eval_stat[["attr", "precision", "recall", "f1", "null_count", "wrong_count", "error_count", "repair_count", "correct_repair_count"]]
    t = df_eval_stat.set_index("attr").T
    t = t.rename_axis("metric", axis=1)
    t = t[["overall"] + eval_attrs]
    pd.set_option("display.precision", 3)
    print(t)

    # export to csv
    file_name = evaluation_config['file_name']
    t.to_csv(f"{dataset_city}-{dataset_name}/{file_name}", float_format="%.3f")
