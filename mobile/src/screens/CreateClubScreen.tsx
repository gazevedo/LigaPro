import { useEffect, useState } from 'react';
import { ActivityIndicator, Image, Modal, Pressable, Text, View } from 'react-native';
import { Catalog, Club } from '../types/game';
import { clubService } from '../services/clubService';
import { ApiError, ApiTimeoutError } from '../services/apiClient';
import { useClubStore } from '../stores/clubStore';
import { useNotificationStore } from '../stores/notificationStore';
import { useAuthStore } from '../stores/authStore';
import { ActionButton, Card, Field, GamePage, palette, useAction } from '../components/GameUI';
import { ClubBadge } from '../components/ClubBadge';
import { CountryPicker } from '../components/CountryPicker';
const creationMessages = [
  'Conferindo os dados do clube…',
  'Buscando um clube disponível na liga…',
  'Aplicando o nome e o escudo escolhidos…',
  'Preparando sua entrada no jogo…',
];

function CreationProgress({ onClose }: { onClose: () => void }) {
  const [messageIndex, setMessageIndex] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setMessageIndex(index => Math.min(index + 1, creationMessages.length - 1)), 1800);
    return () => clearInterval(timer);
  }, []);
  return <Modal transparent visible animationType="fade" onRequestClose={onClose}>
    <View style={{ flex: 1, backgroundColor: '#14243a88', justifyContent: 'center', alignItems: 'center', padding: 24 }}>
      <View accessibilityViewIsModal style={{ width: '100%', maxWidth: 420, backgroundColor: '#fff', borderRadius: 22, padding: 24, gap: 18 }}>
        <Text accessibilityRole="header" style={{ fontSize: 22, fontWeight: '700', color: palette.ink }}>Preparando seu clube</Text>
        <ActivityIndicator accessibilityLabel="Criação do clube em andamento" size="large" color={palette.primary} />
        <Text accessibilityLiveRegion="polite" style={{ color: palette.ink, textAlign: 'center' }}>{creationMessages[messageIndex]}</Text>
        <Text style={{ color: palette.muted }}>Seu clube já conta com elenco e estrutura. Estamos organizando sua chegada.</Text>
        <ActionButton secondary title="Fechar e continuar editando" onPress={onClose} />
      </View>
    </View>
  </Modal>;
}

export function CreateClubScreen() {
  const [name, setName] = useState(''), [country, setCountry] = useState(''), [badge, setBadge] = useState('');
  const [stadiumName, setStadiumName] = useState('');
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const action = useAction();
  const [creating, setCreating] = useState(false), [progressVisible, setProgressVisible] = useState(false);
  async function loadCatalog() {
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const data = await clubService.catalog();
        if (!data.countries.length || !data.badges.length) throw new Error('Não foi possível carregar todas as opções do clube. Tente novamente.');
        setCatalog(data);
        setCountry(value => data.countries.some(item => item.id === value) ? value : '');
        setBadge(value => data.badges.some(item => item.id === value) ? value : '');
        return;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) throw error;
        if (attempt === 2) throw new Error('Não foi possível carregar todas as opções do clube. Tente novamente.');
      }
    }
  }
  useEffect(() => { void action.run(loadCatalog); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  function enterClub(club: Club) { useNotificationStore.getState().show(`${club.name} está pronto. Bem-vindo ao jogo!`); useClubStore.setState({ data: { club }, error: null, loading: false }); }
  const selectionsValid = !!catalog?.countries.some(item => item.id === country) && !!catalog?.badges.some(item => item.id === badge);
  const formValid = selectionsValid && name.trim().length >= 3 && name.trim().length <= 60 && (!stadiumName.trim() || (stadiumName.trim().length >= 3 && stadiumName.trim().length <= 60));
  async function create() {
    if (!selectionsValid) throw new Error('Selecione o país e o escudo do clube para continuar.');
    setCreating(true); setProgressVisible(true);
    try { await submitClub(); }
    finally { setCreating(false); setProgressVisible(false); }
  }
  async function submitClub() {
    if (name.trim().length < 3 || name.trim().length > 60) throw new Error('O nome do clube deve ter entre 3 e 60 caracteres.');
    if (stadiumName.trim() && (stadiumName.trim().length < 3 || stadiumName.trim().length > 60)) throw new Error('O nome do estádio deve ter entre 3 e 60 caracteres.');
    const session = useAuthStore.getState();
    try {
      const club = await clubService.create({ name: name.trim(), country_id: country, badge_id: badge, ...(stadiumName.trim() ? { stadium_name: stadiumName.trim() } : {}) });
      const current = useAuthStore.getState();
      if (current.authenticated === session.authenticated && current.user?.id === session.user?.id) enterClub(club);
    } catch (error) {
      const sameSession = () => {
        const current = useAuthStore.getState();
        return current.authenticated === session.authenticated && current.user?.id === session.user?.id;
      };
      if (!sameSession()) return;
      if (error instanceof ApiTimeoutError || (error instanceof ApiError && error.status === 409)) {
        // The POST may have committed even though its response never arrived.
        // Check the result without issuing another creation request.
        try {
          const { club } = await clubService.status();
          if (!sameSession()) return;
          if (club) { enterClub(club); return; }
        } catch (statusError) {
          if (!sameSession()) return;
          if (statusError instanceof ApiError && statusError.status === 401) {
            await useAuthStore.getState().clearSession();
            useNotificationStore.getState().show('Sua sessão expirou. Entre novamente para continuar.');
            return;
          }
        }
        if (error instanceof ApiTimeoutError) throw new Error('Não foi possível confirmar a criação do clube a tempo. Seus dados foram mantidos. Tente novamente em instantes.');
      }
      if (error instanceof ApiError && error.status === 401) {
        await useAuthStore.getState().clearSession();
        useNotificationStore.getState().show('Sua sessão expirou. Entre novamente para continuar.');
        return;
      }
      throw error;
    }
  }
  return <GamePage loading={action.busy && !creating} error={action.error}>
    {creating && progressVisible && <CreationProgress onClose={() => setProgressVisible(false)} />}
    <Image accessibilityLabel="Logotipo LigaPro" source={require('../../assets/brand/logo-ligapro.png')} resizeMode="contain" style={{ width: '100%', maxWidth: 310, height: 104, alignSelf: 'center' }} />
    <Card><Text style={{ fontWeight: '700', fontSize: 20, color: palette.ink }}>1. Nome e país</Text><Field label="Nome do clube" value={name} onChange={setName} placeholder="Como sua equipe será conhecida?" maxLength={60} /><Field label="Nome do estádio" value={stadiumName} onChange={setStadiumName} maxLength={60} placeholder="Como seu estádio será conhecido?" /><CountryPicker countries={catalog?.countries || []} value={country} onChange={setCountry} disabled={!catalog} /></Card>
    <Card><Text style={{ fontWeight: '700', fontSize: 20, color: palette.ink }}>2. Seu escudo</Text><View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>{catalog?.badges.map(item => <Pressable key={item.id} accessibilityRole="button" accessibilityLabel={`${badge === item.id ? '✓ ' : ''}${item.name}`} accessibilityState={{ selected: badge === item.id }} onPress={() => setBadge(item.id)} style={{ alignItems: 'center', gap: 8, width: 136, padding: 14, borderRadius: 18, borderWidth: 2, borderColor: badge === item.id ? palette.primary : palette.border, backgroundColor: badge === item.id ? '#e8f7f1' : '#fff' }}><ClubBadge badge={item} name={name} size={58} /><Text style={{ color: palette.ink, fontWeight: '600' }}>{badge === item.id ? '✓ ' : ''}{item.name}</Text></Pressable>)}</View></Card>
    <Card><View style={{ flexDirection: 'row', gap: 20, alignItems: 'center' }}><ClubBadge badge={catalog?.badges.find(item => item.id === badge)} name={name} /><View style={{ flex: 1, gap: 6 }}><Text style={{ color: palette.muted }}>PRÉVIA DO CLUBE</Text><Text style={{ fontSize: 24, fontWeight: '800', color: palette.ink }}>{name.trim() || 'Seu clube'}</Text><Text style={{ color: palette.muted }}>{catalog?.countries.find(item => item.id === country)?.name || 'Escolha um país'}</Text></View></View>
    {!catalog && <ActionButton secondary title="Recarregar opções" disabled={action.busy} onPress={() => void action.run(loadCatalog)} />}
    <ActionButton title="Criar clube" disabled={action.busy || !formValid} onPress={() => void action.run(create)} />{creating && !progressVisible && <ActionButton secondary title="Ver andamento" onPress={() => setProgressVisible(true)} />}</Card>
    <ActionButton secondary title="Sair" onPress={() => void useAuthStore.getState().logout()} />
  </GamePage>;
}
