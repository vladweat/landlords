import type { Property } from '@/entities/property';
import type { Tenant } from '@/entities/tenant';

interface ContractLike {
  property_id: string;
  tenant_id: string;
  rent_amount: string;
  currency: string;
}

export function getContractLabel(
  contract: ContractLike,
  properties: Property[],
  tenants: Tenant[]
): string {
  const p = properties.find((x) => x.id === contract.property_id);
  const t = tenants.find((x) => x.id === contract.tenant_id);
  return `${p?.address || '—'} / ${t?.full_name || '—'} — ${Number(contract.rent_amount).toLocaleString('ru-RU')} ${contract.currency}`;
}
