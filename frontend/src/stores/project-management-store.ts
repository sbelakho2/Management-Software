import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { apiClient } from '@/api/client';

// ============================================================
// Types
// ============================================================

export type ProjectStatus = 'planning' | 'active' | 'on_hold' | 'completed' | 'archived' | 'cancelled';
export type ProjectType = 'standard' | 'scrum' | 'kanban' | 'hybrid' | 'npi' | 'kaizen' | 'a3' | 'maintenance';

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  project_type: ProjectType;
  status: ProjectStatus;
  owner_id?: string | null;
  is_private: boolean;
  start_date?: string | null;
  target_end_date?: string | null;
  created_at: string;
  updated_at: string;
  progress_percentage?: number;
}

export type EpicStatus = 'new' | 'in_progress' | 'done' | 'closed';

export interface Epic {
  id: string;
  project_id: string;
  ref: number;
  subject: string;
  description?: string | null;
  status: EpicStatus;
  created_at: string;
  updated_at: string;
}

export type SprintStatus = 'planned' | 'active' | 'completed' | 'cancelled';

export interface Sprint {
  id: string;
  project_id: string;
  name: string;
  slug: string;
  status: SprintStatus;
  start_date: string;
  end_date: string;
  created_at: string;
  updated_at: string;
}

export type UserStoryStatus = 'new' | 'ready' | 'in_progress' | 'ready_for_test' | 'done' | 'archived';

export interface UserStory {
  id: string;
  project_id: string;
  ref: number;
  subject: string;
  description?: string | null;
  status: UserStoryStatus;
  priority: number;
  epic_id?: string | null;
  sprint_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Subtask {
  id: string;
  user_story_id: string;
  ref: number;
  subject: string;
  description?: string | null;
  is_closed: boolean;
  created_at: string;
  updated_at: string;
}

export interface StoryComment {
  id: string;
  user_story_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message?: string;
}

interface ApiPaginated<T> {
  success: boolean;
  data: T;
  pagination: {
    page: number;
    page_size: number;
    total_pages: number;
    total_items: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

async function apiGet<T>(path: string): Promise<T> {
  return apiClient.get<T>(`/project-management${path}`);
}

async function apiSend<T>(path: string, method: 'POST' | 'PATCH' | 'DELETE', body?: unknown): Promise<T> {
  if (method === 'POST') return apiClient.post<T>(`/project-management${path}`, body);
  if (method === 'PATCH') return apiClient.patch<T>(`/project-management${path}`, body);
  return apiClient.delete<T>(`/project-management${path}`);
}

// ============================================================
// Store
// ============================================================

interface ProjectManagementState {
  projects: Project[];
  selectedProject: Project | null;
  epics: Epic[];
  sprints: Sprint[];
  stories: UserStory[];
  subtasksByStoryId: Record<string, Subtask[]>;
  commentsByStoryId: Record<string, StoryComment[]>;

  isLoading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  fetchProjectById: (id: string) => Promise<Project | null>;
  createProject: (payload: Partial<Project> & { name: string }) => Promise<Project>;
  updateProject: (id: string, updates: Partial<Project>) => Promise<Project>;

  fetchEpics: (projectId: string) => Promise<void>;
  createEpic: (projectId: string, subject: string, description?: string) => Promise<Epic>;

  fetchSprints: (projectId: string) => Promise<void>;
  createSprint: (projectId: string, name: string, start_date: string, end_date: string) => Promise<Sprint>;

  fetchStories: (projectId: string) => Promise<void>;
  createStory: (payload: { project_id: string; subject: string; priority?: number; epic_id?: string | null; sprint_id?: string | null; description?: string }) => Promise<UserStory>;

  fetchSubtasks: (storyId: string) => Promise<void>;
  createSubtask: (storyId: string, subject: string, description?: string) => Promise<Subtask>;
  updateSubtask: (subtaskId: string, updates: Partial<Pick<Subtask, 'is_closed' | 'subject' | 'description'>>) => Promise<Subtask>;

  fetchStoryComments: (storyId: string) => Promise<void>;
  createStoryComment: (storyId: string, content: string) => Promise<StoryComment>;

  updateStoryStatus: (storyId: string, status: UserStoryStatus) => Promise<UserStory>;
  updateStory: (storyId: string, updates: Partial<UserStory>) => Promise<UserStory>;

  clearError: () => void;
}

export const useProjectManagementStore = create<ProjectManagementState>()(
  devtools((set, get) => ({
    projects: [],
    selectedProject: null,
    epics: [],
    sprints: [],
    stories: [],
    subtasksByStoryId: {},
    commentsByStoryId: {},
    isLoading: false,
    error: null,

    clearError: () => set({ error: null }),

    fetchProjects: async () => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiPaginated<Project[]>>('/projects?page=1&page_size=50');
        set({ projects: res.data, isLoading: false });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load projects', isLoading: false });
      }
    },

    fetchProjectById: async (id: string) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiEnvelope<Project>>(`/projects/${id}`);
        set({ selectedProject: res.data, isLoading: false });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load project', isLoading: false });
        return null;
      }
    },

    createProject: async (payload) => {
      set({ isLoading: true, error: null });
      const body = {
        name: payload.name,
        description: payload.description ?? null,
        project_type: payload.project_type ?? 'standard',
        status: payload.status ?? 'planning',
        is_private: payload.is_private ?? false,
        start_date: payload.start_date ?? null,
        target_end_date: payload.target_end_date ?? null,
        slug: payload.slug ?? undefined,
      };
      try {
        const res = await apiSend<ApiEnvelope<Project>>('/projects', 'POST', body);
        set({ projects: [res.data, ...get().projects], isLoading: false });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create project', isLoading: false });
        throw e;
      }
    },

    updateProject: async (id, updates) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<Project>>(`/projects/${id}`, 'PATCH', updates);
        set({
          projects: get().projects.map((p) => (p.id === id ? res.data : p)),
          selectedProject: get().selectedProject?.id === id ? res.data : get().selectedProject,
          isLoading: false,
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update project', isLoading: false });
        throw e;
      }
    },

    fetchEpics: async (projectId) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiEnvelope<Epic[]>>(`/projects/${encodeURIComponent(projectId)}/epics`);
        set({ epics: res.data, isLoading: false });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load epics', isLoading: false });
      }
    },

    createEpic: async (projectId, subject, description) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<Epic>>('/epics', 'POST', {
          project_id: projectId,
          subject,
          description: description ?? null,
        });
        set({ epics: [...get().epics, res.data], isLoading: false });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create epic', isLoading: false });
        throw e;
      }
    },

    fetchSprints: async (projectId) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiEnvelope<Sprint[]>>(`/projects/${encodeURIComponent(projectId)}/sprints`);
        set({ sprints: res.data, isLoading: false });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load sprints', isLoading: false });
      }
    },

    createSprint: async (projectId, name, start_date, end_date) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<Sprint>>('/sprints', 'POST', {
          project_id: projectId,
          name,
          start_date,
          end_date,
        });
        set({ sprints: [...get().sprints, res.data], isLoading: false });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create sprint', isLoading: false });
        throw e;
      }
    },

    fetchStories: async (projectId) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiEnvelope<UserStory[]>>(`/projects/${encodeURIComponent(projectId)}/user-stories`);
        set({ stories: res.data, isLoading: false });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load stories', isLoading: false });
      }
    },

    createStory: async (payload) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<UserStory>>('/user-stories', 'POST', {
          ...payload,
          priority: payload.priority ?? 50,
        });
        set({ stories: [...get().stories, res.data], isLoading: false });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create story', isLoading: false });
        throw e;
      }
    },

    fetchSubtasks: async (storyId) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiEnvelope<Subtask[]>>(`/user-stories/${storyId}/subtasks`);
        set({
          subtasksByStoryId: { ...get().subtasksByStoryId, [storyId]: res.data },
          isLoading: false,
        });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load subtasks', isLoading: false });
      }
    },

    createSubtask: async (storyId, subject, description) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<Subtask>>('/subtasks', 'POST', {
          user_story_id: storyId,
          subject,
          description: description ?? null,
        });
        const existing = get().subtasksByStoryId[storyId] ?? [];
        set({
          subtasksByStoryId: { ...get().subtasksByStoryId, [storyId]: [...existing, res.data] },
          isLoading: false,
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create subtask', isLoading: false });
        throw e;
      }
    },

    updateSubtask: async (subtaskId, updates) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<Subtask>>(`/subtasks/${subtaskId}`, 'PATCH', updates);
        const subtasksByStoryId = { ...get().subtasksByStoryId };
        for (const [storyId, list] of Object.entries(subtasksByStoryId)) {
          const idx = list.findIndex((s) => s.id === subtaskId);
          if (idx >= 0) {
            const next = [...list];
            next[idx] = res.data;
            subtasksByStoryId[storyId] = next;
          }
        }
        set({ subtasksByStoryId, isLoading: false });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update subtask', isLoading: false });
        throw e;
      }
    },

    fetchStoryComments: async (storyId) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiGet<ApiEnvelope<StoryComment[]>>(`/user-stories/${storyId}/story-comments`);
        set({
          commentsByStoryId: { ...get().commentsByStoryId, [storyId]: res.data },
          isLoading: false,
        });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load comments', isLoading: false });
      }
    },

    createStoryComment: async (storyId, content) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<StoryComment>>('/story-comments', 'POST', {
          user_story_id: storyId,
          content,
        });
        const existing = get().commentsByStoryId[storyId] ?? [];
        set({
          commentsByStoryId: { ...get().commentsByStoryId, [storyId]: [...existing, res.data] },
          isLoading: false,
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create comment', isLoading: false });
        throw e;
      }
    },

    updateStoryStatus: async (storyId, status) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<UserStory>>(`/user-stories/${storyId}`, 'PATCH', { status });
        set({
          stories: get().stories.map((s) => (s.id === storyId ? res.data : s)),
          isLoading: false,
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update story status', isLoading: false });
        throw e;
      }
    },

    updateStory: async (storyId, updates) => {
      set({ isLoading: true, error: null });
      try {
        const res = await apiSend<ApiEnvelope<UserStory>>(`/user-stories/${storyId}`, 'PATCH', updates);
        set({
          stories: get().stories.map((s) => (s.id === storyId ? res.data : s)),
          isLoading: false,
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update story', isLoading: false });
        throw e;
      }
    },
  }))
);
