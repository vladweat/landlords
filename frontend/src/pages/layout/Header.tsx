import { Menu } from 'lucide-react';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="flex h-16 items-center border-b border-gray-200 bg-white px-4 sm:px-6">
      <button onClick={onMenuClick} className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden">
        <Menu className="h-5 w-5" />
      </button>
    </header>
  );
}
