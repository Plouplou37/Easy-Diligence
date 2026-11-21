import React, { useState, useEffect, useRef } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  PlusIcon,
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
        { name: 'Due diligences', href: '/', icon: HomeIcon },
        { name: 'New due diligence', href: '/session/create', icon: PlusIcon },
        // Vector stores, called by what they hold.
        { name: 'Documents', href: '/vector-stores', icon: BookOpenIcon },
        // DD types. The questions open from their questionnaire, which keeps
        // this entry lit on /questions.
        { name: 'Questionnaires', href: '/dd-types', icon: TagIcon },
      ],
    },
    ...(isAdmin
      ? [
          {
            name: 'Administration',
            items: [{ name: 'Users', href: '/admin/users', icon: UsersIcon }],
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
    if (href === '/dd-types' && path === '/questions') return true;
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

  // The account button shows the user's initials.
  const initials =
    (user?.full_name || user?.username || '?')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part[0].toUpperCase())
      .join('') || '?';

  return (
    <div className="min-h-screen flex flex-col">
      {/* The bar at the top, full width */}
      <nav className="fixed top-0 inset-x-0 z-40 h-(--navbar-height) border-b border-border nav-bg">
        <div className="mx-auto max-w-[100rem] h-full flex items-center gap-6 px-4 sm:px-6 lg:px-8">
          <Link
            to="/"
            onClick={closeMenus}
            className="shrink-0 text-base font-bold tracking-tight whitespace-nowrap logo-gradient-hover"
          >
            Easy Diligence
          </Link>

          {/* Desktop links */}
          <div className="hidden xl:flex flex-1 min-w-0 items-center gap-1">
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
                className="ml-1 h-8 w-8 inline-flex items-center justify-center rounded-full bg-surface-hover border border-border text-xs font-semibold text-content hover:border-border-hover transition-colors"
                aria-label="Account menu"
                aria-expanded={userMenuOpen}
              >
                {initials}
              </button>

              {userMenuOpen && (
                <div
                  className={`absolute right-0 top-full mt-2 min-w-52 z-50 origin-top-right animate-scale-in ${menu.panel}`}
                >
                  <div className={menu.header}>
                    {/* An account has a full name, not a first and a last one: the
                      line used to be empty. */}
                    <p className="eyebrow">{user?.full_name || user?.username}</p>
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
              aria-label={mobileMenuOpen ? 'Close the menu' : 'Open the menu'}
              aria-expanded={mobileMenuOpen}
              className="xl:hidden p-1.5 rounded-md text-content-secondary hover:text-content hover:bg-surface-hover transition-colors"
            >
              {mobileMenuOpen ? (
                <XMarkIcon className="h-6 w-6" />
              ) : (
                <Bars3Icon className="h-6 w-6" />
              )}
            </button>
          </div>
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
            className={`fixed z-40 top-[calc(var(--navbar-height)+0.5rem)] inset-x-2 sm:inset-x-4 py-2 xl:hidden origin-top animate-scale-in ${menu.panel}`}
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
                      className={`${menu.item} ${active ? 'bg-surface-hover' : ''}`}
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
      <main className="flex-1 w-full navbar-spacing px-4 sm:px-6 lg:px-8 pb-12">
        <Outlet />
      </main>
    </div>
  );
};

export default AppLayout;
