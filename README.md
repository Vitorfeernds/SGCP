# S.G.C.P - Sistema de Gestao e Controle de Pedidos

Sistema desktop para gestao de pedidos, mesas, cardapio e usuarios de um estabelecimento. O projeto foi desenvolvido em Python com interface Tkinter e possui persistencia em MongoDB, com fallback para arquivos JSON locais.

## Funcionalidades

- Login com perfis de usuario: administrador e atendente.
- Dashboard com resumo de pedidos, mesas ocupadas e faturamento.
- Cadastro, visualizacao e controle de pedidos.
- Atualizacao de status dos pedidos.
- Gestao de cardapio para administradores.
- Cadastro e edicao de receitas, categorias, precos, disponibilidade e ficha tecnica.
- Suporte a tema claro/escuro.
- Persistencia em MongoDB ou arquivos JSON locais.

## Tecnologias

- Python
- Tkinter
- MongoDB
- PyMongo
- JSON local como fallback

## Requisitos

- Python 3.10 ou superior
- MongoDB local ou MongoDB Atlas, se quiser usar banco de dados
- MongoDB Compass, opcional, para visualizar os dados
- Pacote `pymongo`

Instale a dependencia principal:

```bash
pip install pymongo
```

## Como Executar

Na pasta do projeto, execute:

```bash
python sgcp.py
```

No Windows, dependendo da instalacao do Python, tambem pode ser:

```bash
py sgcp.py
```

## Login Padrao

Atendente:

```text
E-mail: atendente@guanambusiness.com
Senha: 123456
```

Administrador:

```text
E-mail: admin@guanambusiness.com
Senha: admin123
```

Altere essas credenciais antes de usar o sistema em producao.

## Configuracao do MongoDB

O sistema le as configuracoes do arquivo:

```text
data/.env
```

Exemplo para MongoDB local:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB=sgcp
```

Exemplo para MongoDB Atlas:

```env
MONGO_URI=mongodb+srv://usuario:senha@cluster.mongodb.net
MONGO_DB=sgcp
```

Depois de alterar o `.env`, reinicie o aplicativo.

## Como Configurar o MongoDB Compass

Para MongoDB local:

1. Abra o MongoDB Compass.
2. Clique em `New Connection`.
3. Use a URI:

```text
mongodb://localhost:27017
```

4. Clique em `Connect`.
5. Abra o banco:

```text
sgcp
```

6. Verifique as colecoes:

```text
usuarios
pedidos
cardapio
```

Para MongoDB Atlas, copie a connection string no painel do Atlas e cole no Compass.

## Estrutura Principal

```text
SGCP/
├── sgcp.py
├── data/
│   ├── .env
│   ├── usuarios.json
│   ├── pedidos.json
│   ├── cardapio.json
│   └── theme.json
└── .gitignore
```

## Persistencia de Dados

Quando o MongoDB esta configurado corretamente, o sistema salva dados nas colecoes:

- `usuarios`
- `pedidos`
- `cardapio`

Se o MongoDB nao estiver disponivel, o sistema usa os arquivos JSON dentro da pasta `data/`.

Os arquivos `pedidos.json` e `cardapio.json` devem conter JSON valido. Se estiverem vazios, use:

```json
[]
```

## Modelo de Documento do Cardapio

Cada documento da colecao `cardapio` deve seguir este formato:

```json
{
  "categoria": "Bebidas",
  "itens": [
    {
      "nome": "Coca-Cola",
      "preco": 7.0,
      "tempo": "2 min",
      "disponivel": true,
      "cor": "#374151",
      "ingredientes": [],
      "modo": []
    }
  ]
}
```

## Arquivos Sensíveis

Nao envie arquivos com dados sensiveis para o GitHub:

```text
data/
*.json
*.env
__pycache__/
```

O `.gitignore` deve conter:

```gitignore
data/
*.json
*.env
__pycache__/
```

Se alguma senha de MongoDB Atlas foi colocada diretamente no codigo, remova essa senha, gere uma nova no Atlas e use apenas o arquivo `data/.env`.

## Solucao de Problemas

Se o aplicativo fechar ao abrir o cardapio:

- Confira se `data/cardapio.json` nao esta vazio.
- Use `[]` como conteudo inicial do arquivo.
- Confira se os documentos da colecao `cardapio` possuem `categoria` e `itens`.
- Confira se cada item possui `nome`, `preco`, `disponivel` e `cor`.

Se o cardapio nao atualizar no MongoDB:

- Verifique se `MONGO_URI` esta ativo no `data/.env`.
- Verifique se o banco correto no Compass e `sgcp`.
- Reinicie o aplicativo apos alterar o `.env`.
- Confirme se o sistema esta mostrando `MongoDB` na tela de login.

Se houver piscada ao trocar de abas:

- Remova a animacao de fade baseada em `self.attributes("-alpha", ...)`.
- Renderize a nova tela diretamente pela funcao de navegacao.

## Status do Projeto

Projeto em desenvolvimento para uso local/desktop.

## Licenca

Defina aqui a licenca do projeto antes de publicar no GitHub.
