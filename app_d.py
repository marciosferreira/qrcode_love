import boto3
from botocore.exceptions import ClientError
import time

# Configura o cliente DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Use a região correta
client = boto3.client('dynamodb', region_name='us-east-1')  # Cliente para verificar a existência da tabela

# Função para verificar se a tabela já existe
def table_exists(table_name):
    try:
        response = client.describe_table(TableName=table_name)
        return True  # Se a tabela existir, retorna True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False  # A tabela não existe
        else:
            print(f"Erro ao verificar a existência da tabela: {e}")
            raise

# Função para criar a tabela
def create_table():
    table_name = 'CoupleTable'
    
    if table_exists(table_name):
        print(f"Tabela '{table_name}' já existe. Pulando criação.")
        return dynamodb.Table(table_name)
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,  # Nome da tabela
            KeySchema=[
                {'AttributeName': 'email', 'KeyType': 'HASH'},  # Partition key
                {'AttributeName': 'page_url', 'KeyType': 'RANGE'}  # Sort key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'},
                {'AttributeName': 'page_url', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("Criando tabela, aguarde...")
        # Aguarda até que a tabela seja criada
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print("Tabela criada com sucesso!")
        time.sleep(5)
    except ClientError as e:
        print(f"Erro ao criar tabela: {e}")
    return dynamodb.Table(table_name)

# Função para inserir um registro na tabela
def insert_example_item(table):
    try:
        table.put_item(
            Item={
                'email': 'exemplo@exemplo.com',
                'page_url': 'abc123',
                'name1': 'John',
                'name2': 'Jane',
                'event_date': '2024-10-08',
                'event_description': 'Casamento',
                'optional_message': 'Mensagem especial',
                'created_at': '2024-09-01T12:00:00Z',
                'paid': False
            }
        )
        print("Registro inserido com sucesso!")
    except ClientError as e:
        print(f"Erro ao inserir item: {e}")

# Função para recuperar o registro diretamente da tabela
def get_item_from_table(table):
    try:
        response = table.get_item(
            Key={
                'email': 'exemplo@exemplo.com',
                'page_url': 'abc123'
            }
        )
        item = response.get('Item')
        if item:
            print("Item recuperado da tabela:")
            print(item)
        else:
            print("Item não encontrado.")
    except ClientError as e:
        print(f"Erro ao recuperar item: {e}")

if __name__ == "__main__":
    # Cria a tabela se ela não existir
    couple_table = create_table()

    # Insere um registro de exemplo
    insert_example_item(couple_table)

    # Recupera o registro diretamente da tabela
    get_item_from_table(couple_table)
