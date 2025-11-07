'use client'

import { useQuery } from 'react-query'
import { authApi } from '@/lib/api'
import { safeStorageGet, safeStorageSet, safeStorageRemove } from '@/lib/utils'
import { User } from '@/types'

export function useSession() {
  const {
    data: user,
    isLoading,
    error,
    refetch,
  } = useQuery<User>(
    'user',
    async () => {
      const token = safeStorageGet('access_token')
      if (!token) {
        throw new Error('No token found')
      }

      try {
        const response = await authApi.getProfile()
        return response
      } catch (error) {
        // Token might be expired, clear it
        safeStorageRemove('access_token')
        safeStorageRemove('user')
        throw error
      }
    },
    {
      retry: false,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  )

  const login = async (email: string, password: string) => {
    try {
      const response = await authApi.login({ email, password })
      const { access_token } = response

      // Store token and user data
      safeStorageSet('access_token', access_token)

      // Fetch user profile
      const userProfile = await authApi.getProfile()
      safeStorageSet('user', userProfile)

      // Refetch user data
      await refetch()

      return userProfile
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    safeStorageRemove('access_token')
    safeStorageRemove('user')
    window.location.href = '/'
  }

  const updateProfile = async (userData: Partial<User>) => {
    try {
      const response = await authApi.updateProfile(userData)
      safeStorageSet('user', response)
      await refetch()
      return response
    } catch (error) {
      throw error
    }
  }

  const hasPermission = (permission: string) => {
    if (!user) return false

    const permissions = {
      admin: [
        'view_all',
        'create_all',
        'edit_all',
        'delete_all',
        'manage_users',
        'view_analytics',
        'manage_departments',
      ],
      technician: [
        'view_department',
        'create_equipment',
        'edit_equipment',
        'complete_maintenance',
        'view_department_analytics',
      ],
      viewer: ['view_department'],
    }

    return permissions[user.role]?.includes(permission) || false
  }

  return {
    user,
    isLoading,
    isAuthenticated: !!user,
    error,
    login,
    logout,
    updateProfile,
    refetch,
    hasPermission,
  }
}