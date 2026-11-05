import os
from executiva.storage.interface import StorageInterface
from executiva.storage.providers.azure import AzureStorage
from executiva.storage.providers.gcp import GCPStorage
from executiva.storage.providers.local import LocalStorage


def get_storage_provider() -> StorageInterface:
    """Lê CLOUD_PROVIDER e cria o adaptador de armazenamento correspondente.
    Lança ValueError se o fornecedor configurado não for LOCAL, GCP ou AZURE.
    """
    provider = os.getenv("CLOUD_PROVIDER", "AZURE").upper()

    providers: dict[str, type[StorageInterface]] = {
        "LOCAL": LocalStorage,
        "GCP": GCPStorage,
        "AZURE": AzureStorage,
    }

    storage_class = providers.get(provider)
    if storage_class is None:
        valid_providers = ", ".join(providers)
        raise ValueError(
            f"CLOUD_PROVIDER inválido: {provider}. "
            f"Valores possíveis: {valid_providers}."
        )
    return storage_class()