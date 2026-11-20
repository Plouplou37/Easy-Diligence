import React, { useState, useEffect, useRef } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  PlusIcon,
  QuestionMarkCircleIcon,
  TagIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  UsersIcon,
  BookOpenIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/entities/viewer';
import { DarkModeToggle } from '@/features/theme-toggle';
import { menu } from '@/shared/ui';

const AppLayout = () => {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, logout, isAdmin } = useAuth();
  const userMenuRef = useRef(null);

  const navigation = [
    {
      name: 'Main',
      items: [
        { name: 'Dashboard', href: '/', icon: HomeIcon },
        { name: 'New Session', href: '/session/create', icon: PlusIcon },
        { name: 'Vector Stores', href: '/vector-stores', icon: BookOpenIcon },
        // DD types & questions are now per-user owned, so every user manages their own
        { name: 'Questions', href: '/questions', icon: QuestionMarkCircleIcon },
        { name: 'DD Types', href: '/dd-types', icon: TagIcon },
      ],
    },
    ...(isAdmin
      ? [
          {
            name: 'Administration',
            items: [{ name: 'User Management', href: '/admin/users', icon: UsersIcon }],
          },
        ]
      : []),
  ];

  // Nested pages light up their section: a session and its answers belong to
  // the Dashboard, which had nothing highlighted on them.
  const isActive = href => {
    const path = location.pathname;
    if (path === href) return true;
    if (href === '/') return path.startsWith('/session/') && path !== '/session/create';
    return href !== '/session/create' && path.startsWith(`${href}/`);
  };

  const handleLogout = () => {
    logout();
  };

  const closeMenus = () => {
    setUserMenuOpen(false);
    setMobileMenuOpen(false);
  };

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = event => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false);
      }
    };

    if (userMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [userMenuOpen]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Floating navbar */}
      <nav className="fixed top-0 inset-x-0 z-40 mx-2 sm:mx-4 h-(--navbar-height) flex items-center gap-4 px-4 rounded-b-xl border-x border-b border-border nav-bg backdrop-blur-xs shadow-md">
        <Link
          to="/"
          onClick={closeMenus}
          className="shrink-0 text-fluid-sm font-normal uppercase tracking-[0.2em] whitespace-nowrap logo-gradient-hover"
        >
          DD Automation
        </Link>

        {/* Desktop links */}
        <div className="hidden xl:flex flex-1 min-w-0 items-center justify-center gap-1">
          {navigation.map((section, sectionIdx) => (
            <React.Fragment key={section.name}>
              {sectionIdx > 0 && <span className="mx-2 h-4 w-px bg-border" aria-hidden="true" />}
              {section.items.map(item => (
                <Link
                  key={item.name}
                  to={item.href}
                  data-active={isActive(item.href)}
                  className="analysis-link"
                >
                  {item.name}
                </Link>
              ))}
            </React.Fragment>
          ))}
        </div>

        <div className="flex-1 xl:hidden" />

        {/* Theme + profile */}
        <div className="flex items-center gap-1 shrink-0">
          <DarkModeToggle />

          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="p-1.5 rounded-md text-content hover:text-bleu-atlantis transition-colors"
            >
              <UserCircleIcon className="h-6 w-6" />
            </button>

            {userMenuOpen && (
              <div className={`absolute right-0 top-full mt-2 min-w-52 z-50 ${menu.panel}`}>
                <div className={menu.header}>
                  <p className="eyebrow">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <p className="mt-0.5 text-xs text-content-muted truncate">{user?.email}</p>
                </div>
                <div className="py-1">
                  <Link to="/profile" className={menu.item} onClick={closeMenus}>
                    <UserCircleIcon className="h-3.5 w-3.5 shrink-0" />
                    Profile Settings
                  </Link>
                </div>
                <hr className="border-border" />
                <button
                  onClick={() => {
                    handleLogout();
                    closeMenus();
                  }}
                  className={menu.itemDanger}
                >
                  <ArrowRightOnRectangleIcon className="h-3.5 w-3.5 shrink-0" />
                  Sign out
                </button>
              </div>
            )}
          </div>

          {/* Menu button below xl */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="xl:hidden p-1.5 rounded-md text-content-secondary hover:text-content hover:bg-surface-hover transition-colors"
          >
            {mobileMenuOpen ? <XMarkIcon className="h-6 w-6" /> : <Bars3Icon className="h-6 w-6" />}
          </button>
        </div>
      </nav>

      {/* Navigation panel below xl */}
      {mobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-30 modal-backdrop animate-fade-in xl:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div
            className={`fixed z-40 top-[calc(var(--navbar-height)+0.5rem)] inset-x-2 sm:inset-x-4 py-2 xl:hidden animate-fade-in ${menu.panel}`}
          >
            {navigation.map(section => (
              <div key={section.name} className="py-1">
                <h3 className="eyebrow px-4 pt-2 pb-1">{section.name}</h3>
                {section.items.map(item => {
                  const Icon = item.icon;
                  const active = isActive(item.href);

                  return (
                    <Link
                      key={item.name}
                      to={item.href}
                      onClick={closeMenus}
                      className={`${menu.item} ${active ? 'border-bleu-atlantis text-bleu-atlantis' : ''}`}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span>{item.name}</span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Page content */}
      <main className="flex-1 w-full navbar-spacing px-4 sm:px-6 lg:px-8 pb-8">
        <Outlet />
      </main>
    </div>
  );
};

export default AppLayout;
