# FTC — Fila Transparente Cidadã

Aplicação para consulta e administração de filas de regulação em saúde.

Este repositório é um monorepo composto por:

- `backend/`: API desenvolvida com Django e Django REST Framework;
- `frontend/`: aplicação web desenvolvida com Next.js.

## Estrutura do projeto

```text
.
├── backend/
│   ├── config/            # Configurações do Django
│   ├── ftc/               # Aplicação, modelos, serviços, rotas e testes
│   ├── .env.example       # Exemplo das variáveis do backend
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── public/            # Arquivos estáticos
│   ├── src/               # Páginas, componentes e integração com a API
│   ├── .env.example       # Exemplo das variáveis do frontend
│   └── package.json
└── README.md
```

## Requisitos

Antes de começar, instale:

- Git;
- Python 3.10 ou superior;
- Node.js e npm;
- PostgreSQL, caso o backend esteja configurado para usar um banco local.

## Clonando o repositório

```bash
git clone URL_DO_REPOSITORIO
cd NOME_DO_REPOSITORIO
```

## Configurando o backend

Entre na pasta do backend:

```bash
cd backend
```

Crie um ambiente virtual:

```bash
python -m venv venv
```

No Windows PowerShell, ative-o com:

```powershell
.\venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação, permita a execução somente na sessão atual e
tente novamente:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

No Git Bash:

```bash
source venv/Scripts/activate
```

No Linux ou macOS:

```bash
source venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o arquivo local de variáveis de ambiente a partir do exemplo:

```powershell
Copy-Item .env.example .env
```

No Linux ou macOS:

```bash
cp .env.example .env
```

Revise o `.env` e informe, principalmente, a chave secreta e os dados de conexão
com o banco. O arquivo contém também as configurações de CORS, limites de requisição,
tokens JWT, importação de PDF e segurança.

Execute as migrations:

```bash
python manage.py migrate
```

Se precisar acessar o painel administrativo, crie um superusuário:

```bash
python manage.py createsuperuser
```

Inicie a API:

```bash
python manage.py runserver
```

O backend ficará disponível em:

- API: <http://127.0.0.1:8000/>;
- Django Admin: <http://127.0.0.1:8000/admin/>;
- Swagger: <http://127.0.0.1:8000/api/docs/>;
- Redoc: <http://127.0.0.1:8000/api/redoc/>.

## Configurando o frontend

Em outro terminal, partindo da raiz do repositório, entre na pasta do frontend:

```bash
cd frontend
```

Instale as dependências:

```bash
npm install
```

Crie o arquivo local de variáveis de ambiente:

```powershell
Copy-Item .env.example .env
```

No Linux ou macOS:

```bash
cp .env.example .env
```

Por padrão, o frontend espera encontrar o Django em:

```env
DJANGO_API_URL=http://localhost:8000
```

Inicie o servidor de desenvolvimento:

```bash
npm run dev
```

A aplicação ficará disponível em <http://localhost:3000/>.

As chamadas feitas pelo navegador usam o proxy de mesma origem
`/api/backend/*`. Por isso, os caminhos declarados em
`frontend/src/lib/api-routes.ts` devem conter o prefixo completo `/api/` das
rotas do Django. O cliente mantém os tokens de acesso e atualização, renova a
sessão após respostas `401` e invalida o refresh token no logout.

## Dados de desenvolvimento

O seeder cria dados de fila e duas contas de desenvolvimento:

```powershell
cd backend
python manage.py database_seeder
```

- administrador: `servidor.saude` / `SenhaForte123!`;
- cidadão: `10000000001` / `SenhaCidadao123!`;
- CNS do cidadão de exemplo: `700000000000001`.

As contas são criadas ou atualizadas de forma idempotente. As credenciais podem
ser substituídas sem editar código:

```powershell
python manage.py database_seeder `
  --admin-username outro.admin `
  --admin-password OutraSenhaForte123! `
  --cidadao-cpf 10000000002 `
  --cidadao-password OutraSenhaCidadao123!
```

Essas credenciais destinam-se somente ao ambiente de desenvolvimento.

## Autenticação administrativa

O login administrativo utilizado pelo frontend é feito pela API:

```text
POST /api/admin/auth/login/
```

Esse endpoint retorna tokens JWT e não corresponde ao login do Django Admin. A
API espera o token no cabeçalho `Authorization: Bearer <access_token>`; cookies e
sessões do Django não são usados pelo frontend.

O cadastro de usuários administrativos é feito em:

```text
POST /api/admin/users/
```

O primeiro superusuário deve ser criado com `python manage.py createsuperuser`.
Depois disso, somente um superusuário autenticado pode cadastrar outros usuários
administrativos pela API. O cadastro exige `username` e `password`; `email`,
`first_name` e `last_name` são opcionais. O usuário deve estar ativo e possuir
`is_staff=True`.

## Atualização administrativa da fila por PDF

Funcionários autenticados com `is_staff=True` podem substituir a fila publicada:

```text
POST /api/admin/filas/atualizar/
```

A requisição usa `multipart/form-data` e recebe:

- `arquivo`: PDF da lista de regulação;
- `especialidade`: ID de uma especialidade ativa;
- `competencia`: mês no formato `AAAA-MM`;
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

O importador exige uma tabela com data da solicitação, nome do usuário, ano de
nascimento, CNS, sexo, código da solicitação e posição. O título do relatório
deve corresponder ao tipo e ao nome da especialidade selecionada. Nomes e CNS são
mascarados novamente pela API antes da publicação.

O PDF inteiro é validado antes de qualquer troca. Em caso de sucesso, a publicação
anterior da especialidade passa para `ARQUIVADA`, a nova passa para `PUBLICADA` e
somente os novos registros aparecem na API pública. A versão arquivada permanece
no banco para auditoria. Um PDF inválido ou duplicado, ou uma falha de gravação,
não altera a fila vigente.

## Acesso do cidadão

O login do cidadão usa uma conta Django comum, com `is_staff=False`, cujo
`username` deve ser exatamente o CPF com 11 dígitos de um registro existente em
`Paciente`. Essa vinculação impede que uma conta consulte filas de outro CPF.

Endpoints utilizados pelo frontend:

- `POST /api/auth/cidadao/register/`;
- `POST /api/auth/cidadao/login/`;
- `POST /api/auth/cidadao/refresh/`;
- `POST /api/auth/cidadao/logout/`;
- `GET /api/auth/cidadao/me/`;
- `GET /api/cidadao/filas/`.

A conta pode ser criada pela API depois que o paciente já existir. O CPF e o CNS
devem ser enviados sem pontuação e corresponder ao mesmo paciente:

```json
{
  "cpf": "10000000001",
  "cns": "700000000000001",
  "password": "NovaSenhaCidadao123!",
  "password_confirmation": "NovaSenhaCidadao123!"
}
```

O endpoint cria somente contas comuns (`is_staff=False`). Contas administrativas
continuam sendo cadastradas por um superusuário em `POST /api/admin/users/`.

## Testes e verificações

Para verificar o backend:

```bash
cd backend
python manage.py check
python manage.py test
```

Para verificar o frontend:

```bash
cd frontend
npm run lint
npm run build
```

## Atualizando dependências

Ao adicionar uma dependência Python, atualize o arquivo do backend:

```bash
cd backend
pip freeze > requirements.txt
```

As dependências do frontend devem ser instaladas com `npm install`, mantendo
`package.json` e `package-lock.json` versionados.

## Fluxo de desenvolvimento

Execute os comandos Git na raiz do monorepo. Antes de começar:

```bash
git pull
```

Depois das alterações:

```bash
git status
git add .
git commit -m "descrição da alteração"
git push
```

Não envie ao repositório arquivos `.env`, ambientes virtuais, bancos locais,
`node_modules` ou artefatos de build. Os arquivos `.gitignore` dentro de
`backend/` e `frontend/` protegem esses conteúdos em seus respectivos projetos.
