### Integracoes Customizadas

Modulo de integracoes customizadas para o ERPNext

### Notificações por WhatsApp

1. Abra **Configuracoes WhatsApp** no Desk e informe a URL base da Evolution API v2, a chave global da API e o nome da instância. Salve.
2. Clique em **Criar instância**, depois em **Gerar novo QR Code**. Escaneie o código no WhatsApp em **Aparelhos conectados** e use **Atualizar estado** para confirmar a conexão. O mesmo botão gera um novo QR Code caso a sessão precise ser renovada.
3. Nas regras **Notification** desejadas, marque **Enviar também por WhatsApp**. Os usuários já selecionados pela regra receberão o assunto e a mensagem no campo **Celular / mobile_no** do cadastro de usuário.
4. Consulte **Envio WhatsApp** para ver o resultado por usuário. Registros com estado **Falhou** podem ser reenviados pelo botão **Reenviar**.

Números brasileiros com DDD recebem o prefixo 55 automaticamente. Números internacionais precisam estar completos com `+` e código do país. A primeira versão envia somente texto. A configuração e os registros de envio são restritos a administradores do sistema.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app integracoes_customizadas
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/integracoes_customizadas
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
