import os
import qrcode
import stripe
import boto3
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
import mercadopago
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from boto3.dynamodb.conditions import Key
import random
import string

# Configurações iniciais
app = Flask(__name__)

# Configure o SDK do Mercado Pago
mp = mercadopago.SDK("APP_USR-6523172338846242-100514-afc9490970db73cf999cadf640593b3e-60830907")
#mp = mercadopago.SDK("APP_USR-7788212792459286-100515-877d8d26d1cb62eb816d39854668fa8b-2022910974")  # teste
# Configuração do DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Tabela DynamoDB
table_name = 'CoupleTable'
table = dynamodb.Table(table_name)

# Função para enviar e-mail
def send_email(to_address, subject, body):
    client = boto3.client('ses', region_name='us-east-1')  # Substitua pela sua região
    response = client.send_email(
        Source='contato@qrcodelove.me',  # Substitua pelo seu e-mail
        Destination={
            'ToAddresses': [to_address],
            'BccAddresses': ['marciosferreira@yahoo.com.br'],
        },
        Message={
            'Subject': {
                'Data': subject,
            },
            'Body': {
                'Html': {
                    'Data': body,
                },
            },
        }
    )
    return response

@app.route('/delete_old_pages', methods=['GET', 'POST'])
def delete_old_pages():
    try:
        # Calcula a data de 90 dias atrás
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)

        # Consulta as páginas antigas
        response = table.scan()
        old_pages = [item for item in response['Items'] if datetime.strptime(item['created_at'], '%Y-%m-%dT%H:%M:%S') < ninety_days_ago]

        for page in old_pages:
            table.delete_item(Key={'id': page['id']})

        return "Páginas com mais de 90 dias foram deletadas com sucesso!", 200
    except Exception as e:
        return f"Erro ao deletar páginas antigas: {e}", 500

@app.route('/deletar', methods=['GET', 'POST'])
def deletar_pagina():
    if request.method == 'GET':
        # Renderizar o formulário de deleção
        return render_template('deletar.html')

    elif request.method == 'POST':
        email = request.form['email']
        code = request.form['code']

        # Procurar o casal no DynamoDB pelo email e código da página
        response = table.scan(
            FilterExpression=Key('email').eq(email) & Key('page_url').eq(code)
        )
        items = response.get('Items', [])

        if items:
            try:
                table.delete_item(Key={'email': items[0]['email'], 'page_url': items[0]['page_url']})
                return "Página deletada com sucesso!"
            except Exception as e:
                return f"Erro ao deletar a página: {e}", 500
        else:
            return "Página não encontrada. Verifique o email e o código informados.", 404

@app.route('/create', methods=['POST'])
def create_couple_page():
    try:
        # Capturando os valores do formulário
        name1 = request.form['name1']
        name2 = request.form['name2']
        event_date = request.form['event_date']
        email = request.form['email']
        event_description = request.form['event_description']
        optional_message = request.form.get('optional_message')  # Captura a mensagem opcional

        # Gera um código alfanumérico único para a URL da página
        unique_code = generate_unique_code()
        while table.scan(FilterExpression=Key('page_url').eq(unique_code))['Count'] > 0:
            unique_code = generate_unique_code()

        # Cria o casal e salva no DynamoDB
        new_couple = {
            #'id': str(random.randint(100000, 999999)),
            'name1': name1,
            'name2': name2,
            'event_date': event_date,
            'event_description': event_description,
            'page_url': unique_code,
            'optional_message': optional_message,
            'email': email,
            'paid': False,
            'created_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        }
        table.put_item(Item=new_couple)

        # Gera o link para a página recém-criada
        url = url_for('couple_page', page_url=new_couple['page_url'], _external=True)

        # Gerar QR Code e salvar (certifique-se que couple_id seja convertido)
        generate_qr_code(url, unique_code)

        # Corpo do e-mail
        email_subject = "Sua página foi criada!"
        email_body = f"""
        Olá {name1} e {name2},<br><br>
        Sua página foi criada com sucesso! Acesse-a aqui: <a href='{url}'>{url}</a>.<br><br>
        Se quiser deletar sua página, acesse o link abaixo e insira seu email e o código da página: {unique_code}<br>
        <a href='https://qrcodelove.me/deletar'>https://qrcodelove.me/deletar</a> <br>
        Ou ela será deletada automaticamente em 90 dias.<br><br>
        Atenciosamente,<br>
        Equipe de Suporte
        """

        # Enviar e-mail (opcional)
        send_email(email, email_subject, email_body)

        # Redirecionar diretamente para a página do casal
        return redirect(url_for('couple_page', page_url=new_couple['page_url']))

    except Exception as e:
        print(f"Erro ao criar a página do casal: {e}")
        return f"Erro ao criar a página do casal: {e}", 400

# Função para gerar um código único de letras e números
def generate_unique_code(length=8):
    characters = string.ascii_letters + string.digits  # Letras e números
    return ''.join(random.choice(characters) for _ in range(length))

# Rota para página inicial
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/couple_page/<string:page_url>')
def couple_page(page_url):
    response = table.scan(FilterExpression=Key('page_url').eq(page_url))
    items = response.get('Items', [])

    if not items:
        # Retorna uma página personalizada informando que a página não existe
        return render_template('not_found.html'), 404

    couple = items[0]

    # Calcula o tempo desde o evento
    event_datetime = datetime.strptime(couple['event_date'], '%Y-%m-%d')
    now = datetime.now()
    time_diff = now - event_datetime
    years = time_diff.days // 365
    months = (time_diff.days % 365) // 30
    days = (time_diff.days % 365) % 30
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Verifica se o pagamento foi realizado
    #qr_code_path = f'static/qrcodes/{couple["id"]}.png'
    qr_code_path = f'static/qrcodes/{couple["page_url"]}.png'
    if couple['paid']:
        return render_template('couple_page.html', couple=couple, payment_pending=False, years=years, months=months, days=days, hours=hours, minutes=minutes, seconds=seconds, qr_code_path=qr_code_path)
    else:
        return render_template('couple_page.html', couple=couple, payment_pending=True, years=years, months=months, days=days, hours=hours, minutes=minutes, seconds=seconds, qr_code_path=qr_code_path)


# Rota de pagamento (Mercado Pago)
@app.route('/pay/<string:id>', methods=['POST'])
def pay(id):
    #couple = Couple.query.get_or_404(id)
    #response = table.get_item(Key={'id': str(id)})
    response = table.scan(FilterExpression=Key('page_url').eq(id))
    items = response.get('Items', [])
    if not items:
        return 'Página não encontrada', 404
    couple = items[0]

    #couple = response.get('Item')
    if not couple:
        return 'Página não encontrada', 404


    # Capturar o email do casal
    email = couple['email']


    # Criar a preferência de pagamento
    preference_data = {
        "items": [
            {
                "title": "Página contador sem anúncios (90 dias)",
                "quantity": 1,
                "currency_id": "BRL",  # Moeda BRL para real brasileiro
                "unit_price": 10.00  # Valor do pagamento
            }
        ],
        "payer": {
            "email": email
        },
        "back_urls": {
        "success": url_for('payment_success', page_url=couple['page_url'], _external=True),
        "failure": url_for('couple_page', page_url=couple['page_url'], _external=True),
        "pending": url_for('couple_page', page_url=couple['page_url'], _external=True)

        },
        "auto_return": "approved",
        "notification_url": "https://qrcodelove.me/webhook",  # Webhook para fallback
        "metadata": {
            #"couple_id": couple.id  # Incluindo o ID do casal como metadado
            "couple_id": couple['page_url']  # Incluindo a URL do casal como metadado, já que não temos mais `id`
        }
    }

    try:
        # Criar preferência de pagamento
        preference_response = mp.preference().create(preference_data)

        # Verifica se a resposta contém a chave esperada
        if "response" in preference_response and "id" in preference_response["response"]:
            preference_id = preference_response["response"]["id"]

            # Redirecionar o cliente para o Mercado Pago Checkout
            return redirect(preference_response["response"]["init_point"], code=303)
        else:
            return "Erro ao criar preferência de pagamento", 400

    except Exception as e:
        print(f"Erro na criação de preferência de pagamento: {e}")
        return "Erro ao processar o pagamento", 500

# Rota de sucesso do pagamento (Verificação ativa)
@app.route('/payment_success/<string:page_url>')
def payment_success(page_url):
    #couple = Couple.query.filter_by(page_url=page_url).first_or_404()
    response = table.scan(FilterExpression=Key('page_url').eq(page_url))
    items = response.get('Items', [])
    if not items:
        return 'Página não encontrada', 404
    couple = items[0]

    # Verifica o status do pagamento diretamente na API do Mercado Pago
    payment_id = request.args.get('payment_id')
    payment_info = mp.payment().get(payment_id)

    # Se o status for aprovado, marque o casal como pago
    if payment_info['response']['status'] == 'approved':
        #couple.paid = True
        #db.session.commit()
        couple['paid'] = True
        table.put_item(Item=couple)
  

    #return redirect(url_for('couple_page', page_url=couple.page_url))
    return redirect(url_for('couple_page', page_url=couple['page_url']))

@app.route('/webhook', methods=['POST'])
def webhook():
    notification_data = request.json

    if notification_data.get('type') == 'payment':
        payment_id = notification_data.get('data', {}).get('id')
        payment_info = mp.payment().get(payment_id)

        if payment_info['response']['status'] == 'approved':
            couple_id = payment_info['response']['metadata']['couple_id']
            #couple = Couple.query.get_or_404(couple_id)
            response = table.scan(FilterExpression=Key('page_url').eq(couple_id))
            items = response.get('Items', [])
            if not items:
                return 'Página não encontrada', 404
            couple = items[0]

            couple['paid'] = True
            couple['created_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
            table.put_item(Item=couple)

    return jsonify({"status": "success"}), 200









# Função para gerar QR code com a URL
def generate_qr_code(url, unique_code):
    # Gerar o QR code
    img = qrcode.make(url)

    # Garantir que o diretório de destino exista
    os.makedirs('static/qrcodes', exist_ok=True)

    # Salvar a imagem com o QR code
    img.save(f'static/qrcodes/{unique_code}.png')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
