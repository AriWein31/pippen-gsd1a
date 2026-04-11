import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../utils/helpers';
import {
  NowIcon,
  NowIconFilled,
  TrendsIcon,
  TrendsIconFilled,
  WatchIcon,
  WatchIconFilled,
  ActionsIcon,
  ActionsIconFilled,
  ProfileIcon,
  ProfileIconFilled,
} from './Icons';

interface TabItem {
  id: string;
  label: string;
  path: string;
  icon: React.FC<{ size?: number; color?: string }>;
  activeIcon: React.FC<{ size?: number; color?: string }>;
}

const tabs: TabItem[] = [
  {
    id: 'now',
    label: 'Now',
    path: '/',
    icon: NowIcon,
    activeIcon: NowIconFilled,
  },
  {
    id: 'trends',
    label: 'Trends',
    path: '/trends',
    icon: TrendsIcon,
    activeIcon: TrendsIconFilled,
  },
  {
    id: 'watch',
    label: 'Watch',
    path: '/watch',
    icon: WatchIcon,
    activeIcon: WatchIconFilled,
  },
  {
    id: 'actions',
    label: 'Actions',
    path: '/actions',
    icon: ActionsIcon,
    activeIcon: ActionsIconFilled,
  },
  {
    id: 'profile',
    label: 'Profile',
    path: '/profile',
    icon: ProfileIcon,
    activeIcon: ProfileIconFilled,
  },
];

export const BottomNav: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string): boolean => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-[#E5E7EB] z-50 safe-area-bottom">
      <div className="flex items-center justify-around h-[64px] max-w-lg mx-auto">
        {tabs.map((tab) => {
          const active = isActive(tab.path);
          const Icon = active ? tab.activeIcon : tab.icon;

          return (
            <NavLink
              key={tab.id}
              to={tab.path}
              className={cn(
                'flex flex-col items-center justify-center flex-1 h-full transition-colors duration-200',
                'min-w-[44px] min-h-[44px]',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#315BFF] focus-visible:ring-offset-2',
                active ? 'text-[#315BFF]' : 'text-[#8A8E97]'
              )}
            >
              <Icon size={24} color={active ? '#315BFF' : '#8A8E97'} />
              <span
                className={cn(
                  'text-xs mt-1 font-medium transition-all duration-200',
                  active ? 'opacity-100' : 'opacity-0 h-0 mt-0 overflow-hidden'
                )}
              >
                {tab.label}
              </span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
};
