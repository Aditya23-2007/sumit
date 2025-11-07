import axios, { AxiosInstance, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor to handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('access_token')
          localStorage.removeItem('user')
          window.location.href = '/'
          toast.error('Your session has expired. Please log in again.')
        } else if (error.response?.status >= 500) {
          toast.error('Server error. Please try again later.')
        } else if (error.response?.data?.message) {
          toast.error(error.response.data.message)
        } else if (error.code === 'ECONNABORTED') {
          toast.error('Request timeout. Please check your connection.')
        } else if (!error.response) {
          toast.error('Network error. Please check your connection.')
        }
        return Promise.reject(error)
      }
    )
  }

  // Generic request method
  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    url: string,
    data?: any,
    params?: any
  ): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.request({
        method,
        url,
        data,
        params,
      })
      return response.data
    } catch (error) {
      throw error
    }
  }

  // GET request
  async get<T>(url: string, params?: any): Promise<T> {
    return this.request<T>('GET', url, undefined, params)
  }

  // POST request
  async post<T>(url: string, data?: any): Promise<T> {
    return this.request<T>('POST', url, data)
  }

  // PUT request
  async put<T>(url: string, data?: any): Promise<T> {
    return this.request<T>('PUT', url, data)
  }

  // DELETE request
  async delete<T>(url: string): Promise<T> {
    return this.request<T>('DELETE', url)
  }

  // PATCH request
  async patch<T>(url: string, data?: any): Promise<T> {
    return this.request<T>('PATCH', url, data)
  }
}

export const apiClient = new ApiClient()

// Specific API endpoints
export const authApi = {
  login: (credentials: { email: string; password: string }) =>
    apiClient.post<{ access_token: string; token_type: string }>('/api/v1/auth/login', credentials),

  register: (userData: {
    email: string
    password: string
    full_name: string
    role: string
    department_id?: string
  }) => apiClient.post<any>('/api/v1/auth/register', userData),

  getProfile: () => apiClient.get<any>('/api/v1/auth/profile'),

  updateProfile: (userData: any) => apiClient.put<any>('/api/v1/auth/profile', userData),
}

export const equipmentApi = {
  getEquipment: (params?: {
    skip?: number
    limit?: number
    department_id?: string
    status?: string
  }) => apiClient.get<any[]>('/api/v1/equipment', params),

  getEquipmentById: (id: string) => apiClient.get<any>(`/api/v1/equipment/${id}`),

  createEquipment: (data: any) => apiClient.post<any>('/api/v1/equipment', data),

  updateEquipment: (id: string, data: any) => apiClient.put<any>(`/api/v1/equipment/${id}`, data),

  deleteEquipment: (id: string) => apiClient.delete<any>(`/api/v1/equipment/${id}`),

  analyzeEquipment: (id: string) => apiClient.post<any>(`/api/v1/equipment/${id}/ai-analyze`),

  getQRCode: (id: string) => apiClient.get<{ qr_code_url: string }>(`/api/v1/equipment/${id}/qr-code`),
}

export const maintenanceApi = {
  getSchedule: (params?: {
    days_ahead?: number
    department_id?: string
  }) => apiClient.get<any[]>('/api/v1/maintenance/schedule', params),

  completeMaintenance: (data: any) => apiClient.post<any>('/api/v1/maintenance/complete', data),

  getHistory: (equipmentId: string, params?: {
    skip?: number
    limit?: number
  }) => apiClient.get<any[]>(`/api/v1/maintenance/history/${equipmentId}`, params),

  getTasks: (equipmentId: string) => apiClient.get<any[]>(`/api/v1/maintenance/tasks/${equipmentId}`),

  getMyTasks: () => apiClient.get<any[]>('/api/v1/maintenance/my-tasks'),

  getOverdue: () => apiClient.get<any[]>('/api/v1/maintenance/overdue'),
}

export const alertsApi = {
  getAlerts: (params?: {
    skip?: number
    limit?: number
    alert_type?: string
    acknowledged?: boolean
  }) => apiClient.get<any[]>('/api/v1/alerts', params),

  getActiveAlerts: () => apiClient.get<any[]>('/api/v1/alerts/active'),

  acknowledgeAlert: (id: string, data: { acknowledged: boolean }) =>
    apiClient.put<any>(`/api/v1/alerts/${id}/acknowledge`, data),

  testAlert: () => apiClient.post<any>('/api/v1/alerts/test'),

  getCount: () => apiClient.get<any>('/api/v1/alerts/count'),

  deleteAlert: (id: string) => apiClient.delete<any>(`/api/v1/alerts/${id}`),
}

export const departmentsApi = {
  getDepartments: () => apiClient.get<any[]>('/api/v1/departments'),

  getDepartmentById: (id: string) => apiClient.get<any>(`/api/v1/departments/${id}`),

  createDepartment: (data: any) => apiClient.post<any>('/api/v1/departments', data),

  updateDepartment: (id: string, data: any) => apiClient.put<any>(`/api/v1/departments/${id}`, data),

  getEquipmentCount: (id: string) => apiClient.get<any>(`/api/v1/departments/${id}/equipment-count`),

  getStats: (id: string) => apiClient.get<any>(`/api/v1/departments/${id}/stats`),
}

export const dashboardApi = {
  getStats: () => apiClient.get<any>('/api/v1/dashboard/stats'),

  getUpcomingMaintenance: (params?: {
    days?: number
    limit?: number
  }) => apiClient.get<any[]>('/api/v1/dashboard/upcoming-maintenance', params),

  getRecentAlerts: (params?: { limit?: number }) =>
    apiClient.get<any[]>('/api/v1/dashboard/recent-alerts', params),

  getMaintenancePerformance: (params?: { days?: number }) =>
    apiClient.get<any>('/api/v1/dashboard/maintenance-performance', params),

  getEquipmentByDepartment: () => apiClient.get<any[]>('/api/v1/dashboard/equipment-by-department'),

  getAlertsTimeline: (params?: { days?: number }) =>
    apiClient.get<any>('/api/v1/dashboard/alerts-timeline', params),
}

export default apiClient