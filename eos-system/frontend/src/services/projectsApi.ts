/**
 * EOS System — Projects API Service
 */

import apiClient from './apiClient';
import type {
  Project,
  ProjectCreate,
  Task,
  TaskCreate,
  TimeEntry,
  TimeEntryCreate,
  PaginatedResponse,
} from '../types';

export const projectsApi = {
  // =====================================================
  // Projects
  // =====================================================

  // List projects
  listProjects: async (params?: {
    status?: string;
    manager_id?: string;
    client_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Project>> => {
    return apiClient.get('/projects', { params });
  },

  // Get project by ID
  getProject: async (id: string): Promise<Project> => {
    return apiClient.get(`/projects/${id}`);
  },

  // Create project
  createProject: async (data: ProjectCreate): Promise<Project> => {
    return apiClient.post('/projects', data);
  },

  // Update project
  updateProject: async (id: string, data: Partial<ProjectCreate>): Promise<Project> => {
    return apiClient.put(`/projects/${id}`, data);
  },

  // Delete project
  deleteProject: async (id: string): Promise<void> => {
    return apiClient.delete(`/projects/${id}`);
  },

  // Update project status
  updateProjectStatus: async (id: string, status: string): Promise<{ message: string }> => {
    return apiClient.post(`/projects/${id}/status`, { status });
  },

  // Update project progress
  updateProjectProgress: async (id: string, progress: number): Promise<{ message: string }> => {
    return apiClient.post(`/projects/${id}/progress`, { progress });
  },

  // =====================================================
  // Tasks
  // =====================================================

  // List tasks for a project
  listTasks: async (
    projectId: string,
    params?: {
      assignee_id?: string;
      status?: string;
      priority?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<PaginatedResponse<Task>> => {
    return apiClient.get(`/projects/${projectId}/tasks`, { params });
  },

  // Get task by ID
  getTask: async (projectId: string, taskId: string): Promise<Task> => {
    return apiClient.get(`/projects/${projectId}/tasks/${taskId}`);
  },

  // Create task
  createTask: async (projectId: string, data: TaskCreate): Promise<Task> => {
    return apiClient.post(`/projects/${projectId}/tasks`, data);
  },

  // Update task
  updateTask: async (
    projectId: string,
    taskId: string,
    data: Partial<TaskCreate>
  ): Promise<Task> => {
    return apiClient.put(`/projects/${projectId}/tasks/${taskId}`, data);
  },

  // Delete task
  deleteTask: async (projectId: string, taskId: string): Promise<void> => {
    return apiClient.delete(`/projects/${projectId}/tasks/${taskId}`);
  },

  // Update task status
  updateTaskStatus: async (
    projectId: string,
    taskId: string,
    status: string
  ): Promise<{ message: string }> => {
    return apiClient.post(`/projects/${projectId}/tasks/${taskId}/status`, { status });
  },

  // =====================================================
  // Time Entries
  // =====================================================

  // List time entries
  listTimeEntries: async (params?: {
    task_id?: string;
    project_id?: string;
    employee_id?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<TimeEntry>> => {
    return apiClient.get('/projects/time-entries', { params });
  },

  // Create time entry
  createTimeEntry: async (data: TimeEntryCreate): Promise<TimeEntry> => {
    return apiClient.post('/projects/time-entries', data);
  },

  // Delete time entry
  deleteTimeEntry: async (id: string): Promise<void> => {
    return apiClient.delete(`/projects/time-entries/${id}`);
  },

  // Get time summary by project
  getTimeSummaryByProject: async (projectId: string): Promise<any> => {
    return apiClient.get(`/projects/${projectId}/time-summary`);
  },

  // Get time summary by employee
  getTimeSummaryByEmployee: async (
    employeeId: string,
    startDate?: string,
    endDate?: string
  ): Promise<any> => {
    return apiClient.get(`/projects/time-summary/employee/${employeeId}`, {
      params: { start_date: startDate, end_date: endDate },
    });
  },

  // =====================================================
  // Milestones
  // =====================================================

  // List milestones
  listMilestones: async (projectId: string): Promise<any[]> => {
    return apiClient.get(`/projects/${projectId}/milestones`);
  },

  // Create milestone
  createMilestone: async (projectId: string, data: any): Promise<any> => {
    return apiClient.post(`/projects/${projectId}/milestones`, data);
  },

  // Update milestone
  updateMilestone: async (
    projectId: string,
    milestoneId: string,
    data: any
  ): Promise<any> => {
    return apiClient.put(`/projects/${projectId}/milestones/${milestoneId}`, data);
  },

  // Delete milestone
  deleteMilestone: async (projectId: string, milestoneId: string): Promise<void> => {
    return apiClient.delete(`/projects/${projectId}/milestones/${milestoneId}`);
  },

  // =====================================================
  // Reports
  // =====================================================

  // Get project progress report
  getProjectProgressReport: async (): Promise<any[]> => {
    return apiClient.get('/projects/reports/progress');
  },

  // Get time tracking report
  getTimeTrackingReport: async (
    startDate: string,
    endDate: string
  ): Promise<any> => {
    return apiClient.get('/projects/reports/time-tracking', {
      params: { start_date: startDate, end_date: endDate },
    });
  },

  // Get budget vs actual report
  getBudgetVsActualReport: async (projectId: string): Promise<any> => {
    return apiClient.get(`/projects/${projectId}/reports/budget`);
  },
};

export default projectsApi;
