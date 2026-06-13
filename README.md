# FTC Backend - Fila Transparente Cidadã

Backend do projeto **Fila Transparente Cidadã**, desenvolvido com **Django** e **Django REST Framework**.

Este guia explica como configurar o ambiente local após clonar o repositório.

---

## Requisitos necessários

Antes de começar, verifique se você tem instalado:

- Python 3.10 ou superior
- Git
- VS Code ou outro editor de código
- PostgreSQL, caso o projeto já esteja configurado para usar banco local

Para verificar se o Python está instalado:

python --version

ou:

py --version

---

## 1. Clonar o repositório

No terminal, execute:

git clone URL_DO_REPOSITORIO

Depois entre na pasta do projeto:

cd NOME_DA_PASTA_DO_REPOSITORIO

---

## 2. Criar o ambiente virtual

Dentro da pasta do projeto, crie um ambiente virtual:

python -m venv venv

Caso o comando acima não funcione no Windows, tente:

py -m venv venv

---

## 3. Ativar o ambiente virtual

No Windows PowerShell:

.\venv\Scripts\Activate.ps1

Caso apareça erro de permissão, execute:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

Depois tente ativar novamente:

.\venv\Scripts\Activate.ps1

Se estiver usando Git Bash:

source venv/Scripts/activate

No Linux/Mac:

source venv/bin/activate

Quando o ambiente virtual estiver ativo, aparecerá algo parecido com isto no terminal:

(venv)

---

## 4. Instalar as dependências

Com o ambiente virtual ativo, instale as dependências do projeto:

pip install -r requirements.txt

---

## 5. Configurar variáveis de ambiente

Crie um arquivo chamado `.env` na raiz do projeto.

Exemplo:

DEBUG=True
SECRET_KEY=sua_chave_secreta_aqui

DB_NAME=ftc_db
DB_USER=postgres
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432

Atenção: o arquivo `.env` não deve ser enviado para o GitHub.

Cada membro da equipe deve criar o próprio `.env` localmente.

---

## 6. Rodar as migrations

Depois de instalar as dependências e configurar o banco, execute:

python manage.py migrate

---

## 7. Criar um superusuário

Para acessar o painel administrativo do Django, crie um superusuário:

python manage.py createsuperuser

Informe usuário, e-mail e senha quando solicitado.

---

## 8. Rodar o servidor local

Execute:

python manage.py runserver

O servidor ficará disponível em:

http://127.0.0.1:8000/

O painel administrativo do Django fica em:

http://127.0.0.1:8000/admin/

Swagger da API:

http://127.0.0.1:8000/api/docs/

Redoc da API:

http://127.0.0.1:8000/api/redoc/

Login administrativo para o dashboard da secretaria:

POST http://127.0.0.1:8000/api/admin/auth/login/

Cadastro de usuario administrativo:

POST http://127.0.0.1:8000/api/admin/users/

O primeiro superusuario deve ser criado com `python manage.py createsuperuser`.
Depois disso, somente um superusuario autenticado pode cadastrar outros usuarios
administrativos pela API. O cadastro exige `username` e `password`; `email`,
`first_name` e `last_name` sao opcionais.

O usuario precisa estar ativo e com `is_staff=True`. Para invalidar refresh tokens no
logout, rode as migrations depois de instalar as novas dependencias:

python manage.py migrate

---

## 9. Atualizar dependências

Sempre que alguém instalar uma nova biblioteca no projeto, deve atualizar o arquivo `requirements.txt` com:

pip freeze > requirements.txt

Depois disso, o arquivo deve ser commitado no Git.

Quando outro membro da equipe puxar atualizações do repositório, deve rodar novamente:

pip install -r requirements.txt

---

## Fluxo recomendado para trabalhar no projeto

Antes de começar a codar:

git pull

Depois de fazer alterações:

git status
git add .
git commit -m "descrição da alteração"
git push

---

## Observações importantes

- Sempre ativar o ambiente virtual antes de rodar comandos do Django.
- Não enviar a pasta `venv` para o GitHub.
- Não enviar o arquivo `.env` para o GitHub.
- Manter o `requirements.txt` atualizado.
- Antes de criar novas funcionalidades, verificar se a branch local está atualizada.
