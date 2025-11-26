import argparse
import json
import sys
import requests


def build_payload(event: str = "PAYMENT_CREATED", status: str = "PENDING",
                   external_reference: str = "ZfkBLrBs", value: float = 9.90):
    """
    Constrói o payload com base no JSON compartilhado, permitindo ajustar
    event/status/externalReference/value via argumentos.
    """
    return {
        "id": "evt_05b708f961d739ea7eba7e4db318f621&1136995174",
        "event": event,
        "dateCreated": "2025-11-26 17:37:55",
        "payment": {
            "object": "payment",
            "id": "pay_3vi5rk4zph8d6nph",
            "dateCreated": "2025-11-26",
            "customer": "cus_000150041968",
            "checkoutSession": None,
            "paymentLink": "32p7tghzgj52wcr7",
            "value": float(value),
            "netValue": 7.91,
            "originalValue": None,
            "interestValue": None,
            "description": "Extensão de validade: PLAN=30d",
            "billingType": "PIX",
            "pixTransaction": None,
            "status": status,
            "dueDate": "2025-11-27",
            "originalDueDate": "2025-11-27",
            "paymentDate": None,
            "clientPaymentDate": None,
            "installmentNumber": None,
            # Mantém a URL conforme o texto compartilhado (sem remover espaços/backticks)
            "invoiceUrl": " https://www.asaas.com/i/3vi5rk4zph8d6nph ",
            "invoiceNumber": "687632750",
            "externalReference": external_reference,
            "deleted": False,
            "anticipated": False,
            "anticipable": False,
            "creditDate": None,
            "estimatedCreditDate": None,
            "transactionReceiptUrl": None,
            "nossoNumero": None,
            "bankSlipUrl": None,
            "lastInvoiceViewedDate": None,
            "lastBankSlipViewedDate": None,
            "discount": {
                "value": 0,
                "limitDate": None,
                "dueDateLimitDays": 0,
                "type": "FIXED"
            },
            "fine": {
                "value": 0,
                "type": "FIXED"
            },
            "interest": {
                "value": 0,
                "type": "PERCENTAGE"
            },
            "postalService": False,
            "escrow": None,
            "refunds": None
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Enviar webhook de teste para o endpoint /webhook")
    parser.add_argument("--url", default="http://localhost:8000/webhook",
                        help="URL completa do webhook (ex.: http://localhost:8000/webhook ou https://meueventoespecial.com.br/webhook)")
    parser.add_argument("--event", default="PAYMENT_CREATED",
                        choices=["PAYMENT_CREATED", "PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"], help="Evento Asaas a simular")
    parser.add_argument("--status", default="PENDING",
                        choices=["PENDING", "RECEIVED", "CONFIRMED"], help="Status do pagamento")
    parser.add_argument("--ref", "--external_reference", dest="ref", default="ZfkBLrBs",
                        help="externalReference (page_url) a ser enviada no payload")
    parser.add_argument("--value", type=float, default=9.90, help="Valor do pagamento")
    args = parser.parse_args()

    payload = build_payload(event=args.event, status=args.status,
                            external_reference=args.ref, value=args.value)

    headers = {
        "Content-Type": "application/json"
    }

    try:
        print("POST", args.url)
        print("Payload:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        resp = requests.post(args.url, headers=headers, data=json.dumps(payload))
        print("Status:", resp.status_code)
        print("Headers:", dict(resp.headers))
        # Evita quebrar se resposta não for JSON
        try:
            print("Body (JSON):", json.dumps(resp.json(), ensure_ascii=False, indent=2))
        except Exception:
            print("Body (text):", resp.text[:1000])
    except Exception as e:
        print("Falha ao enviar webhook:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
