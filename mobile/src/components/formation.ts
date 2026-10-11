import { Player } from '../types/game';

const aliases: Record<string, string> = { GOL: 'GK', DEF: 'CB', MED: 'MID', ATA: 'ATT' };
export const positionRole = (position: string) => aliases[position] ?? position;
export const positionSector = (position: string) => positionRole(position) === 'GK' ? 'GOL' : ['CB', 'FB'].includes(positionRole(position)) ? 'DEF' : positionRole(position) === 'MID' ? 'MED' : 'ATA';

// Matches the role assignment used by the match engine, including side preference.
export function arrangePlayers(players: Player[], formation: string, preserveOrder = false) {
  const sectors = formation.split('-').map(Number);
  const defenders = Array.from({ length: sectors[0] }, (_, index) => ({ position: sectors[0] >= 4 && index < 2 ? 'FB' : 'CB', side: sectors[0] >= 4 && index < 2 ? index === 0 ? 'left' : 'right' : 'center' }));
  const middle = sectors.slice(1, -1).reduce((sum, count) => sum + count, 0);
  const slots = [{ position: 'GK', side: 'center' }, ...defenders, ...Array.from({ length: middle }, (_, index) => ({ position: 'MID', side: middle >= 4 && index < 2 ? index === 0 ? 'left' : 'right' : 'center' })), ...Array.from({ length: sectors[sectors.length - 1] }, () => ({ position: 'ATT', side: 'center' }))];
  const pool = [...players];
  return slots.flatMap(slot => {
    if (!pool.length) return [];
    const score = (player: Player) => {
      const role = positionRole(player.position);
      const natural = role === slot.position || (['CB', 'FB'].includes(role) && ['CB', 'FB'].includes(slot.position));
      return Number(natural) * 4 + Number([slot.side, 'both'].includes(player.preferred_side ?? 'both')) * 2 + Number(role === slot.position);
    };
    const best = preserveOrder ? pool[0] : pool.reduce((selected, player) => score(player) > score(selected) ? player : selected);
    pool.splice(pool.indexOf(best), 1);
    return [{ ...slot, player: best, outOfPosition: positionSector(best.position) !== positionSector(slot.position) }];
  });
}
