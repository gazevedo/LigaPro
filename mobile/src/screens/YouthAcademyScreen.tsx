import { useState } from 'react';
import { Pressable, Text, useWindowDimensions, View } from 'react-native';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { ActionButton as Button, Card, GamePage, palette, useAction } from '../components/GameUI';
import { PlayerRosterCells, PlayerRosterHeader } from '../components/PlayerRosterColumns';
import { developmentService } from '../services/developmentService';
import { useYouthStore } from '../stores/screenStores';
export function YouthAcademyScreen() {
  const { data, loading, error, load, ensure, refresh } = useYouthStore();
  const [selected, setSelected] = useState<string | null>(null);
  const compact = useWindowDimensions().width < 600;
  const action = useAction();
  useScreenRefresh(ensure, refresh);
  return <GamePage loading={loading} error={action.error || error}>
    <Text>A cada temporada, escolha um dos três candidatos para a base. A promoção ocorre a partir dos 18 anos.</Text>
    <Card><View style={{ width: '100%', minWidth: 0 }}>
      <PlayerRosterHeader compact={compact} trailing="Ações" />
      {data?.map(player => <View key={player.id}>
        <Pressable accessibilityRole="button" accessibilityLabel={`Detalhes de ${player.name}`} accessibilityState={{ expanded: selected === player.id }} onPress={() => setSelected(current => current === player.id ? null : player.id)} style={{ flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 14, borderTopWidth: 1, borderColor: palette.border }}>
          <Text style={{ width: 42, fontWeight: '700', color: palette.ink }}>{player.shirt_number ?? '—'}</Text>
          <PlayerRosterCells player={player} compact={compact} />
          <Text style={{ width: 56, textAlign: 'center', color: palette.primary }}>{selected === player.id ? '⌃' : '⌄'}</Text>
        </Pressable>
        {selected === player.id && <View style={{ gap: 12, padding: 12, backgroundColor: '#f4f7fc', borderRadius: 12 }}>
          <Text>Força: {player.strength ?? player.overall} · CPE: {player.estimated_potential_capacity ?? 'Em avaliação'} · Treino: {player.training_progress ?? 0}/100</Text>
          {player.can_train === false && player.status !== 'candidate' && <Text>Limite de desenvolvimento atingido.</Text>}
          {player.status === 'candidate' ? <Button title={`Escolher ${player.name}`} onPress={() => void action.run(async () => { await developmentService.selectYouth(player.id); await load(); })} /> : <>
            <Button title={`Treinar ${player.name}`} disabled={player.can_train === false} onPress={() => void action.run(async () => { await developmentService.train(player.id); await load(); })} />
            <Button title={`Promover ${player.name}`} disabled={player.age < 18} onPress={() => void action.run(async () => { await developmentService.promote(player.id); await load(); })} />
            <Button title={`Dispensar ${player.name}`} onPress={() => void action.run(async () => { await developmentService.release(player.id); await load(); })} />
          </>}
        </View>}
      </View>)}
      {data?.length === 0 && <Text>Nenhum jovem disponível.</Text>}
    </View></Card>
  </GamePage>;
}
