import type { PropertyType } from '@/entities/property';
import { PROPERTY_TYPE_LABELS as BASE_LABELS } from '@/entities/property';

export type { PropertyType };

export interface ContractTemplate {
  id: string;
  account_id: string;
  name: string;
  title: string;
  body: string;
  property_type: PropertyType | null;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ContractTemplatesListData {
  items: ContractTemplate[];
  placeholders: string[];
}

export interface ContractTemplateCreatePayload {
  name: string;
  title: string;
  body: string;
  property_type?: PropertyType | null;
  is_default?: boolean;
}

export interface ContractTemplateUpdatePayload {
  name?: string;
  title?: string;
  body?: string;
  property_type?: PropertyType | null;
  is_default?: boolean;
}

export const PROPERTY_TYPE_LABELS: Record<PropertyType | 'any', string> = {
  ...BASE_LABELS,
  any: 'Все типы',
};
