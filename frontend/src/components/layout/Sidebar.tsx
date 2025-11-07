'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useSession } from '@/hooks/useSession'
import { Badge } from '@/components/ui/Badge'
import {
  HomeIcon,
  WrenchScrewdriverIcon,
  BellIcon,
  ChartBarIcon,
  BuildingOfficeIcon,
  CogIcon,
  ArrowRightOnRectangleIcon,
  UserCircleIcon,
  QrCodeIcon
} from '@heroicons/react/24/outline'
import { useState } from 'react'
import Link from 'next/link'

interface SidebarProps {
  onClose?: () => void
}

export function Sidebar({ onClose }: SidebarProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, logout, hasPermission } = useSession()
  const [alertsCount] = useState(3) // This would come from a real API

  const navigation = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: HomeIcon,
      permission: 'view_department',
    },
    {
      name: 'Equipment',
      href: '/equipment',
      icon: WrenchScrewdriverIcon,
      permission: 'view_department',
      badge: user?.role === 'admin' ? 'New' : undefined,
    },
    {
      name: 'Maintenance',
      href: '/maintenance',
      icon: WrenchScrewdriverIcon,
      permission: 'view_department',
    },
    {
      name: 'Alerts',
      href: '/alerts',
      icon: BellIcon,
      permission: 'view_department',
      badge: alertsCount > 0 ? alertsCount.toString() : undefined,
    },
    {
      name: 'Analytics',
      href: '/analytics',
      icon: ChartBarIcon,
      permission: 'view_department_analytics',
    },
    {
      name: 'Departments',
      href: '/departments',
      icon: BuildingOfficeIcon,
      permission: 'manage_departments',
    },
    {
      name: 'Settings',
      href: '/settings',
      icon: CogIcon,
      permission: 'view_all',
    },
  ].filter(item => hasPermission(item.permission))

  const handleNavigation = (href: string) => {
    router.push(href)
    onClose?.()
  }

  const handleLogout = () => {
    logout()
    onClose?.()
  }

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Logo */}
      <div className="flex items-center h-16 flex-shrink-0 px-4 border-b border-gray-200">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="ml-3">
            <h1 className="text-lg font-semibold text-gray-900">Maintenance</h1>
            <p className="text-xs text-gray-500">Predictive System</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <button
              key={item.name}
              onClick={() => handleNavigation(item.href)}
              className={`
                w-full flex items-center justify-between px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200
                ${isActive
                  ? 'bg-primary-100 text-primary-700 border-r-2 border-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }
              `}
            >
              <div className="flex items-center">
                <item.icon className="mr-3 h-5 w-5" />
                {item.name}
              </div>
              {item.badge && (
                <Badge variant={isActive ? 'primary' : 'info'} size="sm">
                  {item.badge}
                </Badge>
              )}
            </button>
          )
        })}
      </nav>

      {/* User section */}
      <div className="flex-shrink-0 border-t border-gray-200 p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <UserCircleIcon className="h-8 w-8 text-gray-400" />
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-gray-700">{user?.full_name}</p>
            <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
          </div>
        </div>

        <div className="mt-4 space-y-1">
          <button
            onClick={() => handleNavigation('/profile')}
            className="w-full flex items-center px-3 py-2 text-sm text-gray-600 rounded-md hover:bg-gray-50 hover:text-gray-900"
          >
            <UserCircleIcon className="mr-3 h-5 w-5" />
            Your Profile
          </button>

          {hasPermission('view_all') && (
            <button
              onClick={() => handleNavigation('/admin')}
              className="w-full flex items-center px-3 py-2 text-sm text-gray-600 rounded-md hover:bg-gray-50 hover:text-gray-900"
            >
              <CogIcon className="mr-3 h-5 w-5" />
              Admin Settings
            </button>
          )}

          <button
            onClick={handleLogout}
            className="w-full flex items-center px-3 py-2 text-sm text-red-600 rounded-md hover:bg-red-50 hover:text-red-900"
          >
            <ArrowRightOnRectangleIcon className="mr-3 h-5 w-5" />
            Sign out
          </button>
        </div>
      </div>
    </div>
  )
}