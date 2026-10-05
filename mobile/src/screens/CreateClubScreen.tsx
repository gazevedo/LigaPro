import { useEffect, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { Catalog } from '../types/game';
import { clubService } from '../services/clubService';
import { useClubStore } from '../stores/clubStore';
import { useAuthStore } from '../stores/authStore';
import { Field, GamePage, useAction } from '../components/GameUI';
export function CreateClubScreen() {
  const [name, setName] = useState(''), [country, setCountry] = useState('BR'), [badge, setBadge] = useState('blue');
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const action = useAction();
  useEffect(() => { void action.run(async () => setCatalog(await clubService.catalog())); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}>
    <Text style={{ fontSize: 24 }}>Crie seu clube</Text>
    <Field label="Nome do clube" value={name} onChange={setName} />
    <Text>País</Text>{catalog?.countries.map(item => <Button key={item.id} title={`${country === item.id ? '✓ ' : ''}${item.name}`} onPress={() => setCountry(item.id)} />)}
    <Text>Escudo</Text><View style={{ flexDirection: 'row', gap: 10 }}>{catalog?.badges.map(item => <View key={item.id} style={{ backgroundColor: item.color, padding: 6 }}><Button title={`${badge === item.id ? '✓ ' : ''}${item.symbol} ${item.name}`} onPress={() => setBadge(item.id)} /></View>)}</View>
    {!catalog && <Button title="Recarregar opções" onPress={() => void action.run(async () => setCatalog(await clubService.catalog()))} />}
    <Button title="Criar clube" disabled={action.busy || !catalog || name.trim().length < 3} onPress={() => void action.run(async () => { await clubService.create({ name, country_id: country, badge_id: badge }); await useClubStore.getState().load(); })} />
    <Button title="Sair" onPress={() => void useAuthStore.getState().logout()} />
  </GamePage>;
}
