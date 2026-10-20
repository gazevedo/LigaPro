import { useState } from 'react';
import { Text, View } from 'react-native';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { useBankStore } from '../stores/screenStores';
import { useFinanceStore } from '../stores/financeStore';
import { financeService } from '../services/financeService';
import { ActionButton, Card, Field, GamePage, cents, money, palette, useAction } from '../components/GameUI';
import { ComboBox } from '../components/ComboBox';
const loanNames: Record<string, string> = { short_term: 'Curto prazo', medium_term: 'Médio prazo', long_term: 'Longo prazo' };
export function BankScreen() {
  const { data, loading, error, ensure, load, refresh } = useBankStore();
  const [amount, setAmount] = useState(''), [product, setProduct] = useState('short_term');
  const [payments, setPayments] = useState<Record<string, string>>({});
  const action = useAction();
  useScreenRefresh(ensure, refresh);
  async function reload() { await Promise.all([load(), useFinanceStore.getState().refresh()]); }
  const loans = [
    ...(data?.loans ?? []).filter(loan => loan.remaining_balance > 0).map(loan => ({ id: loan.id, name: loanNames[loan.product], balance: loan.remaining_balance, detail: `Contratado: ${money(loan.principal)} · ${loan.paid_installments ?? 0}/${loan.installments} parcelas pagas · ${loan.installments} parcelas · ${Math.round(loan.interest_rate * 100)}% de juros totais · Parcela de ${money(loan.installment_value)}`, date: loan.next_installment_at, legacy: false })),
    ...(data?.contracts ?? []).filter(loan => loan.type === 'bank_loan' && loan.status === 'active').map(loan => ({ id: loan.id, name: 'Empréstimo bancário', balance: loan.remaining_balance ?? loan.amount + loan.interest, detail: `Valor contratado: ${money(loan.amount)} · Juros: ${money(loan.interest)}`, date: loan.ends_at, legacy: true })),
  ];
  return <GamePage loading={loading} error={action.error || error}>
    <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Crédito disponível</Text>
      <Text style={{ fontSize: 26, fontWeight: '800', color: palette.primary }}>{money(data?.credit_limit ?? 0)}</Text>
      {Object.entries(data?.products ?? {}).map(([key, terms]) => <Text key={key}>{loanNames[key]}: {terms.installments} parcelas mensais · {Math.round(terms.interest_rate * 100)}% de juros totais</Text>)}
      <Text>Parcelas debitadas automaticamente no vencimento. Parcelas e antecipações podem deixar o caixa negativo.</Text>
    </Card>
    <Card><Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Solicitar empréstimo</Text>
      <Field label="Valor do empréstimo (R$)" value={amount} onChange={setAmount} numeric />
      <ComboBox label="Condições de pagamento" value={product} onChange={setProduct} options={Object.entries(data?.products ?? {}).map(([key, terms]) => ({ value: key, label: `${loanNames[key]} · ${terms.installments} parcelas · ${Math.round(terms.interest_rate * 100)}% de juros` }))} />
      <ActionButton title="Solicitar empréstimo" disabled={!data || data.credit_blocked || (data.credit_limit ?? 0) <= 0} onPress={() => void action.run(async () => { await financeService.loan(product, cents(amount)); await reload(); })} />
    </Card>
    <Card><Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Empréstimos ativos</Text>
      {loans.length === 0 && <Text>Nenhum empréstimo ativo.</Text>}
      {loans.map(loan => <View key={loan.id} style={{ gap: 12, paddingVertical: 12, borderTopWidth: 1, borderColor: palette.border }}>
        <Text style={{ fontWeight: '700', color: palette.ink }}>{loan.name}</Text><Text>{loan.detail}</Text>
        <Text>Saldo devedor: {money(loan.balance)}</Text>
        {loan.date && <Text>Próximo vencimento: {new Date(loan.date).toLocaleDateString('pt-BR')}</Text>}
        <Field label={`Valor para antecipar (R$) · ${loan.name}`} value={payments[loan.id] ?? ''} onChange={value => setPayments(current => ({ ...current, [loan.id]: value }))} numeric />
        <ActionButton secondary accessibilityLabel={`Antecipar pagamento · ${loan.name}`} title="Antecipar pagamento" onPress={() => void action.run(async () => {
          const payment = cents(payments[loan.id] ?? '');
          if (payment <= 0 || payment > loan.balance) throw new Error('Informe um valor maior que zero e até o saldo devedor.');
          if (loan.legacy) await financeService.settle(loan.id, payment); else await financeService.settleLoan(loan.id, payment);
          await reload();
        })} />
      </View>)}
    </Card>
  </GamePage>;
}
