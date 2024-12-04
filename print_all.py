import boto3
from botocore.exceptions import ClientError

# Configura o cliente DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Use a região correta

# Função para listar e printar todos os itens da tabela
def list_all_items(table_name):
    table = dynamodb.Table(table_name)
    
    try:
        response = table.scan()  # Recupera todos os itens da tabela
        items = response.get('Items', [])
        
        if items:
            print("Itens existentes na tabela:")
            for item in items:
                print(item)
        else:
            print("Nenhum item encontrado na tabela.")
    except ClientError as e:
        print(f"Erro ao listar itens: {e}")

if __name__ == "__main__":
    # Nome da tabela a ser consultada
    table_name = 'CoupleTable'
    
    # Lista e printa todos os itens da tabela
    list_all_items(table_name)
