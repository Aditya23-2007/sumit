'use client'

import { User } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { MobileMenuButton } from './MobileMenuButton'
import {
  BellIcon,
  MagnifyingGlassIcon,
  UserCircleIcon
} from '@heroicons/react/24/outline'

interface HeaderProps {
  user: User
  onMenuClick: () => void
}

export function Header({ user, onMenuClick }: HeaderProps) {
  const [notificationCount] = useState(5) // This would come from a real API

  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Left side */}
          <div className="flex items-center">
            <MobileMenuButton onClick={onMenuClick} />

            <div className="hidden md:block ml-10">
              <div className="flex items-baseline space-x-4">
                <h1 className="text-xl font-semibold text-gray-900">
                  Predictive Maintenance Dashboard
                </h1>
              </div>
            </div>
          </div>

          {/* Center - Search */}
          <div className="hidden md:block flex-1 max-w-lg mx-8">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                placeholder="Search equipment, maintenance tasks..."
                type="search"
              />
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <div className="relative">
              <Button variant="outline" size="sm" className="relative p-2">
                <BellIcon className="h-5 w-5" />
                {notificationCount > 0 && (
                  <span className="absolute -top-1 -right-1 h-4 w-4 bg-danger-600 text-white text-xs rounded-full flex items-center justify-center">
                    {notificationCount > 9 ? '9+' : notificationCount}
                  </span>
                )}
              </Button>
            </div>

            {/* User menu */}
            <div className="flex items-center space-x-3">
              <div className="hidden md:block text-right">
                <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
                <p className="text-xs text-gray-500 capitalize">{user.role}</p>
              </div>

              <div className="h-8 w-8 bg-primary-100 rounded-full flex items-center justify-center">
                <UserCircleIcon className="h-6 w-6 text-primary-600" />
              </div>

              <Badge variant="info" className="hidden md:block">
                {user.role}
              </Badge>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}