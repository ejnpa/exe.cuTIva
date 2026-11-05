import os
from azure.storage.blob import BlobServiceClient

connection_string = os.environ["AZURITE_CONNECTION_STRING"]

try:
    print("A ligar ao Azurite no Desktop via Tailscale...")
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # Tenta criar um contentor de teste
    nome_contentor = "teste-ligacao"
    container_client = blob_service_client.get_container_client(nome_contentor)
    
    if not container_client.exists():
        container_client.create_container()
        print(f"✅ SUCESSO! Contentor '{nome_contentor}' criado no desktop.")
    else:
        print(f"✅ SUCESSO! Ligação estabelecida. O contentor '{nome_contentor}' já existe.")

except Exception as e:
    print(f"❌ ERRO de ligação: {e}")
