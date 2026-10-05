import { useEffect, useState } from 'react';
import { Button, Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Player } from '../types/game';
import { contractService, ContractView } from '../services/contractService';
import { marketService } from '../services/marketService';
import { useClubStore } from '../stores/clubStore';
import { Choices, Field, GamePage, cents, money, useAction } from '../components/GameUI';
export function PlayerDetailsScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'PlayerDetails'>) {
  const [player, setPlayer] = useState<Player | null>(null), [listing, setListing] = useState<Player['listing']>(null), [amount, setAmount] = useState(''), [days, setDays] = useState('30'), [type, setType] = useState('sale');
  const [contract, setContract] = useState<ContractView | null>(null), [salary, setSalary] = useState(''), [seasons, setSeasons] = useState('2');
  const club = useClubStore(state => state.data?.club?.id), action = useAction();
  async function load() { const p = await marketService.player(route.params.id); setPlayer(p); setListing(p.listing); if (p.owner_club_id === club) { const data = await contractService.get(p.id); setContract(data); setSalary(((data.contract?.salary ?? (p.strength ?? p.overall) * 100) / 100).toFixed(2)); } else { setContract(null); setSalary(((p.strength ?? p.overall) * 100 / 100).toFixed(2)); } }
  useEffect(() => { void action.run(load); }, [route.params.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}>{player && <><Text style={{ fontSize: 24 }}>{player.name}</Text><Text>{player.position} · {player.age} anos · overall {player.overall} · {money(player.value)} · {player.country_id}</Text>{player.owner_club_id && <Button title="Clube proprietário" onPress={() => navigation.navigate('Club', { id: player.owner_club_id! })} />}{player.current_club_id && <Button title="Clube atual" onPress={() => navigation.navigate('Club', { id: player.current_club_id! })} />}{listing && <Text>Anúncio: {listing.type} · {money(listing.price)} · {listing.duration_days} dias</Text>}{(player.owner_club_id === club || listing) && <Field label="Valor da negociação (R$)" value={amount} onChange={setAmount} numeric />}
    {(player.status === 'free_agent' || (player.owner_club_id === club && contract?.contract)) && <>
      <Text>{player.status === 'free_agent' ? 'Jogador livre' : `Contrato ${contract?.contract?.status === 'expiring' ? 'próximo do fim' : 'ativo'} · até ${new Date(contract?.contract?.expires_at ?? '').toLocaleDateString('pt-BR')}`}</Text>
      <Field label="Salário mensal (R$)" value={salary} onChange={setSalary} numeric /><Field label="Duração (temporadas, 1–5)" value={seasons} onChange={setSeasons} numeric />
      <Button title={player.status === 'free_agent' ? 'Contratar jogador livre' : 'Renovar contrato'} disabled={action.busy} onPress={() => void action.run(async () => { if (!/^[1-5]$/.test(seasons)) throw new Error('Informe uma duração de 1 a 5 temporadas.'); const data = { salary: cents(salary), seasons: Number(seasons) }; if (player.status === 'free_agent') await contractService.sign(player.id, data); else await contractService.renew(player.id, data); await load(); })} />
      {contract?.history.map(event => <Text key={event.id}>{new Date(event.created_at).toLocaleDateString('pt-BR')} · {({ created: 'Criado', renewed: 'Renovado', terminated: 'Encerrado', signed: 'Contratado', transferred: 'Transferido', expired: 'Expirado', expiring: 'Próximo do fim', salary_paid: 'Salário pago' } as Record<string, string>)[event.action] ?? event.action} · {money(event.salary)}</Text>)}
    </>}
    {player.owner_club_id === club && player.current_club_id === club && !listing && <><Choices values={['sale', 'loan']} value={type} onChange={setType} />{type === 'loan' && <Field label="Duração (dias)" value={days} onChange={setDays} numeric />}<Button title="Anunciar jogador" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.list({ player_id: player.id, type: type as 'sale' | 'loan', price: cents(amount), duration_days: Number(days) }); await load(); })} /></>}
    {listing && listing.seller_club_id !== club && <Button title="Enviar proposta" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.offer(listing.id, cents(amount)); navigation.navigate('TransferOffers'); })} />}{listing && listing.seller_club_id === club && <Button title="Retirar anúncio" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.cancelListing(listing.id); await load(); })} />}</>}</GamePage>;
}
