import { useParams } from 'react-router-dom';
import { ContractWorkspace } from '@/features/contracts/components/ContractWorkspace';

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  if (!id) return <p className="text-red-500">Договор не найден</p>;
  return <ContractWorkspace contractId={id} />;
}
