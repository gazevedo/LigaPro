# Revisão das branches do Dependabot

Em 06/10/2026, o remoto tinha seis branches contando a `main`. As outras cinco
continham somente atualizações de dependências mobile, sem funcionalidades novas.
Seus commits foram integrados ao histórico da `main`, sem criar branches locais.
As versões incompatíveis foram mantidas nas versões suportadas pelo Expo 57.

| Branch (prefixo `dependabot/npm_and_yarn/mobile/`) | Proposta | Resultado |
| --- | --- | --- |
| `multi-7f19880bf6` | React e tipos 19.3 | React 19.2.3 e tipos 19.2: renderizador embarcado no React Native 0.86.3 usa React 19.2.3. |
| `react-test-renderer-19.3.0` | Renderizador React 19.3 | 19.2.3: deve acompanhar a versão de React. |
| `react-native-screens-4.28.0` | Screens 4.28 | 4.26: verificação do Expo exige `~4.26.0`. |
| `test-renderer-1.3.0` | Test renderer 1.3 | 1.2: 1.3 instala react-reconciler 0.34, cujo peer requer React 19.3. |
| `typescript-7.0.2` | TypeScript 7 | 5.9: a versão 7 quebra o lint do Expo (`TypeFlags.Intrinsic`) e a descoberta dos tipos de Jest/Node. |

O Dependabot passa a usar `open-pull-requests-limit: 0` para atualizações de versões
npm e pip. Alertas/atualizações de segurança têm configuração separada no GitHub.
As branches remotas não foram excluídas.
