'use client'

import { useSession } from '@/hooks/useSession'
import { LoginForm } from '@/components/auth/LoginForm'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'

export default function Home() {
  const { user, isLoading } = useSession()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <LoginForm />
  }

  return <DashboardLayout />
}