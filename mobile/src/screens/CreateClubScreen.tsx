import { useEffect, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { Catalog, Club } from '../types/game';
import { clubService } from '../services/clubService';
import { ApiError, ApiTimeoutError } from '../services/apiClient';
import { useClubStore } from '../stores/clubStore';
import { useNotificationStore } from '../stores/notificationStore';
import { useAuthStore } from '../stores/authStore';
import { ActionButton, Card, Field, GamePage, palette, useAction } from '../components/GameUI';
import { ClubBadge } from '../components/ClubBadge';
import { CountryPicker } from '../components/CountryPicker';
export function CreateClubScreen() {
  const [name, setName] = useState(''), [country, setCountry] = useState('BR'), [badge, setBadge] = useState('blue');
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const action = useAction();
  async function loadCatalog() {
    const data = await clubService.catalog(); setCatalog(data);
    setCountry(value => data.countries.some(item => item.id === value) ? value : data.countries[0]?.id || '');
    setBadge(value => data.badges.some(item => item.id === value) ? value : data.badges[0]?.id || '');
  }
  useEffect(() => { void action.run(loadCatalog); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  function enterClub(club: Club) { useNotificationStore.getState().show(`${club.name} está pronto. Bem-vindo ao jogo!`); useClubStore.setState({ data: { club }, error: null, loading: false }); }
  async function create() {
    if (name.trim().length < 3 || name.trim().length > 60) throw new Error('O nome do clube deve ter entre 3 e 60 caracteres.');
    const session = useAuthStore.getState();
    try {
      const club = await clubService.create({ name: name.trim(), country_id: country, badge_id: badge });
      const current = useAuthStore.getState();
      if (current.authenticated === session.authenticated && current.user?.id === session.user?.id) enterClub(club);
    } catch (error) {
      if (error instanceof ApiTimeoutError || (error instanceof ApiError && error.status === 401)) {
        const current = useAuthStore.getState();
        // A late response from an old session must not change a newer login.
        if (current.user?.id && current.user.id !== session.user?.id) return;
        await current.clearSession();
        useNotificationStore.getState().show(error instanceof ApiTimeoutError
          ? 'O tempo para criar o clube esgotou. Entre novamente para continuar.'
          : 'Sua sessão expirou. Entre novamente para continuar.');
        return;
      }
      throw error;
    }
  }
  return <GamePage loading={action.busy} error={action.error}>
    <Text style={{ color: palette.primary, fontWeight: '800', letterSpacing: 3 }}>LIGAPRO · PRIMEIRO PASSO</Text>
    <Text style={{ fontSize: 34, fontWeight: '800', color: palette.ink }}>Seu clube começa aqui.</Text>
    <Text style={{ color: palette.muted, fontSize: 16 }}>Escolha a identidade da sua equipe e prepare-se para entrar em campo.</Text>
    <Card><Text style={{ fontWeight: '700', fontSize: 20, color: palette.ink }}>1. Nome e país</Text><Field label="Nome do clube" value={name} onChange={setName} placeholder="Como sua equipe será conhecida?" maxLength={60} editable={!action.busy} /><CountryPicker countries={catalog?.countries || []} value={country} onChange={setCountry} disabled={!catalog || action.busy} /></Card>
    <Card><Text style={{ fontWeight: '700', fontSize: 20, color: palette.ink }}>2. Seu escudo</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>{catalog?.badges.map(item => <Pressable key={item.id} accessibilityRole="button" accessibilityLabel={`${badge === item.id ? '✓ ' : ''}${item.name}`} accessibilityState={{ selected: badge === item.id, disabled: action.busy }} disabled={action.busy} onPress={() => setBadge(item.id)} style={{ alignItems: 'center', gap: 8, width: 136, padding: 14, borderRadius: 18, borderWidth: 2, borderColor: badge === item.id ? palette.primary : palette.border, backgroundColor: badge === item.id ? '#e8f7f1' : '#fff' }}><ClubBadge badge={item} name={name} size={58} /><Text style={{ color: palette.ink, fontWeight: '600' }}>{badge === item.id ? '✓ ' : ''}{item.name}</Text></Pressable>)}</View></Card>
    <Card><View style={{ flexDirection: 'row', gap: 20, alignItems: 'center' }}><ClubBadge badge={catalog?.badges.find(item => item.id === badge)} name={name} /><View style={{ flex: 1, gap: 6 }}><Text style={{ color: palette.muted }}>PRÉVIA DO CLUBE</Text><Text style={{ fontSize: 24, fontWeight: '800', color: palette.ink }}>{name.trim() || 'Seu clube'}</Text><Text style={{ color: palette.muted }}>{catalog?.countries.find(item => item.id === country)?.name || 'Escolha um país'}</Text></View></View>
    {!catalog && <ActionButton secondary title="Recarregar opções" disabled={action.busy} onPress={() => void action.run(loadCatalog)} />}
    <ActionButton title="Criar clube" disabled={action.busy || !catalog || name.trim().length < 3} onPress={() => void action.run(create)} />{action.busy && catalog && <Text style={{ color: palette.muted }}>Preparando seu clube e seu elenco. Isso pode levar alguns instantes.</Text>}</Card>
    <ActionButton secondary title="Sair" disabled={action.busy} onPress={() => void useAuthStore.getState().logout()} />
  </GamePage>;
}
