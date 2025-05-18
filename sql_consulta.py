import pymysql

# Parâmetros de conexão
writer_endpoint = "database-1.cluster-c78coese2dbv.us-east-1.rds.amazonaws.com"  # Endpoint de gravação
username = "admin"
password = "cpfl2002"
database = "meu_novo_banco"
port = 3306

# Função para conectar ao banco de dados e listar os dados
def listar_tudo(tabela):
    # Conectar ao banco de dados usando pymysql
    connection = pymysql.connect(
        host=writer_endpoint,
        user=username,
        password=password,
        db=database,
        port=port
    )
    
    try:
        with connection.cursor() as cursor:
            # Executar uma query para listar todos os dados da tabela
            sql_query = f"SELECT * FROM {tabela};"
            cursor.execute(sql_query)
            
            # Pegar todos os resultados da query
            resultados = cursor.fetchall()
            
            # Exibir os resultados
            if resultados:
                print(f"Dados da tabela '{tabela}':")
                for row in resultados:
                    print(row)
            else:
                print(f"Nenhum dado encontrado na tabela '{tabela}'.")

    except Exception as e:
        print(f"Erro ao conectar ao banco de dados ou listar dados: {e}")
    
    finally:
        connection.close()

# Nome da tabela que deseja listar
tabela = "couple"  # Substitua pelo nome da tabela que você deseja listar

# Chamar a função para listar todos os dados da tabela
listar_tudo(tabela)
