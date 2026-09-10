/**
 * EOS Design System contract.
 *
 * This is intentionally framework-agnostic: generated ERP screens should
 * consume these semantic values instead of depending on a vendor component
 * library. The renderer can map these tokens to React/Tailwind/components.
 */

export type EosDensity = 'compact' | 'comfortable' | 'spacious';
export type EosDirection = 'ltr' | 'rtl';
export type EosStatus = 'neutral' | 'info' | 'success' | 'warning' | 'error';

export type EosFieldType =
  | 'text'
  | 'long-text'
  | 'number'
  | 'currency'
  | 'percentage'
  | 'date'
  | 'datetime'
  | 'boolean'
  | 'select'
  | 'reference'
  | 'multi-reference'
  | 'file'
  | 'image';

export interface EosFieldUI {
  component?: EosFieldType;
  required?: boolean;
  readonly?: boolean;
  visible?: boolean;
  order?: number;
  section?: string;
  width?: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12;
  helpText?: string;
  placeholder?: string;
}

export interface EosFieldSchema {
  key: string;
  label: string;
  type: EosFieldType;
  ui?: EosFieldUI;
  format?: {
    currency?: string;
    precision?: number;
  };
}

export interface EosEntitySchema {
  key: string;
  label: string;
  pluralLabel?: string;
  fields: EosFieldSchema[];
  permissions?: {
    create?: boolean;
    read?: boolean;
    update?: boolean;
    delete?: boolean;
  };
}

export interface EosDataGridColumn {
  key: string;
  label: string;
  width?: number;
  minWidth?: number;
  sortable?: boolean;
  filterable?: boolean;
  frozen?: 'start' | 'end';
  visible?: boolean;
}

export interface EosDataGridState {
  density: EosDensity;
  sort?: { key: string; direction: 'asc' | 'desc' };
  filters: Record<string, unknown>;
  visibleColumns: string[];
  frozenColumns: string[];
}

export const EOS_DESIGN_SYSTEM_VERSION = '1.0.0';

export const eosBreakpoints = {
  mobile: 640,
  tablet: 768,
  desktop: 1024,
  wide: 1280,
  max: 1440,
} as const;

export const eosSemanticStatus: Record<EosStatus, string> = {
  neutral: 'neutral',
  info: 'info',
  success: 'success',
  warning: 'warning',
  error: 'error',
};

/** Logical CSS helpers: components must not encode left/right behavior. */
export const eosLogical = {
  inlineStart: 'margin-inline-start',
  inlineEnd: 'margin-inline-end',
  blockStart: 'margin-block-start',
  blockEnd: 'margin-block-end',
  paddingInline: 'padding-inline',
  paddingBlock: 'padding-block',
} as const;
