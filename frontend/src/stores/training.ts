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
  enrollInTraining: (trainingId: string | number, userId: string, notes?: string) => Promise<void>;
  registerCertification: (
    params: {
      userId: string;
      skillId: string | number;
      proficiency: number | string;
      issueDate?: string;
      expiryDate?: string;
      certificateNumber?: string;
      notes?: string;
    }
  ) => Promise<void>;
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

        enrollInTraining: async (trainingId, userId, notes) => {
          set({ isLoading: true, error: null });
          try {
            await apiClient.post<any>(`/training/trainings/${trainingId}/participants`, {
              user_id: userId,
              notes,
            });
            // Optional: caller can refresh trainings to update enrolled_count
            set({ isLoading: false });
          } catch (error: any) {
            set({ error: error.message || 'Failed to enroll in training', isLoading: false });
            throw error;
          }
        },

        registerCertification: async ({ userId, skillId, proficiency, issueDate, expiryDate, certificateNumber, notes }) => {
          set({ isLoading: true, error: null });
          try {
            // Step 1: find or create user-skill
            let userSkillId: number | undefined;
            try {
              const list = await apiClient.get<any>(`/training/user-skills?user_id=${userId}&skill_id=${skillId}`);
              const existing = list?.items?.[0];
              if (existing?.id) {
                userSkillId = existing.id as number;
              }
            } catch {
              // listing may fail due to filters; proceed to create
            }

            if (!userSkillId) {
              const created = await apiClient.post<any>('/training/user-skills', {
                user_id: userId,
                skill_id: Number(skillId),
                proficiency_level: Number(proficiency) || 0,
                notes,
              });
              // unwrapResponse returns inner data when using APIResponse
              userSkillId = created?.id ?? created?.data?.id;
            }

            if (!userSkillId) {
              throw new Error('Unable to resolve user skill record');
            }

            // Step 2: certify the user-skill
            await apiClient.post<any>(`/training/user-skills/${userSkillId}/certify`, {
              proficiency_level: Number(proficiency) || 0,
              expiration_date: expiryDate || undefined,
              certificate_number: certificateNumber || undefined,
              notes,
            });

            // Optional: caller can refresh user skills cache if needed
            set({ isLoading: false });
          } catch (error: any) {
            set({ error: error.message || 'Failed to register certification', isLoading: false });
            throw error;
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
