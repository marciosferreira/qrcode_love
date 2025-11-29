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
from PIL import Image, ImageDraw, ImageFont
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
from dotenv import load_dotenv
# Integração condicional com Langfuse (observabilidade)
try:
    from langfuse.openai import openai as LF_OPENAI  # type: ignore
except Exception:
    LF_OPENAI = None
try:
    # SDK moderno da OpenAI
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None  # será verificado em runtime

load_dotenv()
from datetime import datetime, timedelta
from decimal import Decimal
import pytz
from boto3.dynamodb.conditions import Key
import random
import string

# Defina o fuso horário desejado
timezone = pytz.timezone("America/Manaus")

# Configurações iniciais
app = Flask(__name__)

# Injeta IDs de tracking globalmente nos templates
@app.context_processor
def inject_tracking_ids():
    return {
        "GTM_CONTAINER_ID": os.getenv("GTM_CONTAINER_ID"),
        # IDs para Google tag (gtag.js)
        "GOOGLE_TAG_ID": os.getenv("GOOGLE_TAG_ID"),
        "GA_MEASUREMENT_ID": os.getenv("GA_MEASUREMENT_ID"),
        # ID de conversão do Google Ads (opcional, para detecção e remarketing)
        "AW_CONVERSION_ID": os.getenv("AW_CONVERSION_ID"),
    }

# Sanitização de HTML básico para mensagens (permite apenas poucas tags)
from html import escape
from html.parser import HTMLParser
from decimal import Decimal

ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "br", "p", "ul", "ol", "li"}


class SafeHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []

    def handle_starttag(self, tag, attrs):
        if tag in ALLOWED_TAGS:
            if tag == "br":
                self.result.append("<br>")
            else:
                self.result.append(f"<{tag}>")

    def handle_endtag(self, tag):
        if tag in ALLOWED_TAGS and tag != "br":
            self.result.append(f"</{tag}>")

    def handle_data(self, data):
        self.result.append(escape(data))


def sanitize_html(html_text: str) -> str:
    if not html_text:
        return ""
    parser = SafeHTMLParser()
    parser.feed(html_text)
    return "".join(parser.result)

# Utilitário: converter números para Decimal (recursivo) para DynamoDB
def convert_numbers_to_decimal(obj):
    if isinstance(obj, dict):
        return {k: convert_numbers_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_numbers_to_decimal(v) for v in obj]
    if isinstance(obj, float):
        # Usa str para preservar valor exato
        return Decimal(str(obj))
    if isinstance(obj, int):
        return Decimal(obj)
    return obj

# Utilitário: converter Decimal em float para JSON/template
def convert_decimal_to_float(obj):
    if isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimal_to_float(v) for v in obj]
    if isinstance(obj, Decimal):
        # Converte para float para ser serializável no tojson
        return float(obj)
    return obj

region_name = "us-east-1"
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

app.secret_key = os.getenv("FLASK_SECRET_KEY", "uma_chave_secreta_fixa")
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SESS_OPTS = {}


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



# Este decorador adiciona headers a todas as respostas
@app.after_request
def add_cache_control(response):
    if request.path.startswith("/static/"):
        # Define o header Cache-Control para arquivos estáticos (como CSS, JS, imagens)
        # Desabilitando cache para garantir que as alterações sejam refletidas
        response.headers["Cache-Control"] = (
            "no-cache, no-store, must-revalidate"
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
            user["optional_message"] = sanitize_html(request.form.get("optional_message", ""))
            # video_id removido do formulário; manter valor existente se houver
            # user["video_id"] permanece inalterado
            user["counter_mode"] = request.form.get("counter_mode", "since")

            # Obtenha a nova data e hora do formulário
            new_date = request.form["created_at"]  # 'YYYY-MM-DD'
            new_time = request.form["created_time"]  # 'HH:MM'

            # Combine a nova data e hora no formato correto
            user["created_at"] = (
                f"{new_date}T{new_time}:00.000Z"  # Formato completo de timestamp
            )

            # Atualiza expires_at se fornecido (Data/Hora de Expiração)
            exp_date = request.form.get("expires_at")
            exp_time = request.form.get("expires_time")
            if exp_date or exp_time:
                if not exp_date:
                    exp_date = user.get("expires_at", "")[:10] or new_date
                if not exp_time:
                    exp_time = (user.get("expires_at", "")[11:16]) or "00:00"
                user["expires_at"] = f"{exp_date}T{exp_time}:00.000Z"

            # Campos de plano (opcionais)
            user["last_plan_code"] = request.form.get("last_plan_code", user.get("last_plan_code", ""))
            price_str = request.form.get("last_plan_price")
            if price_str is not None and price_str.strip() != "":
                try:
                    normalized = price_str.strip()
                    # Remove possível prefixo de moeda
                    if normalized.startswith("R$"):
                        normalized = normalized.replace("R$", "").strip()
                    # Se houver vírgula, trata como separador decimal e remove pontos como milhares
                    if "," in normalized:
                        normalized = normalized.replace(".", "")
                        normalized = normalized.replace(",", ".")
                    # Usa Decimal para salvar no DynamoDB como número preciso
                    user["last_plan_price"] = Decimal(normalized)
                except Exception as e:
                    print(f"Erro ao converter last_plan_price '{price_str}': {e}")
            lp = request.form.get("last_payment_at")
            if lp:
                # esperado: YYYY-MM-DDTHH:MM
                try:
                    if len(lp) >= 16:
                        user["last_payment_at"] = f"{lp}:00.000Z"
                except Exception:
                    pass

            # Captura o valor da checkbox (se marcada, é 'on', caso contrário não está presente)
            user["paid"] = (
                "paid" in request.form
            )  # retorna True se a checkbox estiver marcada, senão False
            # Adicione mais campos conforme necessário

            # Atualizar o item no DynamoDB
            table.put_item(Item=user)

            # Feedback de sucesso
            try:
                flash("Alterações salvas com sucesso.", "success")
            except Exception:
                pass

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
        # Parâmetros de paginação
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
        # Fixar 10 itens por página
        per_page = 10

        # Recupera todos os itens da tabela DynamoDB
        response = table.scan()
        items = response.get("Items", [])

        # Ordena por data de criação (mais recentes primeiro) se disponível
        def parse_created_at(it):
            created = it.get("created_at")
            if not created:
                return datetime.min
            try:
                # Formato padrão com milissegundos e sufixo Z
                return datetime.strptime(created, "%Y-%m-%dT%H:%M:%S.%fZ")
            except Exception:
                # Tenta um formato sem milissegundos
                try:
                    return datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    return datetime.min

        try:
            items.sort(key=parse_created_at, reverse=True)
        except Exception:
            # Se algo falhar na ordenação, seguimos sem ordenar
            pass

        # Classificação de fase: teste (1h), expirado, liberado
        # Usa horário local configurado (America/Manaus) para evitar marcar
        # como expirado indevidamente quando datas foram gravadas no fuso local
        # porém com sufixo "Z".
        now_local_naive = datetime.now(timezone).replace(tzinfo=None)

        def parse_iso(dt_str):
            if not dt_str:
                return None
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.strptime(dt_str, fmt)
                except Exception:
                    continue
            return None

        for it in items:
            paid = bool(it.get("paid", False))
            exp_dt = parse_iso(it.get("expires_at"))
            created_dt = parse_iso(it.get("created_at"))

            status = "liberado"
            if exp_dt:
                # Comparação baseada no horário local (naive) para coerência com
                # datas gravadas no fuso local.
                if exp_dt <= now_local_naive:
                    status = "expirado"
                else:
                    status = "liberado" if paid else "teste"
            else:
                if not paid:
                    if created_dt:
                        status = "teste" if (created_dt + timedelta(hours=1)) > now_local_naive else "expirado"
                    else:
                        status = "teste"
                else:
                    status = "liberado"

            it["status_phase"] = status

        # Formatação BR das datas para exibição (dd/mm/yyyy HH:MM)
        def format_br(dt):
            if not dt:
                return ""
            try:
                return dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return ""

        for it in items:
            it["created_br"] = format_br(parse_iso(it.get("created_at")))
            it["expires_br"] = format_br(parse_iso(it.get("expires_at")))
            # Evento: combinar event_date (YYYY-MM-DD) + event_time (HH:MM)
            ev_date = it.get("event_date")
            ev_time = it.get("event_time")
            ev_dt = None
            if ev_date and ev_time:
                try:
                    ev_dt = datetime.strptime(f"{ev_date} {ev_time}", "%Y-%m-%d %H:%M")
                except Exception:
                    ev_dt = None
            elif ev_date:
                try:
                    ev_dt = datetime.strptime(ev_date, "%Y-%m-%d")
                except Exception:
                    ev_dt = None
            it["event_br"] = format_br(ev_dt) if ev_dt else (ev_date or "")
            # Último pagamento
            it["last_payment_br"] = format_br(parse_iso(it.get("last_payment_at")))

        total = len(items)
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        if page > total_pages:
            page = total_pages
        start = (page - 1) * per_page
        end = start + per_page
        page_items = items[start:end]

        # Renderiza com contexto de paginação
        return render_template(
            "items.html",
            items=page_items,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        )
    except Exception as e:
        flash(f"Erro ao recuperar itens do DynamoDB: {e}")
        return redirect(url_for("login"))


def _build_system_prompt():
    return (
        "# Sistema de Copiloto para Criação de Página Personalizada\n\n"
        
        "## Produto\n"
        "Plataforma para criar páginas personalizadas com:\n"
        "- Contador de tempo (passado/futuro)\n"
        "- Fotos (até 3)\n"
        "- Vídeo do YouTube\n"
        "- Mensagem especial\n"
        "- QR Code para compartilhar\n\n"
        
        "## Seu Papel\n"
        "Orientar o preenchimento passo a passo do formulário.\n"
        "- O usuário preenche na interface; você valida e orienta.\n"
        "- Você não preenche campos automaticamente pelo chat.\n"
        "- Adapte a linguagem ao tipo de evento (sem viés para casamento).\n\n"
        
        "## Mecânica de Trabalho\n\n"
        
        "### Fonte de verdade\n"
        "- `user_set_fields`: campos confirmados pelo usuário na UI\n"
        "- `form_context`: estado atual do formulário\n"
        "- Valores padrão são apenas placeholders (ignore até confirmação)\n\n"
        
        "### Estrutura de cada resposta\n"
        "0. **Checklist**: NÃO GERAR. O backend insere no início da resposta; apenas copie quando ele vier. Se o backend não enviar, NÃO inclua a seção 'Checklist' em nenhum lugar da resposta. Nunca reconstrua ou repita esse bloco.\n\n"
        
        "1. **Orientação**: 1 frase reconhecendo a intenção + 1 instrução objetiva\n"
        "2. **Sugestões**: máximo 3 opções curtas (quando aplicável)\n"
        "3. **CTA final**: quando tudo estiver [x], mostre \"Clique em 'Criar minha homenagem'\"\n\n"
        
        "## Campos Obrigatórios (ordem de prioridade)\n\n"
        
        "1. **name1**: Nome principal — é o nome do homenageado; nunca presuma que seja o nome de quem está criando a página.\n"
        "2. **event_date**: Data do evento\n"
        "3. **event_time**: Horário\n"
        "4. **counter_mode**: Escolha entre:\n"
        "   - `since` → \"contagem desde\" (evento passado)\n"
        "   - `until` → \"contagem para\" (evento futuro)\n"
        "5. **event_description** OU **custom_event_description**:\n"
        "   - Explique: \"Há opções pré-definidas no seletor OU ative 'Usar frase personalizada' para criar a sua\"\n"
        "   - Instrua: selecionar no dropdown OU marcar checkbox + digitar + confirmar\n"
        "6. **email**: E-mail para receber o link\n\n"
        
        "## Campos Opcionais (não bloqueiam avanço)\n\n"
        
        "**Regra geral**: ofereça 1 vez de forma direta; se negar/ignorar, marque [x] e avance.\n\n"
        
        "- **name2**: \"Quer adicionar Nome 2? (opcional)\"\n"
        "- **optional_message**: \"Quer incluir uma mensagem curta? (opcional)\" → ofereça 2-3 sugestões\n"
        "- **Fotos**: \n"
        "  - Se `photos_count=0` e sem negativa prévia: explique upload\n"
        "  - Se `photos_count < photos_max`: \"Você tem X/Y. Quer adicionar mais? (limite Y)\"\n"
        "  - NUNCA afirme que há fotos quando `photos_count=0`\n"
        "- **Vídeo YouTube**:\n"
        "  - Se `has_video=false` e sem negativa: explique campo `youtubeLink`\n"
        "  - Vídeo padrão na prévia = campo vazio (não considere link incluído)\n"
        "  - Se `has_video=true` mas link não confirmado: pergunte\n"
        "- **effect_type**: `none`, `hearts`, `stars`, `confetti` (default: `none`)\n"
        "- **background_type**: gradientes/texturas (default: `default`)\n"
        "- **text_theme**: claros/escuros/vibrantes (default: `text_theme_pink`)\n\n"
        
        "## Regras Críticas\n\n"
        
        "❌ **Nunca**:\n"
        "- Perguntar dados que não existem no formulário\n"
        "- Afirmar que algo foi preenchido sem confirmação em `user_set_fields`\n"
        "- Propor opcionais antes de confirmar o campo atual e obrigatórios seguintes\n"
        "- Usar adjetivos excessivos ou linguagem floreada\n\n"
        
        "✅ **Sempre**:\n"
        "- Focar em 1 campo por vez\n"
        "- Conectar a intenção do usuário ao próximo campo obrigatório\n"
        "- Instruir: \"Preencha na página e confirme aqui\"\n"
        "- Manter checklist persistente e atualizado\n"
        "- Se o usuário responder \"não\" a uma oferta opcional, considere o opcional como concluído (marque [x]) e não ofereça novamente; persista essa recusa na sessão.\n"
        "- Ao oferecer um opcional, oriente explicitamente: \"Se não quiser, responda 'não'\" (sem distinção de maiúsculas/minúsculas).\n"
        "- Usar Markdown apenas quando ajudar na clareza\n"
    )


@app.route('/api/copilot', methods=['POST'])
def copilot_api():
    try:
        data = request.get_json(force=True) or {}
        user_msg = (data.get('message') or '').strip()
        form_ctx = data.get('form_context') or {}
        label_map = data.get('label_map') or {}
        # Estado atual da UI/DOM (opcional), se o frontend enviar
        # Modo estrito: não considerar estado de UI/DOM enviado pelo frontend
        dom_state = {}
        user_set_fields = set(data.get('user_set_fields') or [])
        # Histórico e sessão (opcionais) enviados pelo frontend
        raw_history = data.get('history') or []
        session_id = (data.get('session_id') or '').strip() or None

        sess_state = SESS_OPTS.get(session_id or '', {'declined': set(), 'pending_optional': None})
        declined = set(sess_state.get('declined', set()))
        lc_msg = (user_msg or '').lower()
        decline_map = {
            'name2': ['sem nome 2','não adicionar nome 2','nao adicionar nome 2','não quero nome 2','nao quero nome 2','sem segundo nome','não quero segundo nome','nao quero segundo nome'],
            'optional_message': ['sem mensagem','não quero mensagem','nao quero mensagem','pular mensagem','sem texto especial','manter sem mensagem'],
            'photos': ['sem foto','sem fotos','não adicionar foto','nao adicionar foto','não adicionar fotos','nao adicionar fotos','pular foto','pular fotos','sem imagens'],
            'youtube': ['sem vídeo','sem video','não adicionar vídeo','nao adicionar video','sem youtube','sem link do youtube','sem yt','não quero video','nao quero video'],
            'effect_type': ['sem efeito','efeito nenhum','manter sem efeito','sem efeitos'],
            'background_type': ['manter fundo padrão','fundo padrão','sem fundo','não mudar fundo','nao mudar fundo'],
            'text_theme': ['manter tema padrão','tema padrão','não mudar tema','nao mudar tema','sem mudar tema'],
        }
        try:
            for k, pats in decline_map.items():
                if any(p in lc_msg for p in pats):
                    declined.add(k)
        except Exception:
            pass
        # Heurística genérica: se usuário respondeu com "não/nao",
        # considerar recusa apenas do opcional atualmente sugerido na sessão
        try:
            last_assistant_msg = ''
            for m in reversed(raw_history):
                if (m.get('role') == 'assistant') and isinstance(m.get('content'), str):
                    last_assistant_msg = m.get('content') or ''
                    break
            lam = (last_assistant_msg or '').lower()
            neg = ('não' in lc_msg) or ('nao' in lc_msg)
            if neg:
                pending = sess_state.get('pending_optional')
                if pending:
                    declined.add(pending)
        except Exception:
            pass
        if session_id is not None:
            sess_state['declined'] = declined
            SESS_OPTS[session_id] = sess_state

        # Normaliza e limita histórico (evita entradas inválidas e excesso)
        history = []
        if isinstance(raw_history, list):
            try:
                for m in raw_history[-20:]:  # limite adicional no backend (ampliado)
                    role = (m.get('role') or '').strip().lower()
                    content = m.get('content')
                    if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
                        history.append({ 'role': role, 'content': content.strip() })
            except Exception:
                history = []

        system = _build_system_prompt()
        try:
            now_dt = datetime.now(timezone)
            now_text = now_dt.strftime("%Y-%m-%d %H:%M")
            system = (
                system
                + "\n\n"
                + "Contexto temporal:\n"
                + f"- Agora: {now_text} (America/Manaus).\n"
                + "- Regra: 'contagem desde' exige data/hora no passado; 'contagem para' exige data/hora no futuro.\n"
            )
        except Exception:
            pass
        # Decide provedor de IA via variáveis de ambiente
        use_openai = False
        try:
            prov_llm = (os.getenv('LLM_PROVIDER') or '').strip().lower()
            prov_emb = (os.getenv('EMBEDDING_PROVIDER') or '').strip().lower()
            use_flag = (os.getenv('USE_OPENAI') or '').strip().lower()
            use_openai = (
                prov_llm == 'openai' or prov_emb == 'openai' or use_flag in ('1', 'true', 'yes')
            )
        except Exception:
            use_openai = False

        reply = None

        if use_openai:
            api_key = os.getenv('OPENAI_API_KEY')
            model = (os.getenv('OPENAI_MODEL') or '').strip() or 'gpt-4o-mini'
            # Verifica se Langfuse está disponível e configurado
            lf_secret = (os.getenv('LANGFUSE_SECRET_KEY') or '').strip()
            lf_public = (os.getenv('LANGFUSE_PUBLIC_KEY') or '').strip()
            lf_base = (os.getenv('LANGFUSE_BASE_URL') or '').strip()
            use_langfuse = LF_OPENAI is not None and lf_secret and lf_public and lf_base

            if api_key:
                try:
                    # Helper: label humano para chave técnica (definido antes do uso)
                    def human_label(key: str) -> str:
                        try:
                            if not isinstance(key, str):
                                return str(key)
                            # Mapeia combinado de descrição
                            if key == 'event_description/custom_event_description':
                                lbl = (
                                    (isinstance(label_map, dict) and label_map.get(key))
                                    or (
                                        ((isinstance(label_map, dict) and label_map.get('event_description')) or 'Descrição do evento')
                                        + ' ou '
                                        + ((isinstance(label_map, dict) and label_map.get('custom_event_description')) or 'Frase personalizada')
                                    )
                                )
                                return lbl
                            if isinstance(label_map, dict):
                                lbl = label_map.get(key)
                                if lbl:
                                    return lbl
                            # Fallbacks padrão
                            fallback = {
                                'name1': 'Nome 1',
                                'name2': 'Nome 2',
                                'event_date': 'Data do evento',
                                'event_time': 'Hora do evento',
                                'counter_mode': 'Tipo de contagem',
                                'description_mode': 'Modo de descrição',
                                'event_description': 'Descrição do evento',
                                'custom_event_description': 'Frase personalizada',
                                'email': 'E-mail',
                                'optional_message': 'Mensagem especial',
                                # Derivados de UI
                                'photos_count': 'Quantidade de fotos selecionadas',
                                'has_photos': 'Tem fotos?',
                                'photos_selected': 'Fotos selecionadas (número visível)',
                                'photos_max': 'Limite de fotos',
                                'photos_selected_text': 'Texto exibido de seleção de fotos',
                                'video_id': 'ID do vídeo',
                                'has_video': 'Tem vídeo?',
                                'youtube_link_value': 'Link do YouTube',
                                'effect_type': 'Efeito',
                                'background_type': 'Tipo de fundo',
                                'text_theme': 'Tema do texto',
                            }.get(key)
                            return fallback or key
                        except Exception:
                            return str(key)
                    # Monta conteúdo do usuário com contexto do formulário em Markdown
                    ctx_lines = []
                    if isinstance(form_ctx, dict):
                        derived_whitelist = {
                            'photos_count','has_photos','photos_selected','photos_max','photos_selected_text',
                            'video_id','has_video','youtube_link_value'
                        }
                        for k, v in form_ctx.items():
                            # Apenas campos confirmados pelo usuário
                            if user_set_fields and (k not in user_set_fields) and (k not in derived_whitelist):
                                continue
                            try:
                                raw_val = v if isinstance(v, str) else (str(v) if v is not None else '')
                            except Exception:
                                raw_val = ''
                            val = raw_val
                            if k == 'counter_mode':
                                if raw_val == 'since':
                                    val = 'contagem desde'
                                elif raw_val == 'until':
                                    val = 'contagem para'
                            # Usa label humano quando disponível
                            ctx_label = human_label(k)
                            ctx_lines.append(f"- {ctx_label}: {val}")
                    ctx_block = "\n".join(ctx_lines)
                    # dom_state ignorado no modo estrito
                    dom_block = ""
                    # Campos obrigatórios para completude (ordem desejada)
                    required_order = ['name1','event_date','event_time','counter_mode','event_description/custom_event_description','email']
                    # Apenas campos realmente confirmados pelo usuário
                    confirmed_keys = set(user_set_fields or [])
                    # Considera descrição válida se houver valor não vazio em uma das duas chaves
                    ev_desc_val = str(form_ctx.get('event_description','')).strip() if isinstance(form_ctx, dict) else ''
                    cust_desc_val = str(form_ctx.get('custom_event_description','')).strip() if isinstance(form_ctx, dict) else ''
                    has_desc = bool(ev_desc_val) or bool(cust_desc_val)
                    # Monta lista de pendências respeitando a ordem desejada
                    missing = []
                    for k in required_order:
                        if k == 'event_description/custom_event_description':
                            if not has_desc:
                                missing.append(k)
                        elif k not in confirmed_keys:
                            missing.append(k)

                    missing_block = "\n".join([f"- {human_label(k)}" for k in missing])
                    # Validação temporal: compatibilidade entre counter_mode e data/hora (preciso antes do checklist)
                    ev_date_str = str(form_ctx.get('event_date', '') or '').strip()
                    ev_time_str = str(form_ctx.get('event_time', '') or '').strip()
                    mode_str = str(form_ctx.get('counter_mode', '') or '').strip().lower()
                    inconsistency_msg = ''
                    try:
                        now_dt = datetime.now(timezone)
                        ev_dt = None
                        if ev_date_str and ev_time_str:
                            try:
                                ev_dt = timezone.localize(datetime.strptime(f"{ev_date_str} {ev_time_str}", "%Y-%m-%d %H:%M"))
                            except Exception:
                                ev_dt = None
                        if ev_dt and mode_str in ('since','until'):
                            if mode_str == 'since' and ev_dt > now_dt:
                                inconsistency_msg = "Tipo 'since' exige data/hora no passado; ajuste 'counter_mode' para 'until' ou escolha uma data passada."
                            elif mode_str == 'until' and ev_dt <= now_dt:
                                inconsistency_msg = "Tipo 'until' exige data/hora no futuro; ajuste 'counter_mode' para 'since' ou escolha uma data futura."
                    except Exception:
                        # Não bloquear caso parsing falhe; apenas não emitir inconsistência
                        inconsistency_msg = inconsistency_msg or ''
                    # Checklist gerado no backend para o modelo copiar
                    def key_confirmed(k: str) -> bool:
                        try:
                            if k == 'event_description/custom_event_description':
                                desc_touched = ('event_description' in confirmed_keys) or ('custom_event_description' in confirmed_keys)
                                return bool(has_desc) and desc_touched
                            val = str(form_ctx.get(k, '') or '').strip()
                            if not val:
                                return False
                            return (k in confirmed_keys) and (not bool(inconsistency_msg))
                        except Exception:
                            return False
                    req_lines = []
                    for k in required_order:
                        mark = '[x]' if key_confirmed(k) else '[ ]'
                        mark_disp = '\\[x]' if mark == '[x]' else '\\[ ]'
                        req_lines.append(f"- {mark_disp} {human_label(k)}")
                    # Opcionais
                    photos_count = 0
                    photos_max = 3
                    try:
                        photos_count = int(str(form_ctx.get('photos_count', '') or '0'))
                    except Exception:
                        photos_count = 0
                    try:
                        photos_max = int(str(form_ctx.get('photos_max', '') or '3'))
                    except Exception:
                        photos_max = 3
                    opt_items = [
                        ('name2', human_label('name2'), (key_confirmed('name2') or ('name2' in declined))),
                        ('optional_message', human_label('optional_message'), (key_confirmed('optional_message') or ('optional_message' in declined))),
                        ('photos', f"Fotos ({photos_count}/{photos_max})", (photos_count > 0 or ('photos' in declined))),
                        ('youtube', 'Vídeo YouTube', ((bool(str(form_ctx.get('youtube_link_value','')).strip()) and ('youtubeLink' in confirmed_keys)) or ('youtube' in declined))),
                        ('effect_type', human_label('effect_type'), (key_confirmed('effect_type') or ('effect_type' in declined))),
                        ('background_type', human_label('background_type'), (key_confirmed('background_type') or ('background_type' in declined))),
                        ('text_theme', human_label('text_theme'), (key_confirmed('text_theme') or ('text_theme' in declined))),
                    ]
                    opt_pending_count = sum(1 for _, _, ok in opt_items if not ok)
                    try:
                        pend_key = sess_state.get('pending_optional')
                        if pend_key:
                            # Se o opcional atual foi recusado ou confirmado, limpar estado de pendência
                            was_ok = any((k == pend_key and ok) for k, _, ok in opt_items)
                            if (pend_key in declined) or was_ok:
                                sess_state['pending_optional'] = None
                                if session_id is not None:
                                    SESS_OPTS[session_id] = sess_state
                    except Exception:
                        pass
                    opt_lines = [f"- {'\\[x]' if ok else '\\[ ]'} {lbl}" for _, lbl, ok in opt_items]
                    checklist_block = (
                        "Checklist:\n" + "\n".join(req_lines) + "\n\n" + "Opcionais:\n" + "\n".join(opt_lines) + "\n\n"
                    )
                    def strip_dup_checklist(s: str) -> str:
                        try:
                            t = str(s or '')
                            lines = t.splitlines()
                            req_labels = [human_label(k) for k in required_order]
                            opt_labels = [lbl for _, lbl, _ in opt_items]
                            out = []
                            i = 0
                            def is_item(line: str) -> bool:
                                l = line.strip()
                                if l == '':
                                    return True
                                ll = l.lower()
                                if ll.startswith('checklist') or ll.startswith('opcionais'):
                                    return True
                                if l.startswith('-'):
                                    return True
                                if l in req_labels:
                                    return True
                                if (l in opt_labels) or l.startswith('Fotos (') or l.startswith('Vídeo YouTube'):
                                    return True
                                # linhas como "[x] Nome 1" sem marcador '-'
                                if l.startswith('['):
                                    return True
                                return False
                            while i < len(lines):
                                l = lines[i]
                                if l.strip().lower().startswith('checklist'):
                                    j = i + 1
                                    while j < len(lines) and is_item(lines[j]):
                                        j += 1
                                    i = j
                                    continue
                                out.append(l)
                                i += 1
                            return "\n".join(out).lstrip()
                        except Exception:
                            return str(s or '')
                    def strip_optional_when_required(s: str) -> str:
                        try:
                            txt = str(s or '')
                            if next_required:
                                kw = ['foto','fotos','vídeo','video','youtube','efeito','fundo','tema do texto','tema']
                                lines = txt.splitlines()
                                filtered = []
                                for l in lines:
                                    ll = l.lower()
                                    if any(k in ll for k in kw):
                                        continue
                                    filtered.append(l)
                                txt2 = "\n".join(filtered)
                                hint = f"Agora preencha o campo {human_label(next_required)} na página e confirme."
                                if 'preencha o campo' not in txt2.lower():
                                    txt2 = (txt2 + ("\n\n" + hint))
                                return txt2
                            return txt
                        except Exception:
                            return str(s or '')
                    # Progressão: determine próximo campo obrigatório (mesma ordem com descrição antes de e-mail)
                    # já calculado acima
                    # Estilo visual é opcional: fundo (background_type) e tema do texto (text_theme) não bloqueiam avanço.
                    next_required = None
                    for k in required_order:
                        if k == 'event_description/custom_event_description':
                            if not has_desc:
                                next_required = k
                                break
                        elif k not in confirmed_keys:
                            next_required = k
                            break

                    # Se não há próximo obrigatório por pendência mas há inconsistência, force ajuste de counter_mode
                    if not next_required and inconsistency_msg:
                        next_required = 'counter_mode'

                    # Checagem do campo atual contra o formulário (considerando inconsistências)
                    current_confirmed = False
                    current_value = ''
                    if next_required:
                        if next_required == 'event_description/custom_event_description':
                            # Considera confirmado apenas se houver valor E o usuário tocou em uma das chaves
                            desc_touched = ('event_description' in confirmed_keys) or ('custom_event_description' in confirmed_keys)
                            current_confirmed = has_desc and desc_touched
                            current_value = cust_desc_val or ev_desc_val or ''
                        else:
                            try:
                                current_value = str(form_ctx.get(next_required, '')).strip()
                            except Exception:
                                current_value = ''
                            # Considera confirmado apenas se houver valor, sem inconsistência, e o usuário tocou na chave
                            current_confirmed = bool(current_value) and (next_required in confirmed_keys) and not bool(inconsistency_msg)
                    # Detecta prontidão a partir da mensagem do usuário
                    ready_keywords = ['pronto', 'finalizar', 'concluir', 'pode criar', 'vamos criar', 'criar minha homenagem', 'pode publicar', 'terminamos', 'fechamos']
                    msg_lc = (user_msg or '').strip().lower()
                    ready_signal = any(kw in msg_lc for kw in ready_keywords)
                    status_line = (
                        f"Status do formulário: "
                        + (
                            ('completo' if opt_pending_count == 0 else f"completo (opcionais pendentes: {opt_pending_count})") if (not missing and not inconsistency_msg) else (
                                f"incompleto (pendentes: {len(missing)})" if missing else "incompleto (inconsistência temporal: contador vs data/hora)"
                            )
                        )
                    )
                    # Label humano para próximo obrigatório
                    next_label = human_label(next_required) if next_required else ''
                    current_optional_key = None
                    if (not next_required) and opt_pending_count > 0:
                        try:
                            for k,lbl,ok in opt_items:
                                if not ok:
                                    current_optional_key = k
                                    break
                        except Exception:
                            current_optional_key = None
                        if session_id is not None:
                            try:
                                sess_state['pending_optional'] = current_optional_key
                                SESS_OPTS[session_id] = sess_state
                            except Exception:
                                pass
                    user_content = (
                        (
                            (f"Progresso: próximo campo obrigatório: {next_label}\n\n" if next_required else "") +
                            f"{status_line}\n\n"
                            + (f"Checagem do campo atual: confirmado={'sim' if current_confirmed else 'não'}; valor='{current_value}'\n\n" if next_required else "")
                            + (f"Diretriz (campo atual não confirmado): Se confirmado=não, NÃO trate mensagens do chat como preenchimento. Instrua claramente: 'Agora preencha o campo {next_label} na página e confirme'.\n\n" if (next_required and not current_confirmed) else "")
                            + (f"Inconsistências de validação:\n- {inconsistency_msg}\n\n" if inconsistency_msg else "")
                            + (f"Prontidão (sinal do usuário): {'sim' if ready_signal else 'não'}\n\n")
                            + f"Mensagem do usuário:\n{user_msg}\n\n"
                            f"Contexto do formulário (confirmado):\n{(ctx_block or '—')}\n\n"
                            + (f"Estado atual da tela (DOM/UI) confirmado:\n{dom_block}\n\n" if dom_block else "")
                            + (f"Campos não confirmados (trate como 'não definido' até o usuário validar):\n{missing_block}\n" if missing else "")
                            + (f"Diretriz: enquanto houver opcionais pendentes, evite afirmar 'Sua página está completa'; prefira 'Pronta para publicar' e ofereça preencher opcionais.\n\n" if opt_pending_count > 0 else "")
                            + ((f"Opcional sugerido agora: {human_label(current_optional_key)} (key={current_optional_key}). Instrua: 'Se não quiser, responda \"não\"'.\n\n") if (current_optional_key and (not next_required)) else "")
                            + ("Opcionais recusados pelo usuário:\n- " + "\n- ".join([lbl for k,lbl,ok in opt_items if (k in declined)]) + "\n\n" if declined else "")
                        ).strip()
                    )

                    try:
                        messages = [{"role": "system", "content": system}]
                        messages.extend(history)  # mantém a linha de conversa
                        messages.append({"role": "user", "content": user_content})
                        if use_langfuse:
                            # Usa drop-in replacement do OpenAI via Langfuse
                            completion = LF_OPENAI.chat.completions.create(
                                name="copilot-chat",
                                model=model,
                                messages=messages,
                                metadata={
                                    "feature": "copilot",
                                    "session_id": session_id or "",
                                    "context_keys": list(form_ctx.keys()) if isinstance(form_ctx, dict) else [],
                                    "dom_keys": [],
                                },
                            )
                            reply = completion.choices[0].message.content
                            txt = strip_dup_checklist(reply)
                            txt = strip_optional_when_required(txt)
                            if opt_pending_count > 0:
                                try:
                                    low = (txt or '').lower()
                                    if 'página está completa' in low or 'pagina esta completa' in low:
                                        txt = txt.replace('Sua página está completa', 'Sua página está pronta para publicar')
                                        txt = txt.replace('sua página está completa', 'Sua página está pronta para publicar')
                                except Exception:
                                    pass
                            reply = (checklist_block + txt)
                        else:
                            # Usa SDK nativo da OpenAI
                            client = OpenAI(api_key=api_key)
                            completion = client.chat.completions.create(
                                model=model,
                                messages=messages,
                            )
                            reply = completion.choices[0].message.content
                            txt = strip_dup_checklist(reply)
                            txt = strip_optional_when_required(txt)
                            if opt_pending_count > 0:
                                try:
                                    low = (txt or '').lower()
                                    if 'página está completa' in low or 'pagina esta completa' in low:
                                        txt = txt.replace('Sua página está completa', 'Sua página está pronta para publicar')
                                        txt = txt.replace('sua página está completa', 'Sua página está pronta para publicar')
                                except Exception:
                                    pass
                            reply = (checklist_block + txt)
                    except Exception as e:
                        try:
                            fallback_model = 'gpt-4o-mini'
                            messages = [{"role": "system", "content": system}]
                            messages.extend(history)
                            messages.append({"role": "user", "content": user_content})
                            if use_langfuse:
                                completion = LF_OPENAI.chat.completions.create(
                                    name="copilot-chat",
                                    model=fallback_model,
                                    messages=messages,
                                    metadata={
                                        "feature": "copilot",
                                        "session_id": session_id or "",
                                        "context_keys": list(form_ctx.keys()) if isinstance(form_ctx, dict) else [],
                                    },
                                )
                            else:
                                client = OpenAI(api_key=api_key)
                                completion = client.chat.completions.create(
                                    model=fallback_model,
                                    messages=messages,
                                )
                            reply = completion.choices[0].message.content
                            txt = strip_dup_checklist(reply)
                            txt = strip_optional_when_required(txt)
                            if opt_pending_count > 0:
                                try:
                                    low = (txt or '').lower()
                                    if 'página está completa' in low or 'pagina esta completa' in low:
                                        txt = txt.replace('Sua página está completa', 'Sua página está pronta para publicar')
                                        txt = txt.replace('sua página está completa', 'Sua página está pronta para publicar')
                                except Exception:
                                    pass
                            reply = (checklist_block + txt)
                        except Exception as e2:
                            return jsonify({
                                'ok': False,
                                'error': 'Falha ao gerar resposta via IA',
                                'details': str(e2)
                            }), 502
                except Exception as e:
                    # Erro crítico ao usar provedor de IA: retornar erro com detalhes
                    return jsonify({
                        'ok': False,
                        'error': 'Erro crítico ao usar provedor de IA',
                        'details': str(e)
                    }), 500
            else:
                return jsonify({
                    'ok': False,
                    'error': 'OPENAI_API_KEY ausente; habilite USE_OPENAI e configure a chave'
                }), 503
        else:
            # IA não habilitada: retornar erro explícito
            return jsonify({
                'ok': False,
                'error': 'IA não habilitada; defina USE_OPENAI=true e OPENAI_API_KEY'
            }), 503

        try:
            user_lc = (user_msg or '').strip().lower()
            ev_type = None
            if 'batizado' in user_lc:
                ev_type = 'batizado'
            elif 'casamento' in user_lc:
                ev_type = 'casamento'
            elif 'anivers' in user_lc:
                ev_type = 'aniversário'
            elif 'formatura' in user_lc:
                ev_type = 'formatura'
            elif 'chá de bebê' in user_lc or 'cha de bebe' in user_lc:
                ev_type = 'chá de bebê'
            elif 'bodas' in user_lc:
                ev_type = 'bodas'
            elif 'noivado' in user_lc:
                ev_type = 'noivado'
            elif 'culto' in user_lc:
                ev_type = 'culto'
            elif 'natal' in user_lc:
                ev_type = 'natal'
            elif 'ano novo' in user_lc:
                ev_type = 'ano novo'
            intent_chat = any(x in user_lc for x in ['quero', 'gostaria', 'planejo', 'pensando', 'evento de'])
            if reply and (ev_type or intent_chat):
                conv_block = (
                    (f"Ok — {ev_type}.\n\n" if ev_type else "Ok.\n\n")
                )
                reply = str(reply or '') + conv_block
        except Exception:
            pass

        # Antes de retornar, garanta a pergunta opcional de Nome 2 quando aplicável
        try:
            form_ctx_dict = form_ctx if isinstance(form_ctx, dict) else {}
            # Considera confirmados apenas os campos tocados pelo usuário, se fornecidos
            confirmed_keys = set(k for k in form_ctx_dict.keys() if (not user_set_fields or k in user_set_fields))
            n1_val = str(form_ctx_dict.get('name1', '') or '').strip()
            n2_val = str(form_ctx_dict.get('name2', '') or '').strip()
            already_asked = False
            try:
                already_asked = any(
                    (m.get('role') == 'assistant') and (
                        ('Nome 2' in (m.get('content') or '')) or ('segundo homenageado' in (m.get('content') or ''))
                    )
                    for m in (history or [])
                )
            except Exception:
                already_asked = False
            skip_optional = False
            try:
                msg_lc = (user_msg or '').strip().lower()
                neg_markers = ['sem segundo', 'não há segundo', 'nao ha segundo', 'somente um', 'apenas um', 'só um', 'so um', 'individual', 'apenas uma pessoa', 'somente uma pessoa']
                skip_optional = any(x in msg_lc for x in neg_markers)
            except Exception:
                skip_optional = False
            # Injeta pergunta fora do checklist: após confirmação de Nome 1 e antes de avançar, se Nome 2 estiver vazio
            # Não perguntar se o usuário já recusou 'Nome 2'
            if reply and n1_val and ('name1' in confirmed_keys) and (not n2_val) and (not already_asked) and (not skip_optional) and ('name2' not in declined):
                question_block = (
                    "Pergunta: Há um segundo homenageado? Se sim, preencha 'Nome 2' na página e confirme; "
                    "se não, responda 'não' e pode deixar em branco. Isso não bloqueia o avanço.\n\n"
                )
                reply = str(reply or '') + question_block
        except Exception:
            # Não bloquear retorno em caso de falha ao injetar pergunta opcional
            pass

        return jsonify({
            'ok': True,
            'system_prompt': system,
            'reply': reply,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@app.route('/api/copilot/clear', methods=['POST'])
def copilot_clear():
    try:
        data = request.get_json(force=True) or {}
        session_id = (data.get('session_id') or '').strip() or None
        if session_id and (session_id in SESS_OPTS):
            try:
                del SESS_OPTS[session_id]
            except Exception:
                pass
        return jsonify({'ok': True, 'cleared': True, 'session_id': session_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


# Função para enviar e-mail com anexo
def send_email_with_qr_attachment(
    to_address, subject, body, qr_image_bytes, filename="qrcode.png"
):
    client = boto3.client(
        "ses",
        region_name="us-east-1",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )

    # Cria a mensagem MIME
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = "contato@meueventoespecial.com.br"
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
        Source="contato@meueventoespecial.com.br",
        Destinations=[to_address],  # destinatário principal e BCC
        RawMessage={"Data": raw_msg},
    )

    return response


# Função para enviar e-mail
def send_email(to_address, subject, body):
    client = boto3.client(
        "ses",
        region_name="us-east-1",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )  # Substitua pela sua região
    response = client.send_email(
        Source="contato@meueventoespecial.com.br",  # Substitua pelo seu e-mail
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


# Utilitário: saudação amigável em e-mails com 1 ou 2 nomes
def build_email_greeting(name1: str, name2: str) -> str:
    n1 = (name1 or "").strip()
    n2 = (name2 or "").strip()
    if n1 and n2:
        return f"Olá {n1} e {n2},<br><br>"
    if n1:
        return f"Olá {n1},<br><br>"
    if n2:
        return f"Olá {n2},<br><br>"
    return "Olá,<br><br>"


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

from PIL import Image
import io

def compress_image(image, max_size=(1600, 1600), quality=80):
    img = Image.open(image)
    img.thumbnail(max_size)

    output = io.BytesIO()
    if img.format == "PNG":
        img.save(output, format="PNG", optimize=True)
    else:
        img = img.convert("RGB")  # Evita erros com imagens .webp etc
        img.save(output, format="JPEG", quality=quality, optimize=True)

    output.seek(0)
    return output

# Mapeia extensão para Content-Type correto
def get_content_type(ext: str) -> str:
    if ext.lower() == "png":
        return "image/png"
    # Trata jpg e jpeg como image/jpeg
    return "image/jpeg"

@app.route("/create", methods=["GET", "POST"])
def create_couple_page():
    try:
        if request.method == "GET":
            return redirect(url_for("index"))
        # Capturando os valores do formulário
        try:
            print("[create] Content-Type:", request.headers.get("Content-Type"))
            print("[create] content_length:", request.content_length)
            print("[create] files len:", len(request.files or {}))
            print("[create] files keys:", list(request.files.keys()))
        except Exception:
            pass
        name1 = request.form["name1"]
        name2 = request.form["name2"]
        event_date = request.form["event_date"]
        event_time = request.form["event_time"]
        email = request.form["email"]
        event_description = request.form.get("event_description")
        custom_description = request.form.get("custom_event_description")

        print(event_description)
        print(custom_description)

        event_description = request.form.get("event_description", "").strip()
        custom_description = request.form.get("custom_event_description", "").strip()
        description_mode = request.form.get("description_mode")

        if description_mode == "custom" and custom_description:
            final_description = custom_description
        else:
            final_description = event_description

        effect_type = request.form.get("effect_type", "none")
        background_type = request.form.get("background_type", "default")
        text_theme = request.form.get("text_theme", "text_theme_pink")
        counter_mode = request.form.get("counter_mode", "since")

        # Validação: modo "Tempo desde..." não pode ter data futura
        try:
            event_dt_naive = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
            event_dt = timezone.localize(event_dt_naive)
            now_dt = datetime.now(timezone)
            if counter_mode == "since" and event_dt > now_dt:
                flash("Para o modo 'Tempo desde...', escolha uma data que já passou ou mude para 'Contagem para...'.")
                return redirect(url_for("index"))
        except Exception:
            pass

        # Validação: modo "Contagem para..." não pode ter data passada ou já chegada
        try:
            event_dt_naive = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
            event_dt = timezone.localize(event_dt_naive)
            now_dt = datetime.now(timezone)
            if counter_mode == "until" and event_dt <= now_dt:
                flash("Para o modo 'Contagem para...', escolha uma data futura ou mude para 'Tempo desde...'.")
                return redirect(url_for("index"))
        except Exception:
            pass

        optional_message = sanitize_html(request.form.get("optional_message", ""))
        youtubelink = request.form.get("youtubeLink")
        
        # Captura os ajustes de posição/zoom das fotos
        image_adjustments = request.form.get("image_adjustments", "{}")
        # Converte para dict se não estiver vazio
        try:
            import json
            image_adjustments_dict = json.loads(image_adjustments) if image_adjustments else {}
        except:
            image_adjustments_dict = {}

        # Converte números em Decimal para salvar no DynamoDB
        image_adjustments_dict = convert_numbers_to_decimal(image_adjustments_dict)

        # Gera um código alfanumérico único para a URL da página (garante unicidade ANTES de usar)
        unique_code = generate_unique_code()
        while table.scan(FilterExpression=Key("page_url").eq(unique_code))["Count"] > 0:
            unique_code = generate_unique_code()

        # Criar a pasta se não existir para guardar imagens de perfil
        # upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], unique_code)
        # if not os.path.exists(upload_folder):
        # os.makedirs(upload_folder)

        # Processa o URL do YouTube para guardar apenas o código do vídeo
        if youtubelink:
            video_id = extract_video_id(youtubelink)
            if not video_id:
                flash("Não parece ser um link válido do YouTube.")
                return redirect(url_for("index"))
        else:
            video_id = None
        # Verificar se há imagens e salvá-las
        images = [
            image for image in request.files.getlist("images") if image.filename != ""
        ]
        try:
            print("[create] unique_code:", unique_code)
            print("[create] imagens recebidas:", [img.filename for img in images])
            # Diagnóstico adicional: se não houver arquivos, inspeciona raw keys
            if not images:
                try:
                    print("[create] getlist('images') len:", len(request.files.getlist("images")))
                    for k in request.files.keys():
                        f = request.files.get(k)
                        if f:
                            print(f"[create] file key={k} name={getattr(f,'filename',None)} type={getattr(f,'content_type',None)} size? unknown")
                except Exception:
                    pass
        except Exception:
            pass
        if len(images) > 3:
            flash("Você pode enviar no máximo 3 imagens.")
            return redirect(request.url)

        for i, image in enumerate(images):
            if image and allowed_file(image.filename):
                # Usa extensão consistente com o conteúdo
                orig_ext = image.filename.rsplit(".", 1)[1].lower()
                ext = "png" if orig_ext == "png" else "jpg"
                filename = secure_filename(f"{i+1}.{ext}")
                s3_key = f"pictures/{unique_code}/{filename}"
                try:
                    # redimensiona se muito grande
                    resized_image = compress_image(image)

                    # Enviar imagem ao S3
                    content_type = get_content_type(ext)
                    print("[create] uploading:", s3_key, content_type)
                    # Buckets com ACL desativada não aceitam ACL; manter apenas ContentType
                    s3_client.upload_fileobj(resized_image, S3_BUCKET, s3_key, ExtraArgs={"ContentType": content_type})
                except Exception as e:
                    print("[create] erro upload:", e)
                    return str(e), 500
            else:
                flash("Imagens devem estar no formato PNG ou JPEG.")
                return redirect(request.url)

        # Código já garantido único acima

        # Cria o casal e salva no DynamoDB
        new_couple = {
            "name1": name1,
            "name2": name2,
            "event_date": event_date,
            "event_time": event_time,
            "event_description": final_description,
            "effect_type": effect_type,
            "background_type": background_type,
            "text_theme": text_theme,
            "page_url": unique_code,
            "optional_message": optional_message,
            "email": email,
            "paid": False,
            "created_at": datetime.now(timezone).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            + "Z",
            # Define validade inicial: 1h a partir da criação para páginas não pagas
            "expires_at": (datetime.now(timezone) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            + "Z",
            "video_id": video_id,
            "counter_mode": counter_mode,
            "image_adjustments": image_adjustments_dict,  # Adiciona ajustes de foto
        }
        table.put_item(Item=new_couple)

        # Gera o link para a página recém-criada
        url = url_for("couple_page", page_url=new_couple["page_url"], _external=True)

        # Gerar QR Code e salvar
        qr_image_bytes = generate_qr_code(url, unique_code)
        
        # Corpo do e-mail
        email_subject = "Sua página foi criada!"
        email_body = f"""
        {build_email_greeting(name1, name2)}
        Sua página foi criada com sucesso e estará ativa por 1 hora pra você testar à vontade! Acesse-a aqui: <a href='{url}'>{url}</a>.<br><br>
        Para estender para 1 mês e ter tempo suficiente para preparar sua surpesa, acesse o link no final da página e realize o pagamento. O aviso desparecerá após o pagamento.  
        Seu QR Code está anexado neste e-mail.<br><br>
        Se quiser deletar sua página, acesse o link abaixo e insira seu e-mail e o código da página: {unique_code}<br>
        <a href='https://www.meueventoespecial.com.br/deletar'>https://www.meueventoespecial.com.br/deletar</a> <br>
        Ou ela será deletada automaticamente em 1 hora (exceto se fizer upgrade para 30 dias).<br><br>
        Atenciosamente,<br>
        Equipe de Suporte
        """
        email_admin = "marciosferreira@yahoo.com.br"
        # Enviar e-mail admin
        print('first')
        send_email(email_admin, email_subject, email_body)
        # envia email cliente com qrcode

        print("email")
        print(email)
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
    # SEO: canonical e og:image dinâmicos
    canonical_url = request.url_root.rstrip("/")
    og_image_url = url_for(
        "static",
        filename="images/logo_qrcode_heart_transparent.png",
        _external=True,
    )
    meta_description = (
        "Crie páginas especiais com QR Code, fotos e vídeo para celebrar momentos únicos."
    )
    return render_template(
        "index.html",
        canonical_url=canonical_url,
        og_image_url=og_image_url,
        meta_description=meta_description,
        page_title="Meu Evento Especial — Compartilhe com QR Code, Fotos e Vídeo",
        show_copilot_widget=True,
    )


import os
from flask import render_template
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key


# from datetime import datetime

from datetime import datetime
import pytz


@app.route("/couple_page/<string:page_url>")
def couple_page(page_url):

    # Exibe a seção de pagamento apenas se ainda não estiver pago
    show_payment_link = False

    response = table.scan(FilterExpression=Key("page_url").eq(page_url))
    items = response.get("Items", [])

    if not items:
        # Retorna uma página personalizada informando que a página não existe
        return render_template("not_found.html"), 404

    couple = items[0]

    # Oculta a seção "Extensão de validade" quando já estiver pago
    show_payment_link = not couple.get("paid", False)

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

    # Define modo efetivo do contador baseado no tempo real
    display_counter_mode = "since" if now >= event_datetime else "until"
    years = time_diff.days // 365
    months = (time_diff.days % 365) // 30
    days = (time_diff.days % 365) % 30
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Validade baseada em expires_at (persistida). Fallback: created_at + delta.
    valid_until_str = None
    is_expired = False
    try:
        valid_until_dt = None
        expires_str = couple.get("expires_at")
        if expires_str:
            base = expires_str.replace("Z", "")
            if "." in base:
                base = base.split(".")[0]
            exp_naive = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
            valid_until_dt = timezone.localize(exp_naive)
        else:
            created_at_str = couple.get("created_at")
            if created_at_str:
                base = created_at_str.replace("Z", "")
                if "." in base:
                    base = base.split(".")[0]
                created_naive = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
                created_local = timezone.localize(created_naive)
                delta = timedelta(days=30) if couple.get("paid", False) else timedelta(hours=1)
                valid_until_dt = created_local + delta

        if valid_until_dt is not None:
            valid_until_str = valid_until_dt.strftime("%d/%m/%Y %H:%M")
            is_expired = now >= valid_until_dt
    except Exception:
        valid_until_str = None
        is_expired = False

    # Verifica a existência de um vídeo
    has_video = couple.get("video_id") is not None

    # Verifica as imagens disponíveis no S3 em múltiplos prefixos possíveis
    images = []
    prefixes_to_check = [
        f"pictures/{page_url}/",
        f"pictures/{page_url}/originals/",
        f"pictures/{page_url}/photos/",
    ]
    for pref in prefixes_to_check:
        try:
            resp = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=pref)
            if "Contents" in resp:
                keys = [obj["Key"] for obj in resp["Contents"]]
                valid = [
                    k for k in keys
                    if not k.endswith("/") and k.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"))
                ]
                if valid:
                    print(f"Imagens encontradas em '{pref}':")
                    for k in valid:
                        print(k)
                images.extend(valid)
        except Exception as e:
            print(f"Erro ao listar objetos no prefixo {pref}: {e}")

    # Remove duplicados mantendo a ordem
    seen = set()
    dedup_images = []
    for k in images:
        if k not in seen:
            seen.add(k)
            dedup_images.append(k)
    images = dedup_images
    image_exists = len(images) > 0
    if not image_exists:
        print("Nenhuma imagem válida encontrada em quaisquer prefixos.")

    # Gera o caminho do QR code
    import boto3

    bucket_name = "qrcodelove-pictures"
    qr_code_key = f"qrcodes/{couple['page_url']}.png"

    # Se o bucket for público ou o objeto for acessível publicamente:
    qr_code_path = f"https://{bucket_name}.s3.amazonaws.com/{qr_code_key}"

    # Renderiza a página com as informações calculadas

    # SEO: canonical, og:image e meta description dinâmicos
    canonical_url = url_for("couple_page", page_url=page_url, _external=True)

    if image_exists and images:
        # Usa a primeira imagem do S3 como imagem OG
        og_image_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{images[0]}"
    else:
        og_image_url = url_for(
            "static",
            filename="images/logo_qrcode_heart_transparent.png",
            _external=True,
        )

    meta_description = (
        f"Homenagem: {couple['name1']}" + (f" e {couple['name2']}" if couple.get('name2') else "") + " — "
        f"{couple.get('event_description', 'Celebre momentos especiais com fotos, música e QRCode.')}"
    )

    page_title = couple["name1"] + (f" & {couple['name2']}" if couple.get("name2") else "")

    # Base URL de imagens no S3 com região correta
    s3_base_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com"

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
        display_counter_mode=display_counter_mode,
        qr_code_path=qr_code_path,
        images=images,
        image_exists=image_exists,
        show_payment_link=show_payment_link,
        canonical_url=canonical_url,
        og_image_url=og_image_url,
        meta_description=meta_description,
        page_title=page_title,
        image_adjustments=convert_decimal_to_float(couple.get("image_adjustments", {})),  # Passa ajustes para template
        body_class=couple.get("background_type", ""),
        is_expired=is_expired,
        valid_until_str=valid_until_str,
        # Flag server-side: somente administradores logados recebem esta indicação
        is_admin_view=current_user.is_authenticated,
        s3_base_url=s3_base_url,
        show_copilot_widget=False,
    )

@app.route("/robots.txt")
def robots_txt():
    sitemap_url = url_for("sitemap_xml", _external=True)
    content = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
    return content, 200, {"Content-Type": "text/plain; charset=utf-8"}

@app.route("/sitemap.xml")
def sitemap_xml():
    # URL base
    urls = []
    # Home
    urls.append({
        "loc": url_for("index", _external=True),
        "changefreq": "weekly",
        "priority": "0.8",
    })

    try:
        # Lista páginas de casal (pode ser ajustado para usar index secundário)
        response = table.scan()
        items = response.get("Items", [])
        for item in items:
            page_url = item.get("page_url")
            if not page_url:
                continue
            urls.append({
                "loc": url_for("couple_page", page_url=page_url, _external=True),
                "changefreq": "monthly",
                "priority": "0.6",
            })
    except Exception as e:
        # Em caso de erro, seguimos com apenas a home
        pass

    # Monta XML
    xml_parts = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
    ]
    for u in urls:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{u['loc']}</loc>")
        xml_parts.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{u['priority']}</priority>")
        xml_parts.append("  </url>")
    xml_parts.append("</urlset>")
    xml = "\n".join(xml_parts)
    return xml, 200, {"Content-Type": "application/xml; charset=utf-8"}


import os
import requests
from flask import redirect, url_for

ASAAS_API_URL = "https://api.asaas.com/v3/paymentLinks"

# Catálogo de planos progressivos: duração e preço
PLANS = {
    "30d": {"days": 30, "price": 9.90, "label": "30 dias"}, # 9.90
    "90d": {"days": 90, "price": 24.90, "label": "90 dias"}, # 24.90
    "180d": {"days": 180, "price": 39.90, "label": "6 meses"}, # 39.90
    "365d": {"days": 365, "price": 69.90, "label": "1 ano"}, # 69.90
}


@app.route("/pay/<string:id>", methods=["POST"])
def pay(id):
    response = table.scan(FilterExpression=Key("page_url").eq(id))
    items = response.get("Items", [])
    if not items:
        return "Página não encontrada", 404
    couple = items[0]

    # Plano escolhido (default 30d)
    plan_code = request.form.get("plan", "30d")
    plan = PLANS.get(plan_code, PLANS["30d"])

    payload = {
        "billingType": "PIX",
        "chargeType": "DETACHED",
        "name": f"Meu Evento Especial — {plan['label']}",
        "description": f"Extensão de validade: PLAN={plan_code}",
        "value": plan["price"],
        "dueDateLimitDays": 1,
        "notificationEnabled": False,
        "externalReference": couple["page_url"],
        "callback": {
            # Adiciona parâmetros na URL para leitura pelo GTM (GA4):
            # v=<valor>, plan=<código>, ref=<page_url>
            "successUrl": (
                f"{url_for('payment_success', page_url=couple['page_url'], _external=True)}"
                f"?v={plan['price']:.2f}&plan={plan_code}&ref={couple['page_url']}"
            )
        },
        "isAddressRequired": False
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": os.getenv("ASAAS_API_KEY")  # ou use string fixa aqui para teste
    }

    try:
        response = requests.post(ASAAS_API_URL, json=payload, headers=headers)
        print("Status:", response.status_code)
        print("Response:", response.text)

        if response.status_code != 200:
            return f"Erro ao criar link de pagamento: {response.text}", 500

        data = response.json()
        return redirect(data["url"], code=302)

    except Exception as e:
        print("Erro ao processar pagamento:", e)
        return "Erro interno no servidor", 500


import requests

def buscar_pagamento_por_referencia(referencia):
    headers = {
        "Content-Type": "application/json",
        "access_token": os.getenv("ASAAS_API_KEY")
    }
    params = {
        "externalReference": referencia
    }

    response = requests.get("https://api.asaas.com/v3/payments", headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        pagamentos = data.get("data", [])

        # Filtra por pagamentos recebidos
        recebidos = [p for p in pagamentos if p.get("status") == "RECEIVED"]
        
        # Se houver, retorna o mais recente
        if recebidos:
            recebidos.sort(key=lambda x: x.get("paymentDate", ""), reverse=True)
            return recebidos[0]

        # Se nenhum recebido, retorna o mais recente de qualquer status
        if pagamentos:
            pagamentos.sort(key=lambda x: x.get("dateCreated", ""), reverse=True)
            return pagamentos[0]

    return None


@app.route("/payment_success/<string:page_url>")
def payment_success(page_url):
    # Busca pagamento no ASAAS (status precisa ser RECEIVED para confirmação real)
    pagamento = buscar_pagamento_por_referencia(page_url)
    asaas_confirmed = bool(pagamento) and pagamento.get("status") == "RECEIVED"
    dbg_param = request.args.get('debug') or request.args.get('debug_mode') or request.args.get('_dbg')
    debug_flag = dbg_param is not None

    # Passo 1: buscar no DynamoDB pelo GSI com page_url (com fallback para scan)
    response = table.query(
        IndexName="page_url-index",
        KeyConditionExpression=Key("page_url").eq(page_url)
    )
    items = response.get("Items", [])
    if not items:
        try:
            scan_resp = table.scan(FilterExpression=Key("page_url").eq(page_url))
            items = scan_resp.get("Items", [])
        except Exception:
            items = []
        if not items:
            return "Página não encontrada", 404

    couple = items[0]

    # Se não confirmado no ASAAS, permitir bypass quando já estiver pago no banco ou em modo debug
    if not asaas_confirmed:
        if couple.get("paid", False) or debug_flag:
            # Deriva dados do plano pelos parâmetros da URL ou últimos valores salvos
            plan_code = request.args.get("plan") or couple.get("last_plan_code") or "30d"
            v_arg = request.args.get("v")
            conv_value = None
            if v_arg:
                try:
                    conv_value = float(v_arg.replace(',', '.'))
                except Exception:
                    conv_value = None
            if conv_value is None:
                try:
                    conv_value = float(couple.get("last_plan_price") or 0)
                except Exception:
                    conv_value = 0.0
            # Cria um identificador de transação para rastrear no GA (não ASAAS)
            pagamento = pagamento or {"id": f"bypass-{page_url}", "value": conv_value, "description": f"PLAN={plan_code}"}
        else:
            return "Pagamento não confirmado", 400
    else:
        # Confirmado no ASAAS: marcar pago e estender expires_at conforme plano
        try:
            import pytz
            from datetime import datetime, timedelta
            timezone = pytz.timezone("America/Manaus")
            now_dt = datetime.now(timezone)

            # Determina plano via description (PLAN=code) ou valor
            desc = pagamento.get("description", "") or ""
            plan_code = None
            if "PLAN=" in desc:
                try:
                    plan_code = desc.split("PLAN=")[-1].split()[0].strip()
                except Exception:
                    plan_code = None
            if plan_code not in PLANS:
                val = float(pagamento.get("value", 0) or 0)
                for code, p in PLANS.items():
                    if abs(p["price"] - val) < 0.01:
                        plan_code = code
                        break
            plan = PLANS.get(plan_code, PLANS["30d"])  # inclui days/price/label
            plan_days = plan["days"]

            # Calcula nova validade
            new_expires_dt = None
            expires_str = couple.get("expires_at")
            if expires_str:
                base = expires_str.replace("Z", "")
                if "." in base:
                    base = base.split(".")[0]
                exp_naive = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
                exp_local = timezone.localize(exp_naive)
                if now_dt < exp_local:
                    new_expires_dt = exp_local + timedelta(days=plan_days)
                else:
                    new_expires_dt = now_dt + timedelta(days=plan_days)
            else:
                new_expires_dt = now_dt + timedelta(days=plan_days)

            new_expires_str = new_expires_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            last_payment_at = now_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            table.update_item(
                Key={
                    "email": couple["email"],
                    "page_url": couple["page_url"]
                },
                UpdateExpression="SET paid = :v, expires_at = :e, last_plan_code = :p, last_plan_price = :pr, last_payment_at = :t",
                ExpressionAttributeValues={":v": True, ":e": new_expires_str, ":p": plan_code or "30d", ":pr": plan["price"], ":t": last_payment_at}
            )
        except Exception:
            # Fallback: garante marcação como pago
            table.update_item(
                Key={
                    "email": couple["email"],
                    "page_url": couple["page_url"]
                },
                UpdateExpression="SET paid = :v",
                ExpressionAttributeValues={":v": True}
            )

        # Valor confirmado
        try:
            conv_value = float(pagamento.get("value", 0) or 0)
        except Exception:
            conv_value = float(PLANS.get(plan_code, PLANS["30d"]).get("price", 0))

    # IDs para tags
    redirect_url = url_for("couple_page", page_url=page_url)
    aw_id = os.getenv("AW_CONVERSION_ID") or ''
    aw_label = os.getenv("AW_CONVERSION_LABEL") or ''
    ga4_id = os.getenv("GA_MEASUREMENT_ID") or ''

    # Envio server-side (Measurement Protocol) para maior robustez
    try:
        ga_api_secret = os.getenv("GA_API_SECRET")
        if ga_api_secret and ga4_id:
            import uuid
            ga_cookie = request.cookies.get('_ga')
            client_id = None
            if ga_cookie:
                try:
                    parts = ga_cookie.split('.')
                    if len(parts) >= 4:
                        client_id = parts[-2] + '.' + parts[-1]
                except Exception:
                    client_id = None
            if not client_id:
                client_id = str(uuid.uuid4())

            mp_url = f"https://www.google-analytics.com/mp/collect?measurement_id={ga4_id}&api_secret={ga_api_secret}"

            txn_id = pagamento.get("id") if isinstance(pagamento, dict) else page_url

            mp_payload = {
                "client_id": client_id,
                "events": [
                    {
                        "name": "purchase",
                        "params": {
                            "currency": "BRL",
                            "value": float(conv_value or 0),
                            "transaction_id": txn_id,
                            **({"debug_mode": True} if debug_flag else {}),
                            "items": [
                                {
                                    "item_id": plan_code or "unknown",
                                    "item_name": f"Plano {plan_code or 'unknown'}",
                                    "price": float(conv_value or 0),
                                    "quantity": 1
                                }
                            ]
                        }
                    }
                ]
            }
            try:
                r = requests.post(mp_url, json=mp_payload, timeout=3)
                print("GA4 MP purchase status:", r.status_code, r.text[:200])
            except Exception as e:
                print("Falha ao enviar GA4 MP purchase:", e)
    except Exception as e:
        print("Erro no bloco GA4 Measurement Protocol:", e)

    return render_template(
        "payment_success.html",
        conv_value=conv_value,
        redirect_url=redirect_url,
        aw_id=aw_id,
        aw_label=aw_label,
        plan_code=plan_code,
        transaction_id=pagamento.get("id") if isinstance(pagamento, dict) else page_url,
        page_url=page_url,
        GA_MEASUREMENT_ID=ga4_id,
        GTM_CONTAINER_ID='',  # Desativa GTM nesta página
    )




from datetime import datetime
import pytz
from flask import jsonify, request


@app.route('/webhook', methods=['POST'])
def asaas_webhook():
    # Robustez: captura JSON mesmo se Content-Type vier incorreto
    body = request.get_json(silent=True)
    if body is None:
        try:
            import json
            body = json.loads(request.data or b"{}")
        except Exception:
            body = {}

    event = (body or {}).get("event")
    payment = (body or {}).get("payment", {})
    status = (payment or {}).get("status")
    try:
        print("[webhook] event:", event, "status:", status, "externalReference:", payment.get("externalReference"), "value:", payment.get("value"))
    except Exception:
        pass

    if event in ["PAYMENT_CREATED", "PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"]:
        # Reverte: exige confirmação real do pagamento
        if status not in ["RECEIVED", "CONFIRMED"]:
            return jsonify({"received": True, "ignored": True, "reason": "status_not_confirmed"})

        page_url = payment.get("externalReference")
        subscription = payment.get("subscription", "None")

        if subscription == "sub_8m3grz7tz4tyfb51":  # toyota
            return jsonify({"received": True})

        if not page_url:
            return "Referência externa não encontrada", 400

        try:
            response = table.scan(FilterExpression=Key("page_url").eq(page_url))
            items = response.get("Items", [])
            if not items:
                # Não bloqueia o webhook; apenas reporta sem erro
                print("[webhook] casal não encontrado para page_url:", page_url)
                return jsonify({"received": True, "ignored": True, "reason": "page_not_found"})

            couple = items[0]
            couple["paid"] = True
        except Exception as e:
            print("[webhook] erro ao consultar/atualizar DynamoDB:", e)
            return jsonify({"received": True, "error": "dynamodb_error"})

        from datetime import datetime, timedelta
        import pytz

        timezone = pytz.timezone("America/Manaus")
        now_dt = datetime.now(timezone)

        # Determina plano via description (PLAN=code) ou valor
        desc = payment.get("description", "") or ""
        plan_code = None
        if "PLAN=" in desc:
            try:
                plan_code = desc.split("PLAN=")[-1].split()[0].strip()
            except Exception:
                plan_code = None
        if plan_code not in PLANS:
            val = float(payment.get("value", 0) or 0)
            for code, p in PLANS.items():
                if abs(p["price"] - val) < 0.01:
                    plan_code = code
                    break
        plan_days = PLANS.get(plan_code, PLANS["30d"])["days"]

        # Estende validade por +plan_days. Se já existir expires_at futura, soma a partir dela; senão, a partir de agora.
        expires_str = couple.get("expires_at")
        try:
            if expires_str:
                base = expires_str.replace("Z", "")
                if "." in base:
                    base = base.split(".")[0]
                exp_naive = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
                exp_local = timezone.localize(exp_naive)
                if now_dt < exp_local:
                    new_expires_dt = exp_local + timedelta(days=plan_days)
                else:
                    new_expires_dt = now_dt + timedelta(days=plan_days)
            else:
                new_expires_dt = now_dt + timedelta(days=plan_days)
            couple["expires_at"] = new_expires_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        except Exception:
            # Garantia mínima: define validade a partir de agora por 30 dias
            couple["expires_at"] = (now_dt + timedelta(days=plan_days)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # Persiste informações do último pagamento para estatísticas
        couple["last_plan_code"] = plan_code or "30d"
        # DynamoDB não aceita float: usa Decimal
        try:
            couple["last_plan_price"] = Decimal(str(PLANS.get(plan_code, PLANS["30d"]) ["price"]))
        except Exception:
            couple["last_plan_price"] = Decimal("0")
        couple["last_payment_at"] = now_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        try:
            # Converte qualquer número restante para Decimal antes de salvar
            couple_to_save = convert_numbers_to_decimal(couple)
            table.put_item(Item=couple_to_save)
        except Exception as e:
            print("[webhook] erro ao persistir pagamento no DynamoDB:", e)
            return jsonify({"received": True, "error": "persist_error"})

        # GA4 Measurement Protocol: envia 'purchase' server-side para cobrir casos sem redirecionamento
        try:
            ga_api_secret = os.getenv("GA_API_SECRET")
            ga4_id = os.getenv("GA_MEASUREMENT_ID")
            if ga_api_secret and ga4_id:
                print(f"[webhook] GA4 MP configurado (measurement_id={ga4_id})")
                import uuid
                client_id = str(uuid.uuid4())
                mp_url = f"https://www.google-analytics.com/mp/collect?measurement_id={ga4_id}&api_secret={ga_api_secret}"
                try:
                    conv_value = float(payment.get("value", 0) or 0)
                except Exception:
                    conv_value = float(PLANS.get(plan_code or "30d", PLANS["30d"])['price'])
                txn_id = payment.get("id") or page_url
                mp_payload = {
                    "client_id": client_id,
                    "events": [
                        {
                            "name": "purchase",
                            "params": {
                                "currency": "BRL",
                                "value": float(conv_value or 0),
                                "transaction_id": txn_id,
                                "items": [
                                    {
                                        "item_id": plan_code or "unknown",
                                        "item_name": f"Plano {plan_code or 'unknown'}",
                                        "price": float(conv_value or 0),
                                        "quantity": 1
                                    }
                                ]
                            }
                        }
                    ]
                }
                try:
                    r = requests.post(mp_url, json=mp_payload, timeout=3)
                    print("[webhook] GA4 MP purchase status:", r.status_code, r.text[:200])
                except Exception as e:
                    print("[webhook] Falha ao enviar GA4 MP purchase:", e)
            else:
                print("[webhook] GA4 MP NÃO configurado: faltam GA_MEASUREMENT_ID ou GA_API_SECRET")
        except Exception as e:
            print("[webhook] Erro no bloco GA4 Measurement Protocol:", e)

        # (opcional) Envio de email de confirmação
        try:
            email_subject = "Pagamento confirmado!"
            email_body = f"""
            {build_email_greeting(couple.get('name1'), couple.get('name2'))}
            Seu pagamento foi confirmado! Sua página ficará ativa por 30 dias.<br>
            Acesse: <a href='{url_for("couple_page", page_url=page_url, _external=True)}'>{url_for("couple_page", page_url=page_url, _external=True)}</a>
            """
            send_email(couple.get("email"), email_subject, email_body)
        except Exception as e:
            print(f"[webhook] erro ao enviar email de confirmação: {e}")

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

        # Enviar imagem ao S3 com ContentType correto (sem ACL, compatível com buckets com ACL desativada)
        s3_client.upload_fileobj(
            image_bytes_for_s3,
            S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": "image/png"},
        )
        print("QR code enviado ao S3 com sucesso.")

        # Reposicionar o ponteiro novamente para o início para garantir que possa ser lido novamente
        image_bytes.seek(0)

        # Retornar o objeto BytesIO para que possa ser anexado no e-mail
        return image_bytes

    except Exception as e:
        print(f"Erro ao enviar o QR code ao S3: {e}")
        return None


# ----------------------
# Contato via AWS SES
# ----------------------
def send_contact_email_via_ses(name: str, email: str, subject: str, message: str) -> bool:
     """Envia e-mail de contato ao administrador usando AWS SES.
     Retorna True em caso de sucesso, False caso contrário.
     """
     try:
         region = os.environ.get("AWS_SES_REGION", "us-east-1")
         admin_email = os.environ.get("ADMIN_EMAIL", "contato@meueventoespecial.com.br")
         sender_email = os.environ.get("AWS_SES_SENDER", admin_email)

         ses_client = boto3.client("ses", region_name=region)

         body_text = (
             f"Mensagem de contato\n\n"
             f"Nome: {name}\n"
             f"E-mail: {email}\n"
             f"Assunto: {subject}\n\n"
             f"Mensagem:\n{message}\n"
         )
         body_html = (
             f"<h3>Mensagem de contato</h3>"
             f"<p><strong>Nome:</strong> {name}</p>"
             f"<p><strong>E-mail:</strong> {email}</p>"
             f"<p><strong>Assunto:</strong> {subject}</p>"
             f"<p style='white-space:pre-wrap'><strong>Mensagem:</strong><br>{message}</p>"
         )

         ses_client.send_email(
             Source=sender_email,
             Destination={"ToAddresses": [admin_email]},
             Message={
                 "Subject": {"Data": subject, "Charset": "UTF-8"},
                 "Body": {
                     "Text": {"Data": body_text, "Charset": "UTF-8"},
                     "Html": {"Data": body_html, "Charset": "UTF-8"},
                 },
             },
             ReplyToAddresses=[email] if email else [],
         )
         return True
     except Exception as e:
         print(f"Erro ao enviar e-mail via SES: {e}")
         return False

@app.route("/contact", methods=["GET", "POST"])
def contact():
     if request.method == "POST":
         name = request.form.get("name", "").strip()
         email = request.form.get("email", "").strip()
         subject = sanitize_html(request.form.get("subject", "").strip())
         message = sanitize_html(request.form.get("message", "").strip())

         if not name or not email or not subject or not message:
             flash("Por favor, preencha todos os campos.", "error")
             return redirect(url_for("contact"))

         if send_contact_email_via_ses(name, email, subject, message):
             flash("Mensagem enviada com sucesso!", "success")
         else:
             flash("Não foi possível enviar sua mensagem. Tente novamente.", "error")
         return redirect(url_for("contact"))

     return render_template("contact.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
