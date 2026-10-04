import { useTranslation } from 'react-i18next';

import i18n from '@/i18n';

const sw = i18n.getFixedT('sw');

/**
 * Labels for the tap-to-answer options. The patient answers in Swahili, so the Swahili wording is
 * always shown; when the app is in another language that wording follows in brackets for the helper.
 */
export function useBilingual() {
  const { t, i18n: active } = useTranslation();
  return (key: string, options?: Record<string, unknown>) => {
    const local = t(key, options ?? {});
    if (active.language === 'sw') return local;
    const swahili = sw(key, options ?? {});
    return swahili === local ? local : `${swahili} (${local})`;
  };
}
