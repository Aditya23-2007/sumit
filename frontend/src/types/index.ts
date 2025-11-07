// User Types
export type UserRole = 'admin' | 'technician' | 'viewer'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  department_id?: string
  created_at: string
  updated_at: string
}

export interface CreateUserData {
  email: string
  full_name: string
  password: string
  role: UserRole
  department_id?: string
}

// Department Types
export interface Department {
  id: string
  name: string
  description?: string
  location?: string
  created_at: string
}

export interface CreateDepartmentData {
  name: string
  description?: string
  location?: string
}

// Equipment Types
export type EquipmentStatus = 'active' | 'maintenance' | 'retired'

export interface Equipment {
  id: string
  name: string
  description?: string
  ai_generated_description?: string
  department_id: string
  maintenance_interval_months?: number
  last_maintenance_date?: string
  next_maintenance_date?: string
  status: EquipmentStatus
  qr_code_id?: string
  created_at: string
  updated_at: string
}

export interface CreateEquipmentData {
  name: string
  description?: string
  department_id: string
  usage_intensity?: string
  equipment_type?: string
}

export interface EquipmentWithTasks extends Equipment {
  maintenance_tasks: MaintenanceTask[]
}

// Maintenance Task Types
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

export interface MaintenanceTask {
  id: string
  equipment_id: string
  task_name: string
  task_description?: string
  priority: TaskPriority
  estimated_duration_hours?: number
  required_tools?: string[]
  created_at: string
}

export interface CreateMaintenanceTaskData {
  equipment_id: string
  task_name: string
  task_description?: string
  priority: TaskPriority
  estimated_duration_hours?: number
  required_tools?: string[]
}

// Maintenance Log Types
export interface MaintenanceLog {
  id: string
  equipment_id: string
  performed_by: string
  tasks_completed: Record<string, boolean>
  notes?: string
  duration_hours?: number
  cost?: number
  performed_at: string
}

export interface CreateMaintenanceLogData {
  equipment_id: string
  tasks_completed: Record<string, boolean>
  notes?: string
  duration_hours?: number
  cost?: number
}

// Alert Types
export type AlertType = 'due_soon' | 'overdue' | 'predicted_failure'

export interface MaintenanceAlert {
  id: string
  equipment_id: string
  alert_type: AlertType
  message: string
  scheduled_date?: string
  sent_at?: string
  acknowledged_at?: string
  acknowledged_by?: string
}

export interface AlertStats {
  total_alerts: number
  unacknowledged: number
  due_soon: number
  overdue: number
  predicted_failure: number
}

// Dashboard Types
export interface DashboardStats {
  equipment: {
    total: number
    active: number
    maintenance: number
    due_soon: number
    overdue: number
  }
  alerts: {
    total: number
    active: number
  }
}

export interface UpcomingMaintenance {
  equipment_id: string
  equipment_name: string
  department_name: string
  next_maintenance_date: string
  days_until_maintenance: number
  priority: 'low' | 'medium' | 'high'
}

export interface RecentAlert {
  alert_id: string
  equipment_id: string
  equipment_name: string
  department_name: string
  alert_type: AlertType
  message: string
  created_at: string
}

export interface MaintenancePerformance {
  period_days: number
  completed_maintenance: number
  average_duration_hours: number
  total_cost: number
  top_equipment: Array<{
    equipment_name: string
    maintenance_count: number
  }>
}

export interface EquipmentByDepartment {
  department_name: string
  total_equipment: number
  active_equipment: number
}

export interface AlertsTimeline {
  [date: string]: {
    due_soon: number
    overdue: number
    predicted_failure: number
  }
}

// API Response Types
export interface ApiResponse<T> {
  data?: T
  message?: string
  error?: string
  success?: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

// Auth Types
export interface LoginCredentials {
  email: string
  password: string
}

export interface AuthToken {
  access_token: string
  token_type: string
}

// Form Types
export interface SelectOption {
  value: string
  label: string
}

export interface TableColumn<T = any> {
  key: keyof T | string
  label: string
  sortable?: boolean
  render?: (value: any, item: T) => React.ReactNode
}

// Filter Types
export interface EquipmentFilters {
  department_id?: string
  status?: EquipmentStatus
  search?: string
}

export interface MaintenanceFilters {
  equipment_id?: string
  date_range?: {
    start: string
    end: string
  }
  performed_by?: string
}

export interface AlertFilters {
  alert_type?: AlertType
  acknowledged?: boolean
  equipment_id?: string
}