from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
import io
from PIL import Image
from urllib.parse import urlparse, parse_qs
from werkzeug.utils import secure_filename
import os
import qrcode
import stripe
import boto3
import time
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    flash,
    send_from_directory,
    abort,
)
import sys

# No início do seu arquivo app.py
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis do arquivo .env

# Agora você pode acessá-las com os.getenv
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# No início do arquivo, adicione esta linha às configurações
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
# import mercadopago
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from boto3.dynamodb.conditions import Key
import random
import string
import os
from datetime import datetime
import pytz

# Defina o fuso horário desejado
timezone = pytz.timezone("America/Manaus")

# Configurações iniciais
app = Flask(__name__)

region_name = ("us-east-1",)
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
# print(aws_secret_access_key)
# print(aws_access_key_id)

# app.secret_key = 'sua_chave_seHGcreta_aqui'  # Troque por uma string aleatória e segura
app.secret_key = os.getenv("FLASK_SECRET_KEY", "uma_fchave_secreta_fixa")


# Configure o SDK do Mercado Pago
# production
# mp = mercadopago.SDK("APP_USR-7788212792459286-100515-877d8d26d1cb62eb816d39854668fa8b-2022910974")  # teste
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


# Configuração do DynamoDB
# dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
dynamodb = boto3.resource(
    "dynamodb",
    region_name="us-east-1",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
)
# Tabela DynamoDB
table_name = "CoupleTable"
table = dynamodb.Table(table_name)

# Configurações do S3
S3_BUCKET = "qrcodelove-pictures"
S3_REGION = "us-east-1"
# aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
# aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')

# Inicializando o cliente S3
s3_client = boto3.client(
    "s3",
    region_name=S3_REGION,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
)


# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# Usuário de exemplo (somente você)
class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


def resize_image_if_needed(image, max_width=1000):
    """Redimensiona a imagem se a largura exceder o limite permitido."""
    img = Image.open(image)
    width, height = img.size

    # Redimensionar se a largura for maior que o limite
    if width > max_width:
        # Calcula a nova altura mantendo a proporção
        new_height = int(max_width * height / width)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Salva a imagem redimensionada em um objeto de memória
        img_io = io.BytesIO()
        img.save(img_io, format="PNG")  # Salvar como PNG
        img_io.seek(0)  # Voltar ao início do objeto BytesIO
        return img_io
    else:
        # Se não for necessário redimensionar, retorna a imagem original
        image.seek(0)  # Certifica-se de que a imagem esteja no início para o upload
        return image


# Este decorador adiciona headers a todas as respostas
@app.after_request
def add_cache_control(response):
    if request.path.startswith("/static/"):
        # Define o header Cache-Control para arquivos estáticos (como CSS, JS, imagens)
        response.headers["Cache-Control"] = (
            "public, max-age=31536000"  # Cache por 1 ano
        )
    elif request.path == "/":
        # Define o header Cache-Control para a homepage, impedindo o cache
        # response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers["Cache-Control"] = (
            "public, max-age=31536000"  # Cache por 1 ano
        )
    elif request.path.startswith("/couple_page/"):
        # Define o header Cache-Control para páginas de usuário que não mudam
        # response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache por 1 ano
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate, max-age=0"
        )
    else:
        # Define o header Cache-Control para não cachear páginas internas
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate, max-age=0"
        )
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Usuário fixo (somente você)
        if username == "marcioverde" and check_password_hash(
            generate_password_hash("cpfl2002"), password
        ):
            user = User(1)
            login_user(user)
            return redirect(
                url_for("list_dynamo_items")
            )  # Redireciona para a página de itens após login
        else:
            flash("Login ou senha incorretos.")
            return redirect(
                url_for("login")
            )  # Se falhar, redireciona de volta para a página de login

    # Se for um GET, renderiza o template de login
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout realizado com sucesso.")
    return redirect(url_for("login"))


@app.route("/items/edit/<email>/<page_url>", methods=["GET", "POST"])
@login_required
def edit_user(email, page_url):
    try:
        # Pegue o item do DynamoDB usando a chave composta por 'email' e 'page_url'
        response = table.get_item(Key={"email": email, "page_url": page_url})
        user = response.get("Item")

        if not user:
            flash("Usuário não encontrado.")
            return redirect(url_for("list_dynamo_items"))

        if request.method == "POST":
            # Atualize os campos do usuário com os dados do formulário
            user["name1"] = request.form["name1"]
            user["name2"] = request.form["name2"]
            user["event_description"] = request.form["event_description"]
            user["event_date"] = request.form["event_date"]
            user["event_time"] = request.form["event_time"]
            user["email"] = request.form["email"]
            user["optional_message"] = request.form["optional_message"]
            user["video_id"] = request.form["video_id"]

            # Obtenha a nova data e hora do formulário
            new_date = request.form["created_at"]  # 'YYYY-MM-DD'
            new_time = request.form["created_time"]  # 'HH:MM'

            # Combine a nova data e hora no formato correto
            user["created_at"] = (
                f"{new_date}T{new_time}:00.000Z"  # Formato completo de timestamp
            )

            # Captura o valor da checkbox (se marcada, é 'on', caso contrário não está presente)
            user["paid"] = (
                "paid" in request.form
            )  # retorna True se a checkbox estiver marcada, senão False
            # Adicione mais campos conforme necessário

            # Atualizar o item no DynamoDB
            table.put_item(Item=user)

            # Após salvar, redireciona para a lista de itens
            return redirect(url_for("list_dynamo_items"))

        # Renderizar o formulário de edição com os dados do usuário
        return render_template("edit_user.html", user=user)

    except Exception as e:
        flash(f"Erro ao editar o usuário: {e}")
        return redirect(url_for("list_dynamo_items"))


# Página protegida para listar os itens do DynamoDB
@app.route("/items")
@login_required  # Protege a rota para exigir login
def list_dynamo_items():
    try:
        # Recupera todos os itens da tabela DynamoDB
        response = table.scan()
        items = response.get("Items", [])

        if items:
            return render_template("items.html", items=items)
        else:
            flash("Nenhum item encontrado na tabela.")
            # Em vez de redirecionar, renderize a página com a lista vazia
            return render_template("items.html", items=[])
    except Exception as e:
        flash(f"Erro ao recuperar itens do DynamoDB: {e}")
        return redirect(url_for("login"))


# Função para enviar e-mail com anexo
def send_email_with_qr_attachment(
    to_address, subject, body, qr_image_bytes, filename="qrcode.png"
):
    client = boto3.client("ses", region_name="us-east-1")

    # Cria a mensagem MIME
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = "contato@qrcodelove.me"
    msg["To"] = to_address

    # Corpo do e-mail em HTML
    body_part = MIMEText(body, "html")
    msg.attach(body_part)

    # Verifica se há imagem para anexar
    if qr_image_bytes:
        part = MIMEApplication(qr_image_bytes.read())
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    # Converte a mensagem para string
    raw_msg = msg.as_string()

    # Envia o e-mail com cópia oculta
    response = client.send_raw_email(
        Source="contato@qrcodelove.me",
        Destinations=[to_address],  # destinatário principal e BCC
        RawMessage={"Data": raw_msg},
    )

    return response


# Função para enviar e-mail
def send_email(to_address, subject, body):
    client = boto3.client("ses", region_name="us-east-1")  # Substitua pela sua região
    response = client.send_email(
        Source="contato@qrcodelove.me",  # Substitua pelo seu e-mail
        Destination={
            "ToAddresses": [to_address],
        },
        Message={
            "Subject": {
                "Data": subject,
            },
            "Body": {
                "Html": {
                    "Data": body,
                },
            },
        },
    )
    return response


from datetime import datetime

from datetime import datetime, timedelta
import pytz
from flask import request, jsonify

from datetime import datetime, timedelta
import pytz
from flask import request, jsonify


@app.route("/delete_old_pages", methods=["GET", "POST"])
def delete_old_pages():
    try:
        # Fuso horário de Manaus
        timezone = pytz.timezone("America/Manaus")

        # Consulta as páginas
        response = table.scan()
        old_pages = []

        # Converte a data usando o formato padronizado
        for item in response["Items"]:
            created_at = item.get("created_at")
            is_paid = item.get("paid", False)  # Verifica se o pagamento foi realizado

            if created_at:
                try:
                    # Formato padronizado com milissegundos e sufixo Z
                    created_at_date = datetime.strptime(
                        created_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                    # Ajustar o horário UTC para o fuso de Manaus
                    created_at_date = created_at_date.replace(
                        tzinfo=pytz.utc
                    ).astimezone(timezone)
                except ValueError:
                    # Caso a data não esteja no formato esperado (pode não ser necessário se tudo estiver padronizado)
                    continue

                # Definir o tempo limite para deleção
                if is_paid:
                    # Páginas pagas podem ser deletadas após 90 dias
                    time_limit = created_at_date + timedelta(days=30)
                else:
                    # Páginas não pagas podem ser deletadas após 24 horas
                    time_limit = created_at_date + timedelta(hours=2)

                # Verifica se o tempo limite já passou
                if datetime.now(timezone) > time_limit:
                    old_pages.append(item)

        # Verifica se há páginas antigas para deletar
        if not old_pages:
            return "Nenhuma página antiga para deletar.", 200

        # Deletar os itens antigos e suas imagens no S3
        for page in old_pages:
            primary_key = {
                "email": page[
                    "email"
                ],  # Ajuste conforme o nome da chave primária da sua tabela
                "page_url": page["page_url"],  # Ajuste conforme necessário
            }
            table.delete_item(Key=primary_key)

            # Deletar o folder no S3 (imagens do casal)
            folder_key = f'pictures/{page["page_url"]}/'
            try:
                objects_to_delete = s3_client.list_objects_v2(
                    Bucket=S3_BUCKET, Prefix=folder_key
                )
                delete_keys = [
                    {"Key": obj["Key"]} for obj in objects_to_delete.get("Contents", [])
                ]
                if delete_keys:
                    s3_client.delete_objects(
                        Bucket=S3_BUCKET, Delete={"Objects": delete_keys}
                    )
                print(f"Folder {folder_key} deletado do S3.")
            except Exception as e:
                print(f"Erro ao deletar o folder {folder_key} do S3: {e}")

            # Deletar o QRCode no S3
            qrcode_key = f'qrcodes/{page["page_url"]}.png'
            try:
                s3_client.delete_object(Bucket=S3_BUCKET, Key=qrcode_key)
                print(f"QRCode {qrcode_key} deletado do S3.")
            except Exception as e:
                print(f"Erro ao deletar o QRCode {qrcode_key} do S3: {e}")

        return "Páginas antigas foram deletadas com sucesso!", 200
    except Exception as e:
        return f"Erro ao deletar páginas antigas: {e}", 500


# essa rota deleta usuarios na pa´gina de login
@app.route("/delete/<string:email>/<string:page_url>", methods=["POST"])
@login_required  # Protege a rota para exigir login
def delete_item(email, page_url):
    try:
        # Usar `email` e `page_url` como chaves compostas para deletar o item no DynamoDB
        response = table.delete_item(Key={"email": email, "page_url": page_url})
        flash(f"Item com URL {page_url} foi deletado com sucesso.")
    except Exception as e:
        flash(f"Erro ao deletar item: {e}")

    # Deletar o folder no S3 (imagens do casal)
    folder_key = f"pictures/{page_url}"
    try:
        objects_to_delete = s3_client.list_objects_v2(
            Bucket=S3_BUCKET, Prefix=folder_key
        )
        delete_keys = [
            {"Key": obj["Key"]} for obj in objects_to_delete.get("Contents", [])
        ]
        if delete_keys:
            s3_client.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": delete_keys})
        print(f"Folder {folder_key} deletado do S3.")
    except Exception as e:
        print(f"Erro ao deletar o folder {folder_key} do S3: {e}")
        flash(
            f"Erro ao deletar o folder {folder_key} no S3. Por favor, tente novamente.",
            "error",
        )

    # Deletar o QRCode no S3
    qrcode_key = f"qrcodes/{page_url}.png"
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=qrcode_key)
        print(f"QRCode {qrcode_key} deletado do S3.")
    except Exception as e:
        print(f"Erro ao deletar o QRCode {qrcode_key} do S3: {e}")
        flash(
            f"Erro ao deletar o QRCode {qrcode_key} no S3. Por favor, tente novamente.",
            "error",
        )

    return redirect(url_for("list_dynamo_items"))


# essa rota é para o proprio usuario deletar sua página
@app.route("/deletar", methods=["GET", "POST"])
def deletar_pagina():
    if request.method == "GET":
        # Renderizar o formulário de deleção
        return render_template("deletar.html")

    elif request.method == "POST":
        email = request.form["email"]
        code = request.form["code"]

        # Procurar o casal no DynamoDB pelo email e código da página
        response = table.scan(
            FilterExpression=Key("email").eq(email) & Key("page_url").eq(code)
        )
        items = response.get("Items", [])

        if items:
            try:
                # Deletar o item do DynamoDB
                table.delete_item(
                    Key={"email": items[0]["email"], "page_url": items[0]["page_url"]}
                )

                # Deletar o folder no S3 (imagens do casal)
                folder_key = f"pictures/{code}/"
                try:
                    objects_to_delete = s3_client.list_objects_v2(
                        Bucket=S3_BUCKET, Prefix=folder_key
                    )
                    delete_keys = [
                        {"Key": obj["Key"]}
                        for obj in objects_to_delete.get("Contents", [])
                    ]
                    if delete_keys:
                        s3_client.delete_objects(
                            Bucket=S3_BUCKET, Delete={"Objects": delete_keys}
                        )
                    print(f"Folder {folder_key} deletado do S3.")
                except Exception as e:
                    print(f"Erro ao deletar o folder {folder_key} do S3: {e}")
                    flash(
                        f"Erro ao deletar o folder {folder_key} no S3. Por favor, tente novamente.",
                        "error",
                    )

                # Deletar o QRCode no S3
                qrcode_key = f"qrcodes/{code}.png"
                try:
                    s3_client.delete_object(Bucket=S3_BUCKET, Key=qrcode_key)
                    print(f"QRCode {qrcode_key} deletado do S3.")
                except Exception as e:
                    print(f"Erro ao deletar o QRCode {qrcode_key} do S3: {e}")
                    flash(
                        f"Erro ao deletar o QRCode {qrcode_key} no S3. Por favor, tente novamente.",
                        "error",
                    )

                flash("Página deletada com sucesso!", "success")
                return redirect(url_for("deletar_pagina"))
            except Exception as e:
                flash(f"Erro ao deletar a página: {e}", "error")
                return redirect(url_for("deletar_pagina"))
        else:
            flash(
                "Página não encontrada. Verifique o email e o código informados.",
                "error",
            )
            return redirect(url_for("deletar_pagina"))


# Pasta de upload de imagens
UPLOAD_FOLDER = "static/pictures/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Função para verificar a extensão do arquivo
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_video_id(youtube_url):
    # Verifica se é uma URL completa com 'v='
    if "v=" in youtube_url:
        return youtube_url.split("v=")[1].split("&")[0]

    # Se for um link curto (https://youtu.be/...), basta pegar o trecho após 'youtu.be/'
    if "youtu.be/" in youtube_url:
        return youtube_url.split("youtu.be/")[1].split("?")[0]

    # Caso não seja um link válido do YouTube
    return None


# @app.route('/create', methods=['GET'])
# def create_form():
# return render_template('index.html')  # Seu template com o formulário


@app.route("/create", methods=["POST"])
def create_couple_page():
    try:
        # Capturando os valores do formulário
        name1 = request.form["name1"]
        name2 = request.form["name2"]
        event_date = request.form["event_date"]
        event_time = request.form["event_time"]
        email = request.form["email"]
        event_description = request.form["event_description"]
        optional_message = request.form.get(
            "optional_message"
        )  # Captura a mensagem opcional
        youtubelink = request.form.get("youtubeLink")

        # Gera um código alfanumérico único para a URL da página
        unique_code = generate_unique_code()

        # Criar a pasta se não existir para guardar imagens de perfil
        # upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], unique_code)
        # if not os.path.exists(upload_folder):
        # os.makedirs(upload_folder)

        # Processa o URL do YouTube para guardar apenas o código do vídeo
        if youtubelink:
            video_id = extract_video_id(youtubelink)
            if not video_id:
                flash("Não parece ser um link de video válido do youtube")
                # return redirect(request.url)
                return render_template("index.html")
        else:
            video_id = None
        # Verificar se há imagens e salvá-las
        images = [
            image for image in request.files.getlist("images") if image.filename != ""
        ]
        if len(images) > 3:
            flash("Você pode enviar no máximo 3 imagens.")
            return redirect(request.url)

        for i, image in enumerate(images):
            if image and allowed_file(image.filename):
                filename = secure_filename(
                    f"{i+1}.png"
                )  # Renomeando as imagens para 1.png, 2.png, 3.png
                s3_key = f"pictures/{unique_code}/{filename}"
                try:
                    # redimensiona se muito grande
                    resized_image = resize_image_if_needed(image)
                    # Enviar imagem ao S3
                    s3_client.upload_fileobj(
                        resized_image, S3_BUCKET, s3_key
                    )  # Torna o arquivo publicamente acessível
                except Exception as e:
                    return str(e), 500
            else:
                flash("Imagens devem estar no formato PNG ou JPEG.")
                return redirect(request.url)

        # Gera um novo código se já existir um igual no DynamoDB
        while table.scan(FilterExpression=Key("page_url").eq(unique_code))["Count"] > 0:
            unique_code = generate_unique_code()

        # Cria o casal e salva no DynamoDB
        new_couple = {
            "name1": name1,
            "name2": name2,
            "event_date": event_date,
            "event_time": event_time,
            "event_description": event_description,
            "page_url": unique_code,
            "optional_message": optional_message,
            "email": email,
            "paid": False,
            "created_at": datetime.now(timezone).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            + "Z",
            "video_id": video_id,
        }
        table.put_item(Item=new_couple)

        # Gera o link para a página recém-criada
        url = url_for("couple_page", page_url=new_couple["page_url"], _external=True)

        # Gerar QR Code e salvar
        qr_image_bytes = generate_qr_code(url, unique_code)
        print("qr")
        print(qr_image_bytes)
        # Corpo do e-mail
        email_subject = "Sua página foi criada!"
        email_body = f"""
        Olá {name1} e {name2},<br><br>
        Sua página foi criada com sucesso e estará ativa por 1 hora pra você testar à vontade! Acesse-a aqui: <a href='{url}'>{url}</a>.<br><br>
        Para estender para 1 mês e ter tempo psuficiente para preparar sua surpesa, acesse o link no final da página e realize o pagamento. O aviso desparecerá após o pagamento.  
        Seu QR Code está anexado neste e-mail.<br><br>
        Se quiser deletar sua página, acesse o link abaixo e insira seu e-mail e o código da página: {unique_code}<br>
        <a href='https://qrcodelove.me/deletar'>https://qrcodelove.me/deletar</a> <br>
        Ou ela será deletada automaticamente em 1 hora (exceto se fizer upgrade para 30 dias).<br><br>
        Atenciosamente,<br>
        Equipe de Suporte
        """
        email_admin = "marciosferreira@yahoo.com.br"
        # Enviar e-mail admin
        send_email(email_admin, email_subject, email_body)
        # envia email cliente com qrcode
        response = send_email_with_qr_attachment(
            email, email_subject, email_body, qr_image_bytes, filename="qrcode.png"
        )
        print("response")
        print(response)
        # Redirecionar diretamente para a página do casal
        return redirect(url_for("couple_page", page_url=new_couple["page_url"]))

    except Exception as e:
        print(f"Erro ao criar a página do casal: {e}")
        return f"Erro ao criar a página do casal: {e}", 400


# Função para gerar um código único de letras e números
def generate_unique_code(length=8):
    characters = string.ascii_letters + string.digits  # Letras e números
    return "".join(random.choice(characters) for _ in range(length))


# Rota para página inicial
@app.route("/")
def index():
    # response = s3_client.list_objects_v2(Bucket='qrcodelove-pictures', Prefix=f'pictures/fC3RJiNx/')
    # print(response)
    # Verificar se há conteúdo no prefixo
    # if 'Contents' in response:
    # Criar uma lista com as chaves dos objetos encontrados
    # images = [obj['Key'] for obj in response['Contents']]
    # print("Objetos encontrados:")
    # for key in images:
    # print(key)
    # else:
    # print("Nenhum objeto encontrado no prefixo especificado.")

    # Verifica se há imagens no diretório e cria a lista de imagens
    # if os.path.exists(image_folder):
    # images = [f'{i}.png' for i in range(1, 4) if os.path.exists(os.path.join(image_folder, f'{i}.png'))]
    # print(images)
    # image_exists = bool(images)
    return render_template("index.html")


import os
from flask import render_template
from datetime import datetime
from boto3.dynamodb.conditions import Key


# from datetime import datetime

from datetime import datetime
import pytz


@app.route("/couple_page/<string:page_url>")
def couple_page(page_url):

    show_payment_link = False

    # Verifica se o marcador "pagar" está presente na URL

    show_payment_link = True

    response = table.scan(FilterExpression=Key("page_url").eq(page_url))
    items = response.get("Items", [])

    if not items:
        # Retorna uma página personalizada informando que a página não existe
        return render_template("not_found.html"), 404

    couple = items[0]
    print("the couple")
    print(couple)

    # Verifica se o campo event_time existe no banco de dados
    event_date_str = couple[
        "event_date"
    ]  # Pega a string da data do evento (ex: '2024-10-19')
    event_time_str = couple.get(
        "event_time", "00:00"
    )  # Pega a hora, ou usa '00:00' se não existir

    # Cria um objeto datetime combinando a data e a hora do evento
    event_datetime_str = f"{event_date_str} {event_time_str}"
    event_datetime = datetime.strptime(event_datetime_str, "%Y-%m-%d %H:%M")

    # Definir o fuso horário de Manaus
    timezone = pytz.timezone("America/Manaus")

    # Ajustar a data do evento para o fuso horário de Manaus
    event_datetime = timezone.localize(event_datetime)

    # Obter a hora atual no fuso horário de Manaus
    now = datetime.now(timezone)

    # Calcula o tempo desde o evento
    time_diff = now - event_datetime
    years = time_diff.days // 365
    months = (time_diff.days % 365) // 30
    days = (time_diff.days % 365) % 30
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Verifica a existência de um vídeo
    has_video = couple.get("video_id") is not None

    # Verifica as imagens disponíveis no diretório S3
    response = s3_client.list_objects_v2(
        Bucket="qrcodelove-pictures", Prefix=f"pictures/{page_url}/"
    )
    print(response)

    if "Contents" in response:
        image_exists = True
        images = [obj["Key"] for obj in response["Contents"]]
        print("Objetos encontrados:")
        for key in images:
            print(key)
    else:
        print("Nenhum objeto encontrado no prefixo especificado.")
        image_exists = False
        images = []

    # Gera o caminho do QR code
    # qr_code_path = f'static/qrcodes/{couple["page_url"]}.png'

    print("payment")
    print(couple["paid"])

    # Renderiza a página com as informações calculadas
    return render_template(
        "couple_page.html",
        has_video=has_video,
        couple=couple,
        payment_pending=couple["paid"],
        years=years,
        months=months,
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        # qr_code_path=qr_code_path,
        images=images,
        image_exists=image_exists,
        show_payment_link=show_payment_link,
    )


import os
import requests
from flask import redirect, url_for

@app.route("/pay/<string:id>", methods=["POST"])
def pay(id):
    response = table.scan(FilterExpression=Key("page_url").eq(id))
    items = response.get("Items", [])
    if not items:
        return "Página não encontrada", 404
    couple = items[0]

    payload = {
        "billingType": "PIX",
        "chargeType": "DETACHED",
        "name": "qrcode love 30 dias",
        "description": "Extensão da duração da página para 30 dias",
        "value": 9.9,
        "dueDateLimitDays": 1,
        "externalReference": couple["page_url"],
        "callback": {
            "successUrl": url_for("payment_success", page_url=couple["page_url"], _external=True)
        },
        "isAddressRequired": False
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": os.getenv("ASAAS_API_KEY")  # ou use string fixa aqui para teste
    }

    try:
        response = requests.post("https://sandbox.asaas.com/api/v3/paymentLinks", json=payload, headers=headers)
        print("Status:", response.status_code)
        print("Response:", response.text)

        if response.status_code != 200:
            return f"Erro ao criar link de pagamento: {response.text}", 500

        data = response.json()
        return redirect(data["url"], code=302)

    except Exception as e:
        print("Erro ao processar pagamento:", e)
        return "Erro interno no servidor", 500


@app.route("/payment_success/<string:page_url>")
def payment_success(page_url):
    return redirect(url_for("couple_page", page_url=page_url))



from datetime import datetime
import pytz
from flask import jsonify, request


@app.route('/webhook', methods=['POST'])
def asaas_webhook():
    body = request.json

    if body.get("event") == "PAYMENT_RECEIVED":
        payment = body.get("payment", {})
        page_url = payment.get("externalReference")

        if not page_url:
            return "Referência externa não encontrada", 400

        response = table.scan(FilterExpression=Key("page_url").eq(page_url))
        items = response.get("Items", [])
        if not items:
            return "Casal não encontrado", 404

        couple = items[0]
        couple["paid"] = True

        from datetime import datetime
        import pytz

        # Timestamp de pagamento
        timezone = pytz.timezone("America/Manaus")
        couple["created_at"] = (
            datetime.now(timezone).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        )

        table.put_item(Item=couple)

        # (opcional) Envio de email de confirmação
        try:
            email_subject = "Pagamento confirmado!"
            email_body = f"""
            Olá {couple['name1']} e {couple['name2']},<br><br>
            Seu pagamento foi confirmado! Sua página ficará ativa por 30 dias.<br>
            Acesse: <a href='{url_for("couple_page", page_url=page_url, _external=True)}'>{url_for("couple_page", page_url=page_url, _external=True)}</a>
            """
            send_email(couple["email"], email_subject, email_body)
        except Exception as e:
            print(f"Erro ao enviar email: {e}")

    return jsonify({"received": True})



# Função para gerar QR code com uma resolução maior e retornar a imagem em bytes
def generate_qr_code(url, unique_code, box_size=20, border=4):
    try:
        # Gerar o QRCode com resolução personalizada
        qr = qrcode.QRCode(
            version=1,  # Controla o tamanho do QRCode. 1 é o menor, aumentando o valor você aumenta a densidade
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # Controla o nível de correção de erro
            box_size=box_size,  # Tamanho de cada caixa (pixel)
            border=border,  # Tamanho da borda
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Gerar a imagem
        img = qr.make_image(fill="black", back_color="white")

        # Salvar a imagem em um objeto BytesIO
        image_bytes = io.BytesIO()
        img.save(image_bytes, format="PNG")  # Salva no formato PNG
        image_bytes.seek(
            0
        )  # Certifique-se de que o ponteiro do BytesIO esteja no início

        # Definir a chave (nome do arquivo) para o S3
        s3_key = f"qrcodes/{unique_code}.png"

        # Criar um novo BytesIO para o upload
        image_bytes_for_s3 = io.BytesIO(
            image_bytes.getvalue()
        )  # Cria um novo BytesIO para o upload
        image_bytes_for_s3.seek(
            0
        )  # Certifique-se de que o ponteiro do BytesIO esteja no início

        # Enviar imagem ao S3
        s3_client.upload_fileobj(image_bytes_for_s3, S3_BUCKET, s3_key)
        print("QR code enviado ao S3 com sucesso.")

        # Reposicionar o ponteiro novamente para o início para garantir que possa ser lido novamente
        image_bytes.seek(0)

        # Retornar o objeto BytesIO para que possa ser anexado no e-mail
        return image_bytes

    except Exception as e:
        print(f"Erro ao enviar o QR code ao S3: {e}")
        return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
