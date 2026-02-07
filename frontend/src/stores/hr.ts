import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';
import { EmployeeProfile, HRJobOpening, HRJobApplication, HRLeaveRequest } from '@/types';

export interface HRStats {
  total_employees: number;
  open_positions: number;
  pending_time_off: number;
  expiring_certifications: number;
  new_hires_this_month: number;
  turnover_rate: number;
  total_applications?: number;
  interviews_scheduled?: number;
}

export interface DepartmentHeadcount {
  name: string;
  count: number;
  percentage: number;
}

export interface ExpiringCert {
  id: string;
  employee: string;
  cert: string;
  expires: string;
  priority: string;
}

interface HRState {
  stats: HRStats | null;
  headcount: DepartmentHeadcount[];
  expiringCerts: ExpiringCert[];
  employees: EmployeeProfile[];
  selectedEmployee: EmployeeProfile | null;
  
  // Recruitment
  jobOpenings: HRJobOpening[];
  selectedJobOpening: HRJobOpening | null;
  applications: HRJobApplication[];
  
  // Leave Management
  leaveRequests: HRLeaveRequest[];
  
  loading: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Stats & Core
  fetchStats: () => Promise<void>;
  fetchHeadcount: () => Promise<void>;
  fetchExpiringCerts: () => Promise<void>;
  
  // Employees
  fetchEmployees: () => Promise<void>;
  createEmployee: (data: Partial<EmployeeProfile>) => Promise<void>;
  updateEmployee: (id: string, data: Partial<EmployeeProfile>) => Promise<void>;
  deleteEmployee: (id: string) => Promise<void>;
  setSelectedEmployee: (employee: EmployeeProfile | null) => void;
  
  // Job Openings
  fetchJobOpenings: () => Promise<void>;
  createJobOpening: (data: Partial<HRJobOpening>) => Promise<void>;
  updateJobOpening: (id: string, data: Partial<HRJobOpening>) => Promise<void>;
  deleteJobOpening: (id: string) => Promise<void>;
  setSelectedJobOpening: (job: HRJobOpening | null) => void;
  
  // Applications
  fetchApplications: (jobId?: string) => Promise<void>;
  createApplication: (data: Partial<HRJobApplication>) => Promise<void>;
  updateApplicationStatus: (id: string, status: HRJobApplication['status']) => Promise<void>;
  
  // Leave Requests
  fetchLeaveRequests: () => Promise<void>;
  createLeaveRequest: (data: Partial<HRLeaveRequest>) => Promise<void>;
  approveLeaveRequest: (id: string) => Promise<void>;
  rejectLeaveRequest: (id: string) => Promise<void>;
}

export const useHRStore = create<HRState>()(
  devtools(
    persist(
      (set, get) => ({
        stats: null,
        headcount: [],
        expiringCerts: [],
        employees: [],
        selectedEmployee: null,
        jobOpenings: [],
        selectedJobOpening: null,
        applications: [],
        leaveRequests: [],
        loading: false,
        isLoading: false,
        error: null,

        fetchStats: async () => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const data = await apiClient.get<HRStats>('/hr/stats');
            set({ stats: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        fetchHeadcount: async () => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const data = await apiClient.get<DepartmentHeadcount[]>('/hr/headcount');
            set({ headcount: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        fetchExpiringCerts: async () => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const data = await apiClient.get<ExpiringCert[]>('/hr/expiring-certs');
            set({ expiringCerts: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        // ========== EMPLOYEES ==========
        fetchEmployees: async () => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const data = await apiClient.get<EmployeeProfile[]>('/hr/employees');
            set({ employees: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        createEmployee: async (data) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const newEmployee = await apiClient.post<EmployeeProfile>('/hr/employees', data);
            set((state) => ({ 
              employees: [...state.employees, newEmployee],
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
            await get().fetchHeadcount();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        updateEmployee: async (id, data) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const updated = await apiClient.put<EmployeeProfile>('/hr/employees/' + id, data);
            set((state) => ({
              employees: state.employees.map(e => e.id === id ? updated : e),
              selectedEmployee: state.selectedEmployee?.id === id ? updated : state.selectedEmployee,
              loading: false,
              isLoading: false
            }));
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        deleteEmployee: async (id) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            await apiClient.delete('/hr/employees/' + id);
            set((state) => ({
              employees: state.employees.filter(e => e.id !== id),
              selectedEmployee: state.selectedEmployee?.id === id ? null : state.selectedEmployee,
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        setSelectedEmployee: (employee) => set({ selectedEmployee: employee }),

        // ========== JOB OPENINGS ==========
        fetchJobOpenings: async () => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const data = await apiClient.get<HRJobOpening[]>('/hr/job-openings');
            set({ jobOpenings: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        createJobOpening: async (data) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const newJob = await apiClient.post<HRJobOpening>('/hr/job-openings', data);
            set((state) => ({
              jobOpenings: [...state.jobOpenings, newJob],
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        updateJobOpening: async (id, data) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const updated = await apiClient.put<HRJobOpening>('/hr/job-openings/' + id, data);
            set((state) => ({
              jobOpenings: state.jobOpenings.map(j => j.id === id ? updated : j),
              selectedJobOpening: state.selectedJobOpening?.id === id ? updated : state.selectedJobOpening,
              loading: false,
              isLoading: false
            }));
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        deleteJobOpening: async (id) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            await apiClient.delete('/hr/job-openings/' + id);
            set((state) => ({
              jobOpenings: state.jobOpenings.filter(j => j.id !== id),
              selectedJobOpening: state.selectedJobOpening?.id === id ? null : state.selectedJobOpening,
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        setSelectedJobOpening: (job) => set({ selectedJobOpening: job }),

        // ========== APPLICATIONS ==========
        fetchApplications: async (jobId) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const url = jobId ? '/hr/applications?job_opening_id=' + jobId : '/hr/applications';
            const data = await apiClient.get<HRJobApplication[]>(url);
            set({ applications: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        createApplication: async (data) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const newApp = await apiClient.post<HRJobApplication>('/hr/applications', data);
            set((state) => ({
              applications: [...state.applications, newApp],
              loading: false,
              isLoading: false
            }));
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        updateApplicationStatus: async (id, status) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const updated = await apiClient.put<HRJobApplication>('/hr/applications/' + id, { status });
            set((state) => ({
              applications: state.applications.map(a => a.id === id ? updated : a),
              loading: false,
              isLoading: false
            }));
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        // ========== LEAVE REQUESTS ==========
        fetchLeaveRequests: async () => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const data = await apiClient.get<HRLeaveRequest[]>('/hr/leave-requests');
            set({ leaveRequests: data, loading: false, isLoading: false });
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
          }
        },

        createLeaveRequest: async (data) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const newRequest = await apiClient.post<HRLeaveRequest>('/hr/leave-requests', data);
            set((state) => ({
              leaveRequests: [...state.leaveRequests, newRequest],
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        approveLeaveRequest: async (id) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const updated = await apiClient.put<HRLeaveRequest>('/hr/leave-requests/' + id + '/approve', {});
            set((state) => ({
              leaveRequests: state.leaveRequests.map(r => r.id === id ? updated : r),
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },

        rejectLeaveRequest: async (id) => {
          set({ loading: true, isLoading: true, error: null });
          try {
            const updated = await apiClient.put<HRLeaveRequest>('/hr/leave-requests/' + id + '/reject', {});
            set((state) => ({
              leaveRequests: state.leaveRequests.map(r => r.id === id ? updated : r),
              loading: false,
              isLoading: false
            }));
            await get().fetchStats();
          } catch (error) {
            set({ error: (error as Error).message, loading: false, isLoading: false });
            throw error;
          }
        },
      }),
      { name: 'hr-storage' }
    )
  )
);
