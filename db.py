import sqlite3
from pathlib import Path
from typing import Dict, List, Optional


DB_PATH = Path("data/app.db")


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                postal_code TEXT,
                address TEXT,
                contact_name TEXT,
                email TEXT,
                phone TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_type TEXT NOT NULL,
                document_no TEXT,
                customer_id INTEGER NOT NULL,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                subject TEXT,
                subtotal INTEGER NOT NULL,
                tax INTEGER NOT NULL,
                total INTEGER NOT NULL,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            )
            """
        )

        conn.commit()


def add_customer(
    company_name: str,
    postal_code: str,
    address: str,
    contact_name: str,
    email: str,
    phone: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO customers (
                company_name,
                postal_code,
                address,
                contact_name,
                email,
                phone
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                company_name,
                postal_code,
                address,
                contact_name,
                email,
                phone,
            ),
        )

        conn.commit()
        return int(cursor.lastrowid)


def get_customers() -> List[Dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                company_name,
                postal_code,
                address,
                contact_name,
                email,
                phone
            FROM customers
            ORDER BY id DESC
            """
        )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_customer(customer_id: int) -> Optional[Dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                id,
                company_name,
                postal_code,
                address,
                contact_name,
                email,
                phone
            FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        )

        row = cursor.fetchone()
        return dict(row) if row else None


def add_document(
    doc_type: str,
    document_no: str,
    customer_id: int,
    issue_date: str,
    due_date: str,
    subject: str,
    items: List[Dict],
    subtotal: int,
    tax: int,
    total: int,
    note: str,
) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO documents (
                doc_type,
                document_no,
                customer_id,
                issue_date,
                due_date,
                subject,
                subtotal,
                tax,
                total,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_type,
                document_no,
                customer_id,
                issue_date,
                due_date,
                subject,
                subtotal,
                tax,
                total,
                note,
            ),
        )

        document_id = int(cursor.lastrowid)

        for item in items:
            quantity = int(item["quantity"])
            unit_price = int(item["unit_price"])
            amount = quantity * unit_price

            cursor.execute(
                """
                INSERT INTO document_items (
                    document_id,
                    name,
                    quantity,
                    unit_price,
                    amount
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    item["name"],
                    quantity,
                    unit_price,
                    amount,
                ),
            )

        conn.commit()
        return document_id


def update_document_no(document_id: int, document_no: str):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE documents
            SET document_no = ?
            WHERE id = ?
            """,
            (document_no, document_id),
        )

        conn.commit()


def get_documents() -> List[Dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                documents.id,
                documents.doc_type,
                documents.document_no,
                documents.issue_date,
                documents.due_date,
                documents.subject,
                documents.subtotal,
                documents.tax,
                documents.total,
                documents.created_at,
                customers.company_name
            FROM documents
            JOIN customers
                ON documents.customer_id = customers.id
            ORDER BY documents.id DESC
            """
        )

        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
def add_customers_bulk(customers: List[Dict]) -> Dict[str, int]:
    """
    顧客を一括登録する。
    会社名が既に登録済みの場合はスキップする。
    """
    inserted_count = 0
    skipped_count = 0

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT company_name FROM customers")
        existing_company_names = {
            row["company_name"] for row in cursor.fetchall()
        }

        for customer in customers:
            company_name = customer.get("company_name", "").strip()

            if not company_name:
                skipped_count += 1
                continue

            if company_name in existing_company_names:
                skipped_count += 1
                continue

            cursor.execute(
                """
                INSERT INTO customers (
                    company_name,
                    postal_code,
                    address,
                    contact_name,
                    email,
                    phone
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    company_name,
                    customer.get("postal_code", ""),
                    customer.get("address", ""),
                    customer.get("contact_name", ""),
                    customer.get("email", ""),
                    customer.get("phone", ""),
                ),
            )

            existing_company_names.add(company_name)
            inserted_count += 1

        conn.commit()

    return {
        "inserted_count": inserted_count,
        "skipped_count": skipped_count,
    }