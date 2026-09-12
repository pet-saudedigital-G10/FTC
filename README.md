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

Este endpoint retorna JWT e **nao** e uma rota do Django Admin. A API aceita
autenticacao exclusivamente pelo header `Authorization: Bearer <access_token>`;
cookies e sessoes Django nao sao usados pelo frontend.

Cadastro de usuario administrativo:

POST http://127.0.0.1:8000/api/admin/users/

O primeiro superusuario deve ser criado com `python manage.py createsuperuser`.
Depois disso, somente um superusuario autenticado pode cadastrar outros usuarios
administrativos pela API. O cadastro exige `username` e `password`; `email`,
`first_name` e `last_name` sao opcionais.

O usuario precisa estar ativo e com `is_staff=True`. Para invalidar refresh tokens no
logout, rode as migrations depois de instalar as novas dependencias:

python manage.py migrate

### Atualizacao administrativa da fila por PDF

Funcionarios autenticados com `is_staff=True` podem substituir a fila publicada:

`POST /api/admin/filas/atualizar/`

A requisicao usa `multipart/form-data` e recebe:

- `arquivo`: PDF da lista de regulacao;
- `especialidade`: ID de uma especialidade ativa;
- `competencia`: mes no formato `AAAA-MM`;
- `observacao`: texto opcional para auditoria.

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/admin/filas/atualizar/ \
  -H "Authorization: Bearer <access_token>" \
  -F "arquivo=@fila-pediatria.pdf;type=application/pdf" \
  -F "especialidade=1" \
  -F "competencia=2026-04" \
  -F "observacao=Atualizacao mensal"
```

O importador exige a tabela com data da solicitacao, nome do usuario, ano de
nascimento, CNS, sexo, codigo da solicitacao e posicao. O titulo do relatorio deve
corresponder ao tipo e ao nome da especialidade selecionada. Nomes e CNS sao
mascarados novamente pela API antes da publicacao.

O PDF inteiro e validado antes de qualquer troca. Em caso de sucesso, a publicacao
anterior da especialidade passa para `ARQUIVADA`, a nova passa para `PUBLICADA` e
somente os novos registros aparecem na API publica. A versao arquivada permanece no
banco para auditoria. PDF invalido, duplicado ou uma falha de gravacao nao altera a
fila vigente. Os registros publicos incluem `publicada_em`, que informa a data e a
hora da ultima atualizacao visivel.

### Acesso do cidadao

O login do cidadao usa uma conta Django comum (`is_staff=False`) cujo `username`
deve ser exatamente o CPF com 11 digitos de um registro existente em `Paciente`.
Essa vinculacao impede que uma conta consulte filas de outro CPF.

Endpoints usados pelo frontend:

- `POST /api/auth/cidadao/login/`
- `POST /api/auth/cidadao/refresh/`
- `POST /api/auth/cidadao/logout/`
- `GET /api/auth/cidadao/me/`
- `GET /api/cidadao/filas/`

A conta pode ser criada pelo Django Admin: informe o CPF sem pontuacao como nome
de usuario, defina uma senha e mantenha as permissoes de equipe e superusuario
desmarcadas. O paciente com esse CPF precisa existir antes do primeiro login.

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
