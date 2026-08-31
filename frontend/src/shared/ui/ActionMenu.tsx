import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/react';
import { MoreHorizontal } from 'lucide-react';
import type { ReactNode } from 'react';

interface ActionItem {
  label: string;
  icon?: ReactNode;
  danger?: boolean;
  onClick: () => void;
}

interface ActionMenuProps {
  items: ActionItem[];
}

export function ActionMenu({ items }: ActionMenuProps) {
  return (
    <Menu>
      <MenuButton className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 data-[open]:bg-gray-100">
        <MoreHorizontal className="h-4 w-4" />
      </MenuButton>
      <MenuItems
        anchor="bottom end"
        className="z-50 mt-1 w-44 rounded-xl border border-gray-200 bg-white shadow-lg py-1 text-sm origin-top-right transition duration-100 ease-out data-[closed]:scale-95 data-[closed]:opacity-0"
      >
        {items.map((item, i) => (
          <MenuItem key={i}>
            <button
              onClick={item.onClick}
              className={`flex items-center gap-2 w-full px-4 py-2 text-left ${item.danger ? 'text-red-600 hover:bg-red-50' : 'text-gray-700 hover:bg-gray-50'}`}
            >
              {item.icon}
              {item.label}
            </button>
          </MenuItem>
        ))}
      </MenuItems>
    </Menu>
  );
}
