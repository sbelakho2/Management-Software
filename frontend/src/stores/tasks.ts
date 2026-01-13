import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { taskApi, type TaskListParams, type CreateTaskData, type UpdateTaskData } from '@/api/task';
import type { Task, TaskStatus } from '@/types';
import { getErrorMessage } from '@/lib/error-utils';

interface TasksState {
  tasks: Task[];
  loading: boolean;
  error: string | null;

  fetchTasks: (params?: TaskListParams) => Promise<void>;
  createTask: (data: CreateTaskData) => Promise<Task>;
  updateTask: (id: string, data: UpdateTaskData) => Promise<Task>;
  deleteTask: (id: string) => Promise<void>;
  moveTask: (id: string, status: TaskStatus) => Promise<Task>;
}

export const useTasksStore = create<TasksState>()(
  devtools((set, get) => ({
    tasks: [],
    loading: false,
    error: null,

    fetchTasks: async (params) => {
      set({ loading: true, error: null });
      try {
        const response = await taskApi.list(params);
        set({ tasks: response.items, loading: false });
      } catch (error: unknown) {
        set({ error: getErrorMessage(error), loading: false });
      }
    },

    createTask: async (data) => {
      set({ loading: true, error: null });
      try {
        const newTask = await taskApi.create(data);
        set((state) => ({ 
          tasks: [newTask, ...state.tasks], 
          loading: false 
        }));
        return newTask;
      } catch (error: unknown) {
        set({ error: getErrorMessage(error), loading: false });
        throw error;
      }
    },

    updateTask: async (id, data) => {
      set({ loading: true, error: null });
      try {
        const updatedTask = await taskApi.update(id, data);
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === id ? updatedTask : t)),
          loading: false,
        }));
        return updatedTask;
      } catch (error: unknown) {
        set({ error: getErrorMessage(error), loading: false });
        throw error;
      }
    },

    deleteTask: async (id) => {
      set({ loading: true, error: null });
      try {
        await taskApi.delete(id);
        set((state) => ({
          tasks: state.tasks.filter((t) => t.id !== id),
          loading: false,
        }));
      } catch (error: unknown) {
        set({ error: getErrorMessage(error), loading: false });
        throw error;
      }
    },

    moveTask: async (id, status) => {
      try {
        const updatedTask = await taskApi.move(id, status);
        set((state) => ({
          tasks: state.tasks.map((t) => (t.id === id ? updatedTask : t)),
        }));
        return updatedTask;
      } catch (error: unknown) {
        set({ error: getErrorMessage(error) });
        throw error;
      }
    },
  }))
);
