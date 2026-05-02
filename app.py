from datetime import date, timedelta

import pandas as pd
import streamlit as st

from db import (
    add_customer,
    add_customers_bulk,
    add_document,
    add_customer_item,
    get_customer_items,
    get_all_customer_items,
    get_customer,
    get_customers,
    get_documents,
    init_db,
    update_document_no,
    
)
from invoice_logic import (
    calculate_totals,
    create_document_no,
    create_excel_document,
)


def main():
    st.set_page_config(
        page_title="見積・請求書作成アプリ",
        layout="wide",
    )

    init_db()

    st.title("見積・請求書作成アプリ")
    st.write("顧客登録、見積書・請求書作成、Excel出力を行う業務アプリです。")

    tab_customer, tab_item, tab_document, tab_history = st.tabs(
        ["顧客登録", "品目マスタ", "見積・請求書作成", "作成履歴"]
    )

    with tab_customer:
        show_customer_form()

    with tab_item:
        show_customer_item_master()

    with tab_document:
        show_document_form()

    with tab_history:
        show_history()


def show_customer_form():
    st.subheader("顧客登録")

    manual_tab, upload_tab = st.tabs(["手入力登録", "CSV/Excel一括登録"])

    with manual_tab:
        st.write("顧客情報を1件ずつ登録します。")

        with st.form("customer_form"):
            company_name = st.text_input("会社名", placeholder="株式会社サンプル")
            postal_code = st.text_input("郵便番号", placeholder="100-0001")
            address = st.text_input("住所", placeholder="東京都千代田区...")
            contact_name = st.text_input("担当者名", placeholder="山田 太郎")
            email = st.text_input("メールアドレス", placeholder="sample@example.com")
            phone = st.text_input("電話番号", placeholder="03-0000-0000")

            submitted = st.form_submit_button("顧客を登録")

        if submitted:
            if not company_name:
                st.error("会社名は必須です。")
                return

            add_customer(
                company_name=company_name,
                postal_code=postal_code,
                address=address,
                contact_name=contact_name,
                email=email,
                phone=phone,
            )

            st.success("顧客を登録しました。")

    with upload_tab:
        st.write("CSVまたはExcelファイルから顧客情報を一括登録します。")

        st.info(
            "必要な列: 会社名, 郵便番号, 住所, 担当者名, メールアドレス, 電話番号\n\n"
            "必須列は「会社名」のみです。"
        )

        uploaded_file = st.file_uploader(
            "顧客情報ファイルをアップロードしてください",
            type=["csv", "xlsx", "xls"],
            key="customer_upload",
        )

        if uploaded_file is not None:
            try:
                customer_df = load_customer_file(uploaded_file)

                st.subheader("アップロード内容プレビュー")
                st.dataframe(customer_df, use_container_width=True)

                customers = convert_customer_dataframe(customer_df)

                if st.button("この内容で一括登録"):
                    result = add_customers_bulk(customers)

                    st.success(
                        f"一括登録が完了しました。"
                        f"登録: {result['inserted_count']}件 / "
                        f"スキップ: {result['skipped_count']}件"
                    )

            except Exception as e:
                st.error(f"ファイルの読み込みまたは登録に失敗しました: {e}")

    customers = get_customers()

    st.subheader("登録済み顧客")

    if customers:
        st.dataframe(pd.DataFrame(customers), use_container_width=True)
    else:
        st.info("まだ顧客が登録されていません。")

def show_customer_item_master():
    st.subheader("顧客別 品目マスタ")

    customers = get_customers()

    if not customers:
        st.warning("先に顧客を登録してください。")
        return

    customer_options = {
        f"{customer['company_name']} / ID:{customer['id']}": customer["id"]
        for customer in customers
    }

    selected_customer_label = st.selectbox(
        "顧客を選択",
        list(customer_options.keys()),
        key="item_master_customer",
    )

    customer_id = customer_options[selected_customer_label]

    st.write("選択した顧客に紐づく品目を登録します。")

    with st.form("customer_item_form"):
        name = st.text_input(
            "品目名",
            placeholder="例：要件定義、画面実装、月額保守費",
        )

        col1, col2 = st.columns(2)

        with col1:
            default_quantity = st.number_input(
                "標準数量",
                min_value=1,
                value=1,
                step=1,
            )

        with col2:
            unit_price = st.number_input(
                "単価",
                min_value=0,
                value=0,
                step=1000,
            )

        description = st.text_area(
            "説明",
            placeholder="例：ヒアリング、要件整理、仕様書作成を含む",
        )

        submitted = st.form_submit_button("品目を登録")

    if submitted:
        if not name:
            st.error("品目名は必須です。")
            return

        add_customer_item(
            customer_id=customer_id,
            name=name,
            default_quantity=int(default_quantity),
            unit_price=int(unit_price),
            description=description,
        )

        st.success("品目を登録しました。")

    st.subheader("この顧客の登録済み品目")

    customer_items = get_customer_items(customer_id)

    if customer_items:
        st.dataframe(pd.DataFrame(customer_items), use_container_width=True)
    else:
        st.info("この顧客にはまだ品目が登録されていません。")

    st.subheader("全顧客の品目一覧")

    all_items = get_all_customer_items()

    if all_items:
        st.dataframe(pd.DataFrame(all_items), use_container_width=True)
    else:
        st.info("まだ品目は登録されていません。")

def show_document_form():
    st.subheader("見積・請求書作成")

    customers = get_customers()

    if not customers:
        st.warning("先に顧客を登録してください。")
        return

    customer_options = {
        f"{customer['company_name']} / ID:{customer['id']}": customer["id"]
        for customer in customers
    }

    doc_type = st.radio("帳票種別", ["見積書", "請求書"], horizontal=True)

    selected_customer_label = st.selectbox(
        "顧客",
        list(customer_options.keys()),
    )

    customer_id = customer_options[selected_customer_label]
    customer = get_customer(customer_id)

    col1, col2 = st.columns(2)

    with col1:
        issue_date = st.date_input("発行日", value=date.today())

    with col2:
        default_due_date = date.today() + timedelta(days=30)
        due_date_label = "支払期限" if doc_type == "請求書" else "有効期限"
        due_date = st.date_input(due_date_label, value=default_due_date)

    subject = st.text_input(
        "件名",
        value="業務システム開発",
    )

    st.subheader("明細")

    item_count = st.number_input(
        "明細行数",
        min_value=1,
        max_value=10,
        value=3,
        step=1,
    )

    customer_items = get_customer_items(customer_id)

    items = []

    for index in range(item_count):
        st.write(f"明細 {index + 1}")

        item_options = {"手入力する": None}

        for customer_item in customer_items:
            label = (
                f"{customer_item['name']} "
                f"/ 標準数量: {customer_item['default_quantity']} "
                f"/ 単価: {customer_item['unit_price']:,}円"
            )
            item_options[label] = customer_item

        selected_item_label = st.selectbox(
            "品目リスト",
            list(item_options.keys()),
            key=f"item_select_{customer_id}_{index}",
        )

        selected_item = item_options[selected_item_label]

        col_name, col_quantity, col_unit_price = st.columns([3, 1, 1])

        if selected_item is None:
            with col_name:
                name = st.text_input(
                    "品目",
                    value="",
                    key=f"name_manual_{customer_id}_{index}",
                    placeholder="例：要件定義、画面実装、テスト",
                )

            with col_quantity:
                quantity = st.number_input(
                    "数量",
                    min_value=0,
                    value=1,
                    step=1,
                    key=f"quantity_manual_{customer_id}_{index}",
                )

            with col_unit_price:
                unit_price = st.number_input(
                    "単価",
                    min_value=0,
                    value=0,
                    step=1000,
                    key=f"unit_price_manual_{customer_id}_{index}",
                )

        else:
            with col_name:
                name = st.text_input(
                    "品目",
                    value=selected_item["name"],
                    key=f"name_master_{customer_id}_{index}_{selected_item['id']}",
                )

            with col_quantity:
                quantity = st.number_input(
                    "数量",
                    min_value=0,
                    value=int(selected_item["default_quantity"]),
                    step=1,
                    key=f"quantity_master_{customer_id}_{index}_{selected_item['id']}",
                )

            with col_unit_price:
                unit_price = st.number_input(
                    "単価",
                    min_value=0,
                    value=int(selected_item["unit_price"]),
                    step=1000,
                    key=f"unit_price_master_{customer_id}_{index}_{selected_item['id']}",
                )

        if name:
            items.append(
                {
                    "name": name,
                    "quantity": int(quantity),
                    "unit_price": int(unit_price),
                }
            )

    tax_rate_percent = st.selectbox(
        "消費税率",
        [10, 8, 0],
        index=0,
    )

    tax_rate = tax_rate_percent / 100

    totals = calculate_totals(items, tax_rate)

    st.subheader("金額サマリー")

    col_subtotal, col_tax, col_total = st.columns(3)

    with col_subtotal:
        st.metric("小計", f"{totals['subtotal']:,}円")

    with col_tax:
        st.metric("消費税", f"{totals['tax']:,}円")

    with col_total:
        st.metric("合計", f"{totals['total']:,}円")

    note = st.text_area(
        "備考",
        value="お支払い条件：月末締め翌月末払い",
    )

    if st.button("保存してExcelを作成"):
        if not items:
            st.error("明細を1件以上入力してください。")
            return

        document_id = add_document(
            doc_type=doc_type,
            document_no="",
            customer_id=customer_id,
            issue_date=str(issue_date),
            due_date=str(due_date),
            subject=subject,
            items=items,
            subtotal=totals["subtotal"],
            tax=totals["tax"],
            total=totals["total"],
            note=note,
        )

        document_no = create_document_no(doc_type, document_id)
        update_document_no(document_id, document_no)

        excel_data = create_excel_document(
            doc_type=doc_type,
            document_no=document_no,
            issue_date=str(issue_date),
            due_date=str(due_date),
            customer=customer,
            subject=subject,
            items=items,
            totals=totals,
            note=note,
        )

        st.success(f"{doc_type}を作成しました。帳票番号: {document_no}")

        file_name = f"{document_no}_{doc_type}.xlsx"

        st.download_button(
            label="Excelファイルをダウンロード",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

def load_customer_file(uploaded_file) -> pd.DataFrame:
    """
    顧客情報のCSVまたはExcelファイルを読み込む。
    CSVはUTF-8-SIGを優先し、失敗した場合はCP932で読み込む。
    """
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding="cp932")

    if file_name.endswith((".xlsx", ".xls")):
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file)

    raise ValueError("CSVまたはExcelファイルをアップロードしてください。")


def convert_customer_dataframe(df: pd.DataFrame) -> list[dict]:
    """
    アップロードされた顧客データをDB登録用の形式に変換する。
    """
    column_mapping = {
        "会社名": "company_name",
        "郵便番号": "postal_code",
        "住所": "address",
        "担当者名": "contact_name",
        "メールアドレス": "email",
        "電話番号": "phone",
    }

    required_columns = ["会社名"]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"必須列が不足しています: {missing_columns}")

    converted_df = df.rename(columns=column_mapping)

    for column in [
        "company_name",
        "postal_code",
        "address",
        "contact_name",
        "email",
        "phone",
    ]:
        if column not in converted_df.columns:
            converted_df[column] = ""

    converted_df = converted_df[
        [
            "company_name",
            "postal_code",
            "address",
            "contact_name",
            "email",
            "phone",
        ]
    ]

    converted_df = converted_df.fillna("")

    customers = converted_df.to_dict(orient="records")

    return customers

def show_history():
    st.subheader("作成履歴")

    documents = get_documents()

    if not documents:
        st.info("まだ作成履歴はありません。")
        return

    df = pd.DataFrame(documents)

    display_columns = [
        "id",
        "doc_type",
        "document_no",
        "company_name",
        "issue_date",
        "due_date",
        "subject",
        "subtotal",
        "tax",
        "total",
        "created_at",
    ]

    st.dataframe(df[display_columns], use_container_width=True)


if __name__ == "__main__":
    main()