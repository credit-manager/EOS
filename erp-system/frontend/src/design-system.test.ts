import { describe, expect, it } from 'vitest';
import {
  EOS_DESIGN_SYSTEM_VERSION,
  eosBreakpoints,
  eosLogical,
  eosSemanticStatus,
} from './design-system';

describe('EOS design system contract', () => {
  it('exposes a stable version and responsive breakpoints', () => {
    expect(EOS_DESIGN_SYSTEM_VERSION).toBe('1.0.0');
    expect(eosBreakpoints.mobile).toBe(640);
    expect(eosBreakpoints.desktop).toBe(1024);
    expect(eosBreakpoints.max).toBe(1440);
  });

  it('provides all semantic statuses', () => {
    expect(Object.keys(eosSemanticStatus).sort()).toEqual([
      'error',
      'info',
      'neutral',
      'success',
      'warning',
    ]);
  });

  it('uses logical CSS properties for bidirectional layouts', () => {
    expect(eosLogical.inlineStart).toBe('margin-inline-start');
    expect(eosLogical.inlineEnd).toBe('margin-inline-end');
    expect(eosLogical.paddingInline).toBe('padding-inline');
  });
});
