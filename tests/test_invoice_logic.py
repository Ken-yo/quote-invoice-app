from invoice_logic import calculate_totals, create_document_no


def test_calculate_totals_with_tax():
    items = [
        {
            "name": "要件定義",
            "quantity": 1,
            "unit_price": 50000,
        },
        {
            "name": "画面実装",
            "quantity": 2,
            "unit_price": 80000,
        },
    ]

    result = calculate_totals(items, 0.10)

    assert result["subtotal"] == 210000
    assert result["tax"] == 21000
    assert result["total"] == 231000


def test_create_document_no_for_quote():
    result = create_document_no("見積書", 1)

    assert result == "QUO-00001"


def test_create_document_no_for_invoice():
    result = create_document_no("請求書", 25)

    assert result == "INV-00025"