import { useI18n } from './useI18n';

export function useDirection() {
  const { isRTL } = useI18n();
  return {
    dir: isRTL ? 'rtl' as const : 'ltr' as const,
    isRTL,
    textAlign: isRTL ? 'right' as const : 'left' as const,
    marginStart: isRTL ? 'marginRight' as const : 'marginLeft' as const,
    marginEnd: isRTL ? 'marginLeft' as const : 'marginRight' as const,
    paddingStart: isRTL ? 'paddingRight' as const : 'paddingLeft' as const,
    paddingEnd: isRTL ? 'paddingLeft' as const : 'paddingRight' as const,
    start: isRTL ? 'right' as const : 'left' as const,
    end: isRTL ? 'left' as const : 'right' as const,
  };
}
