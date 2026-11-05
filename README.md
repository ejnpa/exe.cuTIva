# exe.cuTIva - Plataforma de partilha de Apontamentos 

Uma plataforma para gestão, organização e partilha de apontamentos académicos. Este repositório contém o código base da aplicação
(Backend e Frontend),desenvolvido para funcionar num ambiente local.

## Sobre o Projeto

O **exe.cuTIva** surgiu da necessidade de centralizar e organizar o conhecimento gerado durante o percurso académico. 
Num ambiente de ensino superior, a quantidade de material de estudo, desde apontamentos de aulas teóricas a guiões de projetos práticos,
cresce rapidamente a cada semestre. Este projeto foi desenvolvido com o objetivo de criar uma plataforma dedicada onde os estudantes podem
não só estruturar os seus próprios materiais por curso, ano e disciplina,
mas também facilitar a partilha de recursos e resumos fundamentais para a preparação de frequências e exames.
Mais do que um simples gestor de ficheiros, é uma ferramenta pensada para otimizar o estudo,
resolver o problema da informação dispersa e promover a colaboração académica.

## Stack Tecnológica

* **Backend:** Python 3.11, FastAPI, Uvicorn
* **Base de Dados:** SQLite (persistência local)
* **Frontend:** HTML, CSS, JavaScript (Vanilla)
* **Autenticação:** JSON Web Tokens (JWT) e hashing de passwords (Bcrypt)

## Funcionalidades

* **Sistema de Utilizadores:** Registo e autenticação segura de contas.
* **Gestão de Apontamentos:** Estruturação de dados académicos (Escola, Curso, Ano, Disciplina).
* **Upload de Ficheiros:** Processamento e receção de ficheiros PDF.
* **Processamento de Imagens:** Geração automática de miniaturas/capas para os documentos submetidos.
* **API RESTful:** Endpoints estruturados para comunicação fluída com o frontend.

## Configuração de segurança

Define `SECRET_KEY` no ambiente da API com um valor aleatório e persistente (por exemplo, gerado com `python -c "import secrets; print(secrets.token_urlsafe(48))"`). A aplicação não inicia sem esta variável. `COOKIE_SECURE` é `true` por omissão; para desenvolvimento local por HTTP, define `COOKIE_SECURE=false`.

Ao atualizar uma instalação antiga, depois de iniciar a nova versão executa uma vez `docker exec executiva_api python -m scripts.migrate_saved_artifacts` para copiar os itens guardados da tabela antiga para o esquema atual. A tabela antiga fica preservada.
