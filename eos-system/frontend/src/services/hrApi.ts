/**
 * EOS System — HR API Service
 */

import apiClient from './apiClient';
import type {
  Employee,
  EmployeeCreate,
  Department,
  DepartmentCreate,
  Position,
  AttendanceRecord,
  AttendanceRecordCreate,
  PaginatedResponse,
} from '../types';

export const hrApi = {
  // =====================================================
  // Employees
  // =====================================================

  // List employees
  listEmployees: async (params?: {
    department_id?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Employee>> => {
    return apiClient.get('/hr/employees', { params });
  },

  // Get employee by ID
  getEmployee: async (id: string): Promise<Employee> => {
    return apiClient.get(`/hr/employees/${id}`);
  },

  // Create employee
  createEmployee: async (data: EmployeeCreate): Promise<Employee> => {
    return apiClient.post('/hr/employees', data);
  },

  // Update employee
  updateEmployee: async (id: string, data: Partial<EmployeeCreate>): Promise<Employee> => {
    return apiClient.put(`/hr/employees/${id}`, data);
  },

  // Delete employee
  deleteEmployee: async (id: string): Promise<void> => {
    return apiClient.delete(`/hr/employees/${id}`);
  },

  // Get employee attendance
  getEmployeeAttendance: async (
    employeeId: string,
    startDate?: string,
    endDate?: string
  ): Promise<AttendanceRecord[]> => {
    return apiClient.get(`/hr/employees/${employeeId}/attendance`, {
      params: { start_date: startDate, end_date: endDate },
    });
  },

  // Get employee payslips
  getEmployeePayslips: async (employeeId: string): Promise<any[]> => {
    return apiClient.get(`/hr/employees/${employeeId}/payslips`);
  },

  // =====================================================
  // Departments
  // =====================================================

  // List departments
  listDepartments: async (): Promise<Department[]> => {
    return apiClient.get('/hr/departments');
  },

  // Create department
  createDepartment: async (data: DepartmentCreate): Promise<Department> => {
    return apiClient.post('/hr/departments', data);
  },

  // Update department
  updateDepartment: async (id: string, data: Partial<DepartmentCreate>): Promise<Department> => {
    return apiClient.put(`/hr/departments/${id}`, data);
  },

  // Delete department
  deleteDepartment: async (id: string): Promise<void> => {
    return apiClient.delete(`/hr/departments/${id}`);
  },

  // =====================================================
  // Positions
  // =====================================================

  // List positions
  listPositions: async (departmentId?: string): Promise<Position[]> => {
    const params = departmentId ? { department_id: departmentId } : {};
    return apiClient.get('/hr/positions', { params });
  },

  // Create position
  createPosition: async (data: Partial<Position>): Promise<Position> => {
    return apiClient.post('/hr/positions', data);
  },

  // Update position
  updatePosition: async (id: string, data: Partial<Position>): Promise<Position> => {
    return apiClient.put(`/hr/positions/${id}`, data);
  },

  // Delete position
  deletePosition: async (id: string): Promise<void> => {
    return apiClient.delete(`/hr/positions/${id}`);
  },

  // =====================================================
  // Attendance
  // =====================================================

  // List attendance records
  listAttendance: async (params?: {
    employee_id?: string;
    start_date?: string;
    end_date?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<AttendanceRecord>> => {
    return apiClient.get('/hr/attendance', { params });
  },

  // Record attendance
  recordAttendance: async (data: AttendanceRecordCreate): Promise<AttendanceRecord> => {
    return apiClient.post('/hr/attendance', data);
  },

  // Clock in
  clockIn: async (employeeId: string): Promise<{ message: string }> => {
    return apiClient.post('/hr/attendance/clock-in', { employee_id: employeeId });
  },

  // Clock out
  clockOut: async (employeeId: string): Promise<{ message: string }> => {
    return apiClient.post('/hr/attendance/clock-out', { employee_id: employeeId });
  },

  // =====================================================
  // Payroll
  // =====================================================

  // List payroll runs
  listPayrollRuns: async (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<any>> => {
    return apiClient.get('/hr/payroll', { params });
  },

  // Run payroll
  runPayroll: async (data: {
    period_start: string;
    period_end: string;
    payment_date: string;
  }): Promise<any> => {
    return apiClient.post('/hr/payroll/run', data);
  },

  // Get payslip
  getPayslip: async (id: string): Promise<any> => {
    return apiClient.get(`/hr/payroll/payslips/${id}`);
  },

  // =====================================================
  // Leave Management
  // =====================================================

  // List leave requests
  listLeaveRequests: async (params?: {
    employee_id?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<any>> => {
    return apiClient.get('/hr/leave-requests', { params });
  },

  // Create leave request
  createLeaveRequest: async (data: any): Promise<any> => {
    return apiClient.post('/hr/leave-requests', data);
  },

  // Approve leave request
  approveLeaveRequest: async (id: string): Promise<{ message: string }> => {
    return apiClient.post(`/hr/leave-requests/${id}/approve`);
  },

  // Reject leave request
  rejectLeaveRequest: async (id: string, reason: string): Promise<{ message: string }> => {
    return apiClient.post(`/hr/leave-requests/${id}/reject`, { reason });
  },
};

export default hrApi;
