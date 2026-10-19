# AGENTS.md

## Projeto

Jogo mobile de gerenciamento de futebol estilo Brasfoot.

Stack principal:

- Backend: Python
- Banco: MongoDB
- Cliente mobile
- Dados locais podem ser usados para reduzir consultas ao servidor

## Regra principal

Execute somente o que foi solicitado.

Não amplie o escopo da tarefa.

## Uso de contexto

Antes de alterar código:

1. Localize somente os arquivos diretamente relacionados à tarefa.
2. Não percorra o repositório inteiro sem necessidade.
3. Não leia diretórios sem relação com a funcionalidade solicitada.
4. Reutilize implementações existentes sempre que possível.
5. Consulte documentação adicional apenas quando necessária para executar a tarefa.

## Alterações

Faça a menor alteração possível para cumprir o requisito.

Não:

- refatore código fora do escopo;
- renomeie arquivos sem necessidade;
- reorganize pastas sem necessidade;
- altere APIs existentes sem necessidade;
- altere modelos não relacionados;
- crie funcionalidades extras;
- faça melhorias não solicitadas;
- gere documentação extensa.

Preserve compatibilidade com o código existente.

## Arquitetura

Antes de criar:

- novo service;
- repository;
- controller;
- model;
- utilitário;
- endpoint;

procure se já existe componente equivalente.

Evite duplicação.

## Banco de dados

MongoDB é o banco principal.

Evite:

- consultas desnecessárias;
- múltiplas consultas quando uma consulta resolver;
- gravações redundantes;
- carregar documentos completos quando apenas alguns campos forem necessários.

Considere cache ou persistência local quando isso reduzir tráfego sem comprometer consistência.

## Regras importantes do jogo

O universo do jogo continua funcionando mesmo quando o usuário está offline.

Partidas devem ocorrer mesmo se um dos jogadores não estiver conectado.

O cliente pode armazenar informações localmente para reduzir consultas ao servidor.

Campeonatos:

- 20 clubes por divisão;
- sempre deve existir ao menos uma série ativa e completa, mesmo formada apenas por bots;
- ao esgotar as vagas de bots da última série, prepare a próxima com 20 bots;
- acessos e rebaixamentos devem manter todas as séries com 20 clubes; crie a série inferior quando necessária;
- não extinga uma série por ausência de técnicos humanos;
- clubes bots ocupam vagas disponíveis;
- novos usuários podem substituir bots;
- sem vaga disponível, o usuário entra em divisão inferior.

Elenco inicial:

- 25 jogadores;
- posições: GOL, DEF, MED e ATA.

Não altere regras de negócio existentes sem solicitação explícita.

## Testes

Execute somente testes relacionados à alteração.

Evite executar toda a suíte quando testes específicos forem suficientes.

Se não houver testes para a área modificada, crie apenas os testes necessários para validar a alteração solicitada.

## Dependências

Não adicione bibliotecas externas se a funcionalidade puder ser implementada adequadamente com dependências existentes ou biblioteca padrão.

Antes de adicionar dependência:

- verifique se já existe solução no projeto;
- confirme que ela é realmente necessária.

## Saída

Ao concluir, responda de forma curta.

Informe apenas:

- o que foi alterado;
- arquivos alterados;
- testes executados;
- algum problema relevante, se existir.

Não explique código linha por linha.

## Controle de escopo

Se encontrar outro problema não relacionado à tarefa:

- não corrija;
- apenas mencione brevemente ao final, se for relevante.

## Prioridade

Priorize nesta ordem:

1. Correção funcional
2. Manter regras existentes
3. Alterar o mínimo de código
4. Reutilizar código existente
5. Reduzir consultas e processamento desnecessários
6. Manter código simples

## Instrução para tarefas pequenas

Para correções simples, não faça análise ampla da arquitetura.

Localize o ponto necessário, faça a correção e valide.

## Instrução para tarefas grandes

Para funcionalidades maiores:

1. Identifique os componentes envolvidos.
2. Trabalhe apenas nesses componentes.
3. Implemente por etapas pequenas.
4. Valide cada etapa.
5. Evite modificar módulos não relacionados.

## Git

Trabalhe sempre na branch `main`. Não crie novas branches.

Ao concluir qualquer alteração:

- incremente sempre a versão em `mobile/version.json`, usando `mobile/scripts/bump-version.cjs` (patch por padrão);
- inclua o incremento de versão no mesmo commit da alteração;
- execute as validações relacionadas antes do commit;
- faça sempre commit e push para `origin/main`;
- confirme o resultado do push antes de informar que o trabalho foi publicado no GitHub;
- se o commit ou push falhar, informe o impedimento; não declare a publicação concluída.

O workflow de versão já reconhece incrementos incluídos no commit; não duplique o incremento automático.

## Experiência de uso

As ações não podem bloquear a tela nem impedir novas edições enquanto salvam.
Atualize a interface imediatamente e salve em background, preservando a última escolha.
Serialize gravações relacionadas para evitar respostas antigas sobrescrevendo alterações novas.
Em caso de falha, informe o erro sem bloquear a tela e preserve ou restaure o último estado confirmado.
Bloqueie controles apenas por regras do jogo, como jogadores lesionados ou suspensos, nunca pela gravação em andamento.

Mensagens de erro, aviso e confirmação devem usar o componente compartilhado NotificationBubble, com opção de fechar. Não use texto solto, alertas nativos ou popups para essas mensagens. Falhas de atualização da próxima partida devem ser silenciosas, preservando os dados já carregados.
