import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

export interface Skill {
  id: string;
  name: string;
  code: string;
  description?: string;
  skill_category: string;
  proficiency_levels: string[];
  minimum_required_level: number;
  is_safety_critical: boolean;
  is_quality_critical: boolean;
  requires_recertification: boolean;
  recertification_interval_days: number;
}

export interface Training {
  id: string;
  title: string;
  description?: string;
  training_type: string;
  skill_id?: string;
  instructor_id?: string;
  location?: string;
  start_date: string;
  end_date: string;
  status: string;
  capacity?: number;
  enrolled_count: number;
}

export interface TrainingRecord {
  id: string;
  user_id: string;
  user_name: string;
  training_id: string;
  training_title: string;
  status: string;
  enrolled_at: string;
  completed_at?: string;
  score?: number;
}

export interface UserSkill {
  id: string;
  user_id: string;
  skill_id: string;
  skill_name: string;
  proficiency_level: number;
  certified_at?: string;
  expires_at?: string;
  status: string;
}

interface TrainingState {
  skills: Skill[];
  trainings: Training[];
  records: TrainingRecord[];
  userSkills: UserSkill[];
  isLoading: boolean;
  error: string | null;

  fetchSkills: () => Promise<void>;
  fetchTrainings: () => Promise<void>;
  fetchRecords: () => Promise<void>;
  fetchUserSkills: (userId?: string) => Promise<void>;
  clearError: () => void;
}

export const useTrainingStore = create<TrainingState>()(
  devtools(
    persist(
      (set) => ({
        skills: [],
        trainings: [],
        records: [],
        userSkills: [],
        isLoading: false,
        error: null,

        fetchSkills: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/training/skills');
            set({ skills: data.items || [], isLoading: false });
          } catch (error: any) {
            set({ error: error.message || 'Failed to fetch skills', isLoading: false });
          }
        },

        fetchTrainings: async () => {
          set({ isLoading: true, error: null });
          try {
            const data = await apiClient.get<any>('/training/trainings');
            set({ trainings: data.items || [], isLoading: false });
          } catch (error: any) {
            set({ error: error.message || 'Failed to fetch trainings', isLoading: false });
          }
        },

        fetchRecords: async () => {
          set({ isLoading: true, error: null });
          try {
            // This might need a different endpoint or query params
            const data = await apiClient.get<any>('/training/trainings/participants');
            set({ records: data.items || [], isLoading: false });
          } catch (error: any) {
            set({ error: error.message || 'Failed to fetch records', isLoading: false });
          }
        },

        fetchUserSkills: async (userId) => {
          set({ isLoading: true, error: null });
          try {
            const url = userId ? `/training/user-skills?user_id=${userId}` : '/training/user-skills';
            const data = await apiClient.get<any>(url);
            set({ userSkills: data.items || [], isLoading: false });
          } catch (error: any) {
            set({ error: error.message || 'Failed to fetch user skills', isLoading: false });
          }
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'training-storage',
        partialize: (state) => ({
          skills: state.skills,
          trainings: state.trainings,
        }),
      }
    ),
    { name: 'TrainingStore' }
  )
);
