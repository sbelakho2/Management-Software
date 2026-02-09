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
  color: string;
  use_story_points: boolean;
  use_time_tracking: boolean;
  enable_wiki: boolean;
  enable_issues: boolean;
  enable_sprints: boolean;
  custom_user_story_statuses?: { id: string; name: string; color?: string; is_closed?: boolean }[] | null;
  custom_task_statuses?: { id: string; name: string; color?: string; is_closed?: boolean }[] | null;
  custom_issue_statuses?: { id: string; name: string; color?: string; is_closed?: boolean }[] | null;
  total_user_stories: number;
  completed_user_stories: number;
  total_story_points: number;
  completed_story_points: number;
  total_issues: number;
  open_issues: number;
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
  related_work_order_id?: number | null;
  related_ctq_id?: string | null;
  estimated_hours?: number | null;
  actual_hours: number;
  created_at: string;
  updated_at: string;
}

export interface Subtask {
  id: string;
  user_story_id: string;
  ref: number;
  subject: string;
  description?: string | null;
  status: string;
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

export type IssueType = 'bug' | 'improvement' | 'task' | 'question' | 'incident' | 'ncr' | 'safety';
export type IssueSeverity = 'wishlist' | 'minor' | 'normal' | 'important' | 'critical';
export type IssueStatus = 'new' | 'in_progress' | 'ready_for_test' | 'closed' | 'rejected' | 'postponed';
export type IssuePriority = 'low' | 'normal' | 'high' | 'urgent';

export interface Issue {
  id: string;
  project_id: string;
  ref: number;
  subject: string;
  description?: string | null;
  issue_type: IssueType;
  severity: IssueSeverity;
  status: IssueStatus;
  priority: IssuePriority;
  owner_id?: string | null;
  assigned_to_id?: string | null;
  due_date?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IssueComment {
  id: string;
  issue_id: string;
  author_id?: string | null;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface WikiPage {
  id: string;
  project_id: string;
  title: string;
  slug: string;
  content: string;
  page_type: string;
  parent_id?: string | null;
  order: number;
  owner_id?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectMilestone {
  id: string;
  project_id: string;
  name: string;
  slug: string;
  description?: string | null;
  milestone_type: string;
  due_date: string;
  is_closed: boolean;
  closed_at?: string | null;
  order: number;
  total_items: number;
  closed_items: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectActivity {
  id: string;
  project_id: string;
  user_id?: string | null;
  activity_type: string;
  entity_type: string;
  entity_id: string;
  entity_ref?: number | null;
  summary: string;
  details?: Record<string, any> | null;
  created_at: string;
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
  issues: Issue[];
  wikiPages: WikiPage[];
  milestones: ProjectMilestone[];
  activities: ProjectActivity[];
  myWork: { stories: UserStory[]; issues: Issue[] };
  subtasksByStoryId: Record<string, Subtask[]>;
  commentsByStoryId: Record<string, StoryComment[]>;
  commentsByIssueId: Record<string, IssueComment[]>;

  /** @deprecated Use loadingOps for per-operation states */
  isLoading: boolean;
  /** Set of currently in-progress operation names */
  loadingOps: Set<string>;
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
  createStory: (payload: { project_id: string; subject: string; priority?: number; epic_id?: string | null; sprint_id?: string | null; description?: string; story_points?: number }) => Promise<UserStory>;

  fetchIssues: (projectId: string) => Promise<void>;
  createIssue: (payload: Partial<Issue> & { project_id: string; subject: string; issue_type: IssueType }) => Promise<Issue>;
  updateIssue: (issueId: string, updates: Partial<Issue>) => Promise<Issue>;
  fetchIssueComments: (issueId: string) => Promise<void>;
  createIssueComment: (issueId: string, content: string) => Promise<IssueComment>;

  fetchWikiPages: (projectId: string) => Promise<void>;
  createWikiPage: (payload: { project_id: string; title: string; content: string; parent_id?: string | null }) => Promise<WikiPage>;
  updateWikiPage: (pageId: string, updates: Partial<WikiPage>) => Promise<WikiPage>;

  fetchMilestones: (projectId: string) => Promise<void>;
  createMilestone: (payload: Partial<ProjectMilestone> & { project_id: string; name: string; due_date: string }) => Promise<ProjectMilestone>;
  updateMilestone: (milestoneId: string, updates: Partial<ProjectMilestone>) => Promise<ProjectMilestone>;
  deleteMilestone: (milestoneId: string) => Promise<void>;

  fetchActivities: (projectId: string) => Promise<void>;

  fetchMyWork: () => Promise<void>;

  fetchSubtasks: (storyId: string) => Promise<void>;
  createSubtask: (storyId: string, subject: string, description?: string, status?: string) => Promise<Subtask>;
  updateSubtask: (subtaskId: string, updates: Partial<Subtask>) => Promise<Subtask>;

  fetchStoryComments: (storyId: string) => Promise<void>;
  createStoryComment: (storyId: string, content: string) => Promise<StoryComment>;

  updateStoryStatus: (storyId: string, status: UserStoryStatus) => Promise<UserStory>;
  updateStory: (storyId: string, updates: Partial<UserStory>) => Promise<UserStory>;

  clearError: () => void;
  /** Check if a specific operation is in progress */
  isOpLoading: (op: string) => boolean;
}


/* ── Per-operation loading helpers ─────────────────────────────────── */
function startOp(set: (fn: (s: ProjectManagementState) => Partial<ProjectManagementState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.add(op);
    return { loadingOps: next, isLoading: true, error: null };
  });
}
function endOp(set: (fn: (s: ProjectManagementState) => Partial<ProjectManagementState>) => void, op: string) {
  set((s) => {
    const next = new Set(s.loadingOps);
    next.delete(op);
    return { loadingOps: next, isLoading: next.size > 0 };
  });
}

export const useProjectManagementStore = create<ProjectManagementState>()(
  devtools((set, get) => ({
    projects: [],
    selectedProject: null,
    epics: [],
    sprints: [],
    stories: [],
    issues: [],
    wikiPages: [],
    milestones: [],
    activities: [],
    myWork: { stories: [], issues: [] },
    subtasksByStoryId: {},
    commentsByStoryId: {},
    commentsByIssueId: {},
    isLoading: false,
  loadingOps: new Set<string>(),
    error: null,

    clearError: () => set({ error: null }),

    fetchProjects: async () => {
      startOp(set, 'fetchProjects');
      try {
        const res = await apiGet<ApiPaginated<Project[]>>('/projects?page=1&page_size=50');
        set({ projects: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load projects' });
      }
        finally {
          endOp(set, 'fetchProjects');
        }
    },

    fetchProjectById: async (id: string) => {
      startOp(set, 'fetchProjectById');
      try {
        const res = await apiGet<ApiEnvelope<Project>>(`/projects/${id}`);
        set({ selectedProject: res.data });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load project' });
        return null;
      }
      finally {
        endOp(set, 'fetchProjectById');
      }
    },

    createProject: async (payload) => {
      startOp(set, 'createProject');
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
        set({ projects: [res.data, ...get().projects] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create project' });
        throw e;
      }
        finally {
          endOp(set, 'createProject');
        }
    },

    updateProject: async (id, updates) => {
      startOp(set, 'updateProject');
      try {
        const res = await apiSend<ApiEnvelope<Project>>(`/projects/${id}`, 'PATCH', updates);
        set({
          projects: get().projects.map((p) => (p.id === id ? res.data : p)),
          selectedProject: get().selectedProject?.id === id ? res.data : get().selectedProject,
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update project' });
        throw e;
      }
        finally {
          endOp(set, 'updateProject');
        }
    },

    fetchEpics: async (projectId) => {
      startOp(set, 'fetchEpics');
      try {
        const res = await apiGet<ApiEnvelope<Epic[]>>(`/projects/${encodeURIComponent(projectId)}/epics`);
        set({ epics: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load epics' });
      }
        finally {
          endOp(set, 'fetchEpics');
        }
    },

    createEpic: async (projectId, subject, description) => {
      startOp(set, 'createEpic');
      try {
        const res = await apiSend<ApiEnvelope<Epic>>('/epics', 'POST', {
          project_id: projectId,
          subject,
          description: description ?? null,
        });
        set({ epics: [...get().epics, res.data] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create epic' });
        throw e;
      }
        finally {
          endOp(set, 'createEpic');
        }
    },

    fetchSprints: async (projectId) => {
      startOp(set, 'fetchSprints');
      try {
        const res = await apiGet<ApiEnvelope<Sprint[]>>(`/projects/${encodeURIComponent(projectId)}/sprints`);
        set({ sprints: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load sprints' });
      }
        finally {
          endOp(set, 'fetchSprints');
        }
    },

    createSprint: async (projectId, name, start_date, end_date) => {
      startOp(set, 'createSprint');
      try {
        const res = await apiSend<ApiEnvelope<Sprint>>('/sprints', 'POST', {
          project_id: projectId,
          name,
          start_date,
          end_date,
        });
        set({ sprints: [...get().sprints, res.data] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create sprint' });
        throw e;
      }
        finally {
          endOp(set, 'createSprint');
        }
    },

    fetchStories: async (projectId) => {
      startOp(set, 'fetchStories');
      try {
        const res = await apiGet<ApiEnvelope<UserStory[]>>(`/projects/${encodeURIComponent(projectId)}/user-stories`);
        set({ stories: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load stories' });
      }
        finally {
          endOp(set, 'fetchStories');
        }
    },

    createStory: async (payload) => {
      startOp(set, 'createStory');
      try {
        const res = await apiSend<ApiEnvelope<UserStory>>('/user-stories', 'POST', {
          ...payload,
          priority: payload.priority ?? 50,
        });
        set({ stories: [...get().stories, res.data] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create story' });
        throw e;
      }
        finally {
          endOp(set, 'createStory');
        }
    },
    
    fetchIssues: async (projectId) => {
      startOp(set, 'fetchIssues');
      try {
        const res = await apiGet<ApiEnvelope<Issue[]>>(`/projects/${encodeURIComponent(projectId)}/issues`);
        set({ issues: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load issues' });
      }
        finally {
          endOp(set, 'fetchIssues');
        }
    },

    createIssue: async (payload) => {
      startOp(set, 'createIssue');
      try {
        const res = await apiSend<ApiEnvelope<Issue>>('/issues', 'POST', payload);
        set({ issues: [...get().issues, res.data] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create issue' });
        throw e;
      }
        finally {
          endOp(set, 'createIssue');
        }
    },

    updateIssue: async (issueId, updates) => {
      startOp(set, 'updateIssue');
      try {
        const res = await apiSend<ApiEnvelope<Issue>>(`/issues/${issueId}`, 'PATCH', updates);
        set({
          issues: get().issues.map((i) => (i.id === issueId ? res.data : i)),
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update issue' });
        throw e;
      }
        finally {
          endOp(set, 'updateIssue');
        }
    },

    fetchIssueComments: async (issueId) => {
      startOp(set, 'fetchIssueComments');
      try {
        const res = await apiGet<ApiEnvelope<IssueComment[]>>(`/issues/${issueId}/comments`);
        set({
          commentsByIssueId: { ...get().commentsByIssueId, [issueId]: res.data },
        });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load issue comments' });
      }
        finally {
          endOp(set, 'fetchIssueComments');
        }
    },

    createIssueComment: async (issueId, content) => {
      startOp(set, 'createIssueComment');
      try {
        const res = await apiSend<ApiEnvelope<IssueComment>>(`/issues/${issueId}/comments`, 'POST', {
          content,
        });
        const existing = get().commentsByIssueId[issueId] ?? [];
        set({
          commentsByIssueId: { ...get().commentsByIssueId, [issueId]: [...existing, res.data] },
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create issue comment' });
        throw e;
      }
        finally {
          endOp(set, 'createIssueComment');
        }
    },

    fetchWikiPages: async (projectId) => {
      startOp(set, 'fetchWikiPages');
      try {
        const res = await apiGet<ApiEnvelope<WikiPage[]>>(`/projects/${encodeURIComponent(projectId)}/wiki-pages`);
        set({ wikiPages: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load wiki pages' });
      }
        finally {
          endOp(set, 'fetchWikiPages');
        }
    },

    createWikiPage: async (payload) => {
      startOp(set, 'createWikiPage');
      try {
        const res = await apiSend<ApiEnvelope<WikiPage>>('/wiki-pages', 'POST', payload);
        set({ wikiPages: [...get().wikiPages, res.data] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create wiki page' });
        throw e;
      }
        finally {
          endOp(set, 'createWikiPage');
        }
    },

    updateWikiPage: async (pageId, updates) => {
      startOp(set, 'updateWikiPage');
      try {
        const res = await apiSend<ApiEnvelope<WikiPage>>(`/wiki-pages/${pageId}`, 'PATCH', updates);
        set({
          wikiPages: get().wikiPages.map((p) => (p.id === pageId ? res.data : p)),
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update wiki page' });
        throw e;
      }
        finally {
          endOp(set, 'updateWikiPage');
        }
    },

    fetchMilestones: async (projectId) => {
      startOp(set, 'fetchMilestones');
      try {
        const res = await apiGet<ApiEnvelope<ProjectMilestone[]>>(`/projects/${encodeURIComponent(projectId)}/milestones`);
        set({ milestones: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load milestones' });
      }
        finally {
          endOp(set, 'fetchMilestones');
        }
    },

    createMilestone: async (payload) => {
      startOp(set, 'createMilestone');
      try {
        const res = await apiSend<ApiEnvelope<ProjectMilestone>>('/milestones', 'POST', payload);
        set({ milestones: [...get().milestones, res.data] });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create milestone' });
        throw e;
      }
        finally {
          endOp(set, 'createMilestone');
        }
    },

    updateMilestone: async (milestoneId, updates) => {
      startOp(set, 'updateMilestone');
      try {
        const res = await apiSend<ApiEnvelope<ProjectMilestone>>(`/milestones/${milestoneId}`, 'PATCH', updates);
        set({
          milestones: get().milestones.map((m) => (m.id === milestoneId ? res.data : m)),
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update milestone' });
        throw e;
      }
        finally {
          endOp(set, 'updateMilestone');
        }
    },

    deleteMilestone: async (milestoneId) => {
      startOp(set, 'deleteMilestone');
      try {
        await apiSend(`/milestones/${milestoneId}`, 'DELETE');
        set({
          milestones: get().milestones.filter((m) => m.id !== milestoneId),
        });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to delete milestone' });
        throw e;
      }
        finally {
          endOp(set, 'deleteMilestone');
        }
    },

    fetchActivities: async (projectId) => {
      startOp(set, 'fetchActivities');
      try {
        const res = await apiClient.get<ApiPaginated<ProjectActivity[]>>(`/project-management/projects/${encodeURIComponent(projectId)}/activities`);
        set({ activities: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load activities' });
      }
        finally {
          endOp(set, 'fetchActivities');
        }
    },

    fetchMyWork: async () => {
      startOp(set, 'fetchMyWork');
      try {
        const res = await apiGet<ApiEnvelope<{ stories: UserStory[]; issues: Issue[] }>>('/my-work');
        set({ myWork: res.data });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load my work' });
      }
        finally {
          endOp(set, 'fetchMyWork');
        }
    },

    fetchSubtasks: async (storyId) => {
      startOp(set, 'fetchSubtasks');
      try {
        const res = await apiGet<ApiEnvelope<Subtask[]>>(`/user-stories/${storyId}/subtasks`);
        set({
          subtasksByStoryId: { ...get().subtasksByStoryId, [storyId]: res.data },
        });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load subtasks' });
      }
        finally {
          endOp(set, 'fetchSubtasks');
        }
    },

    createSubtask: async (storyId, subject, description, status) => {
      startOp(set, 'createSubtask');
      try {
        const res = await apiSend<ApiEnvelope<Subtask>>('/subtasks', 'POST', {
          user_story_id: storyId,
          subject,
          description: description ?? null,
          status: status ?? 'open',
        });
        const existing = get().subtasksByStoryId[storyId] ?? [];
        set({
          subtasksByStoryId: { ...get().subtasksByStoryId, [storyId]: [...existing, res.data] },
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create subtask' });
        throw e;
      }
        finally {
          endOp(set, 'createSubtask');
        }
    },

    updateSubtask: async (subtaskId, updates) => {
      startOp(set, 'updateSubtask');
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
        set({ subtasksByStoryId });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update subtask' });
        throw e;
      }
        finally {
          endOp(set, 'updateSubtask');
        }
    },

    fetchStoryComments: async (storyId) => {
      startOp(set, 'fetchStoryComments');
      try {
        const res = await apiGet<ApiEnvelope<StoryComment[]>>(`/user-stories/${storyId}/story-comments`);
        set({
          commentsByStoryId: { ...get().commentsByStoryId, [storyId]: res.data },
        });
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to load comments' });
      }
        finally {
          endOp(set, 'fetchStoryComments');
        }
    },

    createStoryComment: async (storyId, content) => {
      startOp(set, 'createStoryComment');
      try {
        const res = await apiSend<ApiEnvelope<StoryComment>>('/story-comments', 'POST', {
          user_story_id: storyId,
          content,
        });
        const existing = get().commentsByStoryId[storyId] ?? [];
        set({
          commentsByStoryId: { ...get().commentsByStoryId, [storyId]: [...existing, res.data] },
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to create comment' });
        throw e;
      }
        finally {
          endOp(set, 'createStoryComment');
        }
    },

    updateStoryStatus: async (storyId, status) => {
      const originalStories = get().stories;
      
      // Optimistic update
      set({
        stories: originalStories.map((s) => (s.id === storyId ? { ...s, status } : s)),
      });

      try {
        startOp(set, 'updateStoryStatus');
        const res = await apiSend<ApiEnvelope<UserStory>>(`/user-stories/${storyId}`, 'PATCH', { status });
        set({
          stories: get().stories.map((s) => (s.id === storyId ? res.data : s)),
        });
        return res.data;
      } catch (e) {
        // Rollback
        set({
          stories: originalStories,
          error: e instanceof Error ? e.message : 'Failed to update story status',
        });
        throw e;
      }
        finally {
          endOp(set, 'updateStoryStatus');
        }
    },

    updateStory: async (storyId, updates) => {
      startOp(set, 'updateStory');
      try {
        const res = await apiSend<ApiEnvelope<UserStory>>(`/user-stories/${storyId}`, 'PATCH', updates);
        set({
          stories: get().stories.map((s) => (s.id === storyId ? res.data : s)),
        });
        return res.data;
      } catch (e) {
        set({ error: e instanceof Error ? e.message : 'Failed to update story' });
        throw e;
      }
        finally {
          endOp(set, 'updateStory');
        }
    },

    isOpLoading: (op: string) => get().loadingOps.has(op),
  }))
);
