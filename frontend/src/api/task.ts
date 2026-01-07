import { apiClient, type PaginationParams } from './client';
import type {
  Task,
  TaskStatus,
  TaskType,
  Priority,
  KanbanBoard,
  KanbanColumn,
  ChecklistItem,
  PaginatedResponse,
} from '@/types';

// ============================================================================
// Task API
// ============================================================================

export interface TaskListParams extends PaginationParams {
  status?: TaskStatus | TaskStatus[];
  priority?: Priority | Priority[];
  type?: TaskType | TaskType[];
  assigned_to?: string;
  created_by?: string;
  due_date_from?: string;
  due_date_to?: string;
  search?: string;
  tags?: string[];
  linked_entity_type?: string;
  linked_entity_id?: string;
  parent_task_id?: string | null;
}

export interface CreateTaskData {
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: Priority;
  type?: TaskType;
  assigned_to?: string;
  due_date?: string;
  estimated_hours?: number;
  parent_task_id?: string;
  linked_entity_type?: string;
  linked_entity_id?: string;
  tags?: string[];
  checklist?: Array<{ text: string }>;
}

export interface UpdateTaskData {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: Priority;
  type?: TaskType;
  assigned_to?: string | null;
  due_date?: string | null;
  estimated_hours?: number | null;
  actual_hours?: number | null;
  tags?: string[];
}

export const taskApi = {
  /**
   * List tasks with pagination and filters
   */
  async list(params?: TaskListParams): Promise<PaginatedResponse<Task>> {
    return apiClient.get('/tasks', { params });
  },

  /**
   * Get a task by ID
   */
  async get(id: string): Promise<Task> {
    return apiClient.get(`/tasks/${id}`);
  },

  /**
   * Create a new task
   */
  async create(data: CreateTaskData): Promise<Task> {
    return apiClient.post('/tasks', data);
  },

  /**
   * Update a task
   */
  async update(id: string, data: UpdateTaskData): Promise<Task> {
    return apiClient.patch(`/tasks/${id}`, data);
  },

  /**
   * Delete a task
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/tasks/${id}`);
  },

  /**
   * Move task to a different status
   */
  async move(id: string, status: TaskStatus): Promise<Task> {
    return apiClient.post(`/tasks/${id}/move`, { status });
  },

  /**
   * Assign task to a user
   */
  async assign(id: string, userId: string): Promise<Task> {
    return apiClient.post(`/tasks/${id}/assign`, { user_id: userId });
  },

  /**
   * Unassign task
   */
  async unassign(id: string): Promise<Task> {
    return apiClient.post(`/tasks/${id}/unassign`);
  },

  /**
   * Duplicate a task
   */
  async duplicate(id: string): Promise<Task> {
    return apiClient.post(`/tasks/${id}/duplicate`);
  },

  /**
   * Get my tasks
   */
  async getMyTasks(params?: TaskListParams): Promise<PaginatedResponse<Task>> {
    return apiClient.get('/tasks/my', { params });
  },

  /**
   * Get tasks due today
   */
  async getDueToday(): Promise<Task[]> {
    return apiClient.get('/tasks/due-today');
  },

  /**
   * Get overdue tasks
   */
  async getOverdue(): Promise<Task[]> {
    return apiClient.get('/tasks/overdue');
  },

  /**
   * Bulk update tasks
   */
  async bulkUpdate(ids: string[], data: Partial<UpdateTaskData>): Promise<Task[]> {
    return apiClient.post('/tasks/bulk-update', { ids, data });
  },

  /**
   * Bulk delete tasks
   */
  async bulkDelete(ids: string[]): Promise<void> {
    return apiClient.post('/tasks/bulk-delete', { ids });
  },

  // Checklist
  checklist: {
    /**
     * Add a checklist item
     */
    async add(taskId: string, text: string): Promise<ChecklistItem> {
      return apiClient.post(`/tasks/${taskId}/checklist`, { text });
    },

    /**
     * Update a checklist item
     */
    async update(taskId: string, itemId: string, data: { text?: string; is_completed?: boolean }): Promise<ChecklistItem> {
      return apiClient.patch(`/tasks/${taskId}/checklist/${itemId}`, data);
    },

    /**
     * Delete a checklist item
     */
    async delete(taskId: string, itemId: string): Promise<void> {
      return apiClient.delete(`/tasks/${taskId}/checklist/${itemId}`);
    },

    /**
     * Toggle checklist item completion
     */
    async toggle(taskId: string, itemId: string): Promise<ChecklistItem> {
      return apiClient.post(`/tasks/${taskId}/checklist/${itemId}/toggle`);
    },

    /**
     * Reorder checklist items
     */
    async reorder(taskId: string, itemIds: string[]): Promise<ChecklistItem[]> {
      return apiClient.post(`/tasks/${taskId}/checklist/reorder`, { ids: itemIds });
    },
  },

  // Subtasks
  subtasks: {
    /**
     * List subtasks
     */
    async list(taskId: string): Promise<Task[]> {
      return apiClient.get(`/tasks/${taskId}/subtasks`);
    },

    /**
     * Create a subtask
     */
    async create(taskId: string, data: CreateTaskData): Promise<Task> {
      return apiClient.post(`/tasks/${taskId}/subtasks`, data);
    },
  },
};

// ============================================================================
// Kanban Board API
// ============================================================================

export interface KanbanBoardListParams extends PaginationParams {
  search?: string;
  is_active?: boolean;
}

export interface CreateKanbanBoardData {
  name: string;
  description?: string;
  columns?: Array<{
    name: string;
    task_status: TaskStatus;
    wip_limit?: number;
    color?: string;
  }>;
  members?: string[];
}

export interface UpdateKanbanBoardData {
  name?: string;
  description?: string;
  is_active?: boolean;
  members?: string[];
}

export interface UpdateKanbanColumnData {
  name?: string;
  wip_limit?: number;
  color?: string;
}

export const kanbanApi = {
  /**
   * List kanban boards
   */
  async list(params?: KanbanBoardListParams): Promise<PaginatedResponse<KanbanBoard>> {
    return apiClient.get('/kanban-boards', { params });
  },

  /**
   * Get a kanban board by ID
   */
  async get(id: string): Promise<KanbanBoard> {
    return apiClient.get(`/kanban-boards/${id}`);
  },

  /**
   * Create a new kanban board
   */
  async create(data: CreateKanbanBoardData): Promise<KanbanBoard> {
    return apiClient.post('/kanban-boards', data);
  },

  /**
   * Update a kanban board
   */
  async update(id: string, data: UpdateKanbanBoardData): Promise<KanbanBoard> {
    return apiClient.patch(`/kanban-boards/${id}`, data);
  },

  /**
   * Delete a kanban board
   */
  async delete(id: string): Promise<void> {
    return apiClient.delete(`/kanban-boards/${id}`);
  },

  /**
   * Get tasks for a board
   */
  async getTasks(id: string, params?: TaskListParams): Promise<Record<TaskStatus, Task[]>> {
    return apiClient.get(`/kanban-boards/${id}/tasks`, { params });
  },

  /**
   * Move a task on the board
   */
  async moveTask(boardId: string, taskId: string, status: TaskStatus, position?: number): Promise<Task> {
    return apiClient.post(`/kanban-boards/${boardId}/tasks/${taskId}/move`, { status, position });
  },

  /**
   * Add member to board
   */
  async addMember(id: string, userId: string): Promise<KanbanBoard> {
    return apiClient.post(`/kanban-boards/${id}/members`, { user_id: userId });
  },

  /**
   * Remove member from board
   */
  async removeMember(id: string, userId: string): Promise<KanbanBoard> {
    return apiClient.delete(`/kanban-boards/${id}/members/${userId}`);
  },

  // Columns
  columns: {
    /**
     * List columns for a board
     */
    async list(boardId: string): Promise<KanbanColumn[]> {
      return apiClient.get(`/kanban-boards/${boardId}/columns`);
    },

    /**
     * Update a column
     */
    async update(boardId: string, columnId: string, data: UpdateKanbanColumnData): Promise<KanbanColumn> {
      return apiClient.patch(`/kanban-boards/${boardId}/columns/${columnId}`, data);
    },

    /**
     * Reorder columns
     */
    async reorder(boardId: string, columnIds: string[]): Promise<KanbanColumn[]> {
      return apiClient.post(`/kanban-boards/${boardId}/columns/reorder`, { ids: columnIds });
    },
  },
};
