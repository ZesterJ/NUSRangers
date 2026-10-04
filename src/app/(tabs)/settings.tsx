import { useTranslation } from "react-i18next";
import { StyleSheet, Switch, Text, TextInput, View } from "react-native";

import { Chip, KeyboardScrollView, SectionTitle } from "@/components/ui";
import { PACKS, getPack } from "@/packs";
import { useConnectivityStore } from "@/store/connectivity";
import { useSettings, type AiMode } from "@/store/settings";
import { radius, spacing, usePackContext } from "@/theme";

const AI_MODES: AiMode[] = ["auto", "offline", "cloud"];

function Row({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  const { theme } = usePackContext();
  return (
    <View style={styles.row}>
      <Text style={{ color: theme.text, fontSize: 16, flex: 1 }}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ true: theme.primary }}
      />
    </View>
  );
}

export default function Settings() {
  const { pack, locale, theme } = usePackContext();
  const { t } = useTranslation();
  const s = useSettings();
  const deviceOnline = useConnectivityStore((c) => c.deviceOnline);

  return (
    <KeyboardScrollView
      style={{ backgroundColor: theme.background }}
      contentContainerStyle={styles.content}
    >
      <SectionTitle>{t("settings.language")}</SectionTitle>
      <View style={styles.chips}>
        {pack.locales.map((l) => (
          <Chip
            key={l.code}
            label={l.label}
            selected={locale === l.code}
            onPress={() => s.set({ locale: l.code })}
          />
        ))}
      </View>

      {/* Connection and backend settings are for the team and clinic staff, never for patients. */}
      {s.role === "clinic" && (
        <>
          <SectionTitle>{t("settings.aiMode")}</SectionTitle>
          <View style={styles.chips}>
            {AI_MODES.map((m) => (
              <Chip
                key={m}
                label={t(`settings.aiModes.${m}`)}
                selected={s.aiMode === m}
                onPress={() => s.set({ aiMode: m })}
              />
            ))}
          </View>
          <Row
            label={t("settings.forceOffline")}
            value={s.forceOffline}
            onChange={(v) => s.set({ forceOffline: v })}
          />
          <Text style={{ color: theme.textMuted, fontSize: 12 }}>
            Device network: {deviceOnline ? "connected" : "none"}
          </Text>

          <SectionTitle>{t("settings.developer")}</SectionTitle>
          {Object.keys(PACKS).length > 1 && (
            <>
              <Text style={{ color: theme.text, fontWeight: "600" }}>
                {t("settings.pack")}
              </Text>
              <View style={styles.chips}>
                {Object.values(PACKS).map((p) => (
                  <Chip
                    key={p.id}
                    label={`${p.emoji} ${p.appName}`}
                    selected={pack.id === p.id}
                    onPress={() => {
                      const next = getPack(p.id);
                      const keepLocale = next.locales.some(
                        (l) => l.code === locale,
                      );
                      s.set({
                        packId: p.id,
                        locale: keepLocale ? locale : next.defaultLocale,
                      });
                    }}
                  />
                ))}
              </View>
            </>
          )}
          <Row
            label={t("settings.useMock")}
            value={s.useMock}
            onChange={(v) => s.set({ useMock: v })}
          />
          <Text style={{ color: theme.text, fontWeight: "600" }}>
            {t("settings.apiUrl")}
          </Text>
          <TextInput
            style={[
              styles.input,
              {
                color: theme.text,
                borderColor: theme.border,
                backgroundColor: theme.card,
              },
            ]}
            value={s.apiUrl}
            onChangeText={(v) => s.set({ apiUrl: v })}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
          />
        </>
      )}
    </KeyboardScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    gap: spacing.sm,
    paddingBottom: spacing.xl * 2,
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: spacing.sm,
  },
  input: {
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    minHeight: 44,
    fontSize: 15,
  },
});
