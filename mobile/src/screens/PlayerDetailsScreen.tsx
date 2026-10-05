import { useEffect, useState } from 'react';
import { Button, Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Player } from '../types/game';
import { marketService } from '../services/marketService';
import { useClubStore } from '../stores/clubStore';
import { Choices, Field, GamePage, cents, money, useAction } from '../components/GameUI';
export function PlayerDetailsScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'PlayerDetails'>) {
  const [player, setPlayer] = useState<Player | null>(null), [listing, setListing] = useState<Player['listing']>(null), [amount, setAmount] = useState(''), [days, setDays] = useState('30'), [type, setType] = useState('sale');
  const club = useClubStore(state => state.data?.club?.id), action = useAction();
  async function load() { const p = await marketService.player(route.params.id); setPlayer(p); setListing(p.listing); }
  useEffect(() => { void action.run(load); }, [route.params.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}>{player && <><Text style={{ fontSize: 24 }}>{player.name}</Text><Text>{player.position} · {player.age} anos · overall {player.overall} · {money(player.value)} · {player.country_id}</Text><Button title="Clube proprietário" onPress={() => navigation.navigate('Club', { id: player.owner_club_id })} /><Button title="Clube atual" onPress={() => navigation.navigate('Club', { id: player.current_club_id })} />{listing && <Text>Anúncio: {listing.type} · {money(listing.price)} · {listing.duration_days} dias</Text>}{(player.owner_club_id === club || listing) && <Field label="Valor da negociação (R$)" value={amount} onChange={setAmount} numeric />}
    {player.owner_club_id === club && player.current_club_id === club && !listing && <><Choices values={['sale', 'loan']} value={type} onChange={setType} />{type === 'loan' && <Field label="Duração (dias)" value={days} onChange={setDays} numeric />}<Button title="Anunciar jogador" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.list({ player_id: player.id, type: type as 'sale' | 'loan', price: cents(amount), duration_days: Number(days) }); await load(); })} /></>}
    {listing && listing.seller_club_id !== club && <Button title="Enviar proposta" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.offer(listing.id, cents(amount)); navigation.navigate('TransferOffers'); })} />}{listing && listing.seller_club_id === club && <Button title="Retirar anúncio" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.cancelListing(listing.id); await load(); })} />}</>}</GamePage>;
}
