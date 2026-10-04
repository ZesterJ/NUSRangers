import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Pressable, StyleSheet, Text, useColorScheme, View } from 'react-native';
import Svg, { Circle, G, Line, Path, Rect, Text as SvgText } from 'react-native-svg';

import type { Coordinates } from '@/intake/careRouting';
import directory from '@/intake/kilifiDirectory.json';
import map from '@/intake/kenyaMap.json';
import { radius, spacing, usePackContext } from '@/theme';

/**
 * Offline map for the Clinics tab: county outlines drawn from data shipped in the app (no map tiles,
 * no connection), with every facility as a dot. A small inset shows where the county sits in Kenya.
 */
type Facility = (typeof directory.facilities)[number];
type Box = { west: number; south: number; east: number; north: number };
type Shape = { name: string; rings: number[][][] };

const UNITS = 1000; // viewBox units per degree
const VIEW = map.view;
const W = (VIEW.east - VIEW.west) * UNITS;
const H = (VIEW.north - VIEW.south) * UNITS;
const KM_PER_DEGREE = 111.32;

const px = (lon: number, box: Box = VIEW) => (lon - box.west) * UNITS;
const py = (lat: number, box: Box = VIEW) => (box.north - lat) * UNITS;
const pathOf = (shape: Shape, box: Box = VIEW) =>
  shape.rings
    .map((ring) => ring.map(([lon, lat], i) => `${i ? 'L' : 'M'}${px(lon, box).toFixed(0)} ${py(lat, box).toFixed(0)}`).join('') + 'Z')
    .join('');

// Paths never change, so build them once.
const DETAIL = (map.detail as Shape[]).map((c) => ({ name: c.name, d: pathOf(c) }));
const COUNTRY_VIEW = map.countryView;
const CW = (COUNTRY_VIEW.east - COUNTRY_VIEW.west) * UNITS;
const CH = (COUNTRY_VIEW.north - COUNTRY_VIEW.south) * UNITS;
const COUNTRY = (map.country as Shape[]).map((c) => ({ name: c.name, d: pathOf(c, COUNTRY_VIEW) }));
const INSET_WIDTH = 78;

const PALETTE = {
  light: { sea: '#D6EAF8', land: '#F3EFE6', border: '#D9D2C2', county: '#DFF2E3', countyEdge: '#3E9B57', label: '#5B6770', seaLabel: '#7FA6C4', other: '#8795A1', confirmed: '#1E7B3A', you: '#1E88E5', picked: '#F57C00', ring: '#11181C' },
  dark: { sea: '#12222F', land: '#26292D', border: '#3A3F45', county: '#1F3A28', countyEdge: '#5FBF7A', label: '#A8B0B7', seaLabel: '#4F6F88', other: '#7C8791', confirmed: '#6FD08A', you: '#64B5F6', picked: '#FFA726', ring: '#ECEDEE' },
};

type Props = {
  selected: string | null;
  onSelect: (id: string) => void;
  /** Where distances are measured from, and whether that is the phone's own location. */
  from: Coordinates;
  fromIsUser: boolean;
};

export function ClinicMap({ selected, onSelect, from, fromIsUser }: Props) {
  const { theme, scale } = usePackContext();
  const { t } = useTranslation();
  const c = PALETTE[useColorScheme() === 'dark' ? 'dark' : 'light'];
  const [width, setWidth] = useState(0);

  const height = width * (H / W);
  const u = width ? W / width : 1; // viewBox units per screen point
  const picked = selected ? directory.facilities.find((f) => f.id === selected) : undefined;

  // A tap selects the facility nearest to the finger.
  const tap = (x: number, y: number) => {
    let best: Facility | null = null;
    let bestD = Infinity;
    for (const f of directory.facilities) {
      const d = (px(f.longitude) / u - x) ** 2 + (py(f.latitude) / u - y) ** 2;
      if (d < bestD) {
        bestD = d;
        best = f;
      }
    }
    if (best) onSelect(best.id);
  };

  const scaleKm = 20;
  const scaleUnits = (scaleKm / KM_PER_DEGREE) * UNITS;

  return (
    <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
      <View style={styles.head}>
        <Text style={[styles.title, { color: theme.text, fontSize: 16 * scale }]}>
          {t('clinics.mapTitle', { county: map.county })}
        </Text>
        <View style={[styles.badge, { backgroundColor: c.county }]}>
          <Text style={{ color: c.countyEdge, fontSize: 12 * scale, fontWeight: '700' }}>{t('clinics.offlineMap')}</Text>
        </View>
      </View>

      <Pressable
        accessibilityLabel={t('clinics.mapHint')}
        onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
        onPress={(e) => tap(e.nativeEvent.locationX, e.nativeEvent.locationY)}
        style={[styles.map, { height: height || 240, backgroundColor: c.sea }]}>
        {width > 0 && (
          <Svg width={width} height={height} viewBox={`0 0 ${W} ${H}`} pointerEvents="none">
            <Rect x={0} y={0} width={W} height={H} fill={c.sea} />
            {DETAIL.filter((s) => s.name !== map.county).map((s) => (
              <Path key={s.name} d={s.d} fill={c.land} stroke={c.border} strokeWidth={1 * u} />
            ))}
            {DETAIL.filter((s) => s.name === map.county).map((s) => (
              <Path key={s.name} d={s.d} fill={c.county} stroke={c.countyEdge} strokeWidth={2 * u} strokeLinejoin="round" />
            ))}
            <SvgText x={px(40.12)} y={py(-3.72)} fill={c.seaLabel} fontSize={12 * u} fontStyle="italic" textAnchor="middle">
              {t('clinics.ocean')}
            </SvgText>

            {directory.facilities
              .filter((f) => !f.services.length)
              .map((f) => (
                <Circle key={f.id} cx={px(f.longitude)} cy={py(f.latitude)} r={3 * u} fill={c.other} opacity={0.85} />
              ))}
            {directory.facilities
              .filter((f) => f.services.length)
              .map((f) => (
                <Circle key={f.id} cx={px(f.longitude)} cy={py(f.latitude)} r={5 * u} fill={c.confirmed} stroke="#FFFFFF" strokeWidth={1.5 * u} />
              ))}

            {/* Town names, drawn twice: a pale outline first so they stay readable over dots and borders. */}
            {map.towns.map((town) => (
              <G key={town.name}>
                <SvgText x={px(town.longitude) + 7 * u} y={py(town.latitude) - 6 * u} fontSize={11 * u} fontWeight="700" fill="none" stroke={c.county} strokeWidth={3 * u}>
                  {town.name}
                </SvgText>
                <SvgText x={px(town.longitude) + 7 * u} y={py(town.latitude) - 6 * u} fontSize={11 * u} fontWeight="700" fill={c.label}>
                  {town.name}
                </SvgText>
              </G>
            ))}

            {/* Where distances are measured from */}
            <Circle cx={px(from.longitude)} cy={py(from.latitude)} r={13 * u} fill={c.you} opacity={0.22} />
            <Circle cx={px(from.longitude)} cy={py(from.latitude)} r={6 * u} fill={c.you} stroke="#FFFFFF" strokeWidth={2 * u} />

            {picked && (
              <G>
                <Circle cx={px(picked.longitude)} cy={py(picked.latitude)} r={11 * u} fill="none" stroke={c.ring} strokeWidth={2.5 * u} />
                <Circle cx={px(picked.longitude)} cy={py(picked.latitude)} r={6 * u} fill={c.picked} stroke="#FFFFFF" strokeWidth={2 * u} />
              </G>
            )}

            {/* Scale bar */}
            <Line x1={12 * u} y1={H - 14 * u} x2={12 * u + scaleUnits} y2={H - 14 * u} stroke={c.label} strokeWidth={2 * u} />
            <SvgText x={12 * u} y={H - 20 * u} fill={c.label} fontSize={10 * u}>
              {scaleKm} km
            </SvgText>
          </Svg>
        )}

        {/* Locator: where the county is in Kenya */}
        {width > 0 && (
          <View pointerEvents="none" style={[styles.inset, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Svg width={INSET_WIDTH} height={INSET_WIDTH * (CH / CW)} viewBox={`0 0 ${CW} ${CH}`}>
              {COUNTRY.map((s) => (
                <Path key={s.name} d={s.d} fill={s.name === map.county ? c.countyEdge : c.land} stroke={c.border} strokeWidth={CW / INSET_WIDTH / 2} />
              ))}
            </Svg>
            <Text style={{ color: theme.textMuted, fontSize: 10, textAlign: 'center' }}>{t('clinics.kenya')}</Text>
          </View>
        )}
      </Pressable>

      <View style={styles.legend}>
        <Legend color={c.confirmed} label={t('clinics.legendConfirmed')} />
        <Legend color={c.other} label={t('clinics.legendOther')} />
        <Legend color={c.you} label={t(fromIsUser ? 'clinics.legendYou' : 'clinics.legendAnchor')} />
      </View>
      <Text style={{ color: theme.textMuted, fontSize: 13 * scale }}>{t('clinics.mapHint')}</Text>
    </View>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  const { theme, scale } = usePackContext();
  return (
    <View style={styles.legendItem}>
      <View style={[styles.swatch, { backgroundColor: color }]} />
      <Text style={{ color: theme.textMuted, fontSize: 12 * scale }}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.md,
    gap: spacing.sm,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: spacing.sm },
  title: { fontWeight: '800', flexShrink: 1 },
  badge: { borderRadius: 999, paddingHorizontal: spacing.md, paddingVertical: spacing.xs },
  map: { borderRadius: radius.md, overflow: 'hidden' },
  inset: { position: 'absolute', top: spacing.sm, left: spacing.sm, borderWidth: 1, borderRadius: radius.sm, padding: spacing.xs },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  swatch: { width: 10, height: 10, borderRadius: 5 },
});
