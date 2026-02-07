/**
 * AI Email Drafting Store
 *
 * Manages state for AI-powered email draft generation including:
 * - Draft generation and management
 * - Recipient handling
 * - Template management
 * - Compliance checking
 * - Draft history
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/api/client';

// ============================================================================
// Types & Enums
// ============================================================================

export type EmailTone =
  | 'formal'
  | 'professional'
  | 'friendly'
  | 'urgent'
  | 'apologetic'
  | 'appreciative'
  | 'concise';

export type EmailPurpose =
  | 'missing_info_request'
  | 'quote_followup'
  | 'quote_submission'
  | 'supplier_inquiry'
  | 'meeting_request'
  | 'meeting_confirmation'
  | 'meeting_reschedule'
  | 'issue_notification'
  | 'status_update'
  | 'thank_you'
  | 'introduction'
  | 'escalation'
  | 'apology'
  | 'custom';

export type DraftStatus =
  | 'generating'
  | 'ready'
  | 'reviewed'
  | 'approved'
  | 'sent'
  | 'discarded'
  | 'failed';

export type Language =
  | 'en'
  | 'fr'
  | 'de'
  | 'es'
  | 'it'
  | 'pt'
  | 'ja'
  | 'zh'
  | 'ko'
  | 'ar';

export type ComplianceCheckType =
  | 'pii_check'
  | 'confidentiality'
  | 'profanity'
  | 'legal_terms'
  | 'tone_appropriate'
  | 'completeness';

export type SuggestionType =
  | 'grammar'
  | 'clarity'
  | 'tone'
  | 'structure'
  | 'brevity'
  | 'call_to_action';

export interface Recipient {
  id: string;
  email: string;
  name?: string;
  title?: string;
  company?: string;
  relationship?: string;
  languagePreference: Language;
  previousInteractions: number;
}

export interface EmailContext {
  purpose: EmailPurpose;
  recipient: Recipient;
  subjectHint?: string;
  keyPoints: string[];
  attachments: string[];
  referenceNumber?: string;
  deadline?: Date;
  tone: EmailTone;
  language: Language;
  includeSignature: boolean;
  maxParagraphs: number;
  threadEntityType?: string;
  threadEntityId?: string;
}

export interface ThreadContext {
  entityType?: string;
  entityId?: string;
  reasoningId?: string;
}

export interface GenerationRequest {
  id: string;
  context: EmailContext;
  senderName: string;
  senderTitle?: string;
  senderEmail: string;
  companyName: string;
  language?: string;
  requestedBy?: string;
  requestedAt: Date;
  threadContext?: ThreadContext;
}

export interface GeneratedDraft {
  id: string;
  requestId: string;
  subject: string;
  bodyPlain: string;
  bodyHtml: string;
  salutation: string;
  body?: string;
  opening: string;
  mainContent: string[];
  closing: string;
  signature: string;
  fullText?: string;
  status: DraftStatus;
  confidenceScore: number;
  alternatives: string[];
  complianceIssues: string[];
  suggestions: string[];
  tokensUsed: number;
  generationTimeMs: number;
  context?: EmailContext;
  tone?: string;
  language?: string;
  modelVersion?: string;
  reasoningId?: string;
  generatedAt?: Date;
  createdAt: Date;
  reviewedAt?: Date;
  reviewedBy?: string;
  editsMade: string[];
}

export interface ComplianceCheck {
  checkType: ComplianceCheckType;
  passed: boolean;
  severity: 'info' | 'warning' | 'error';
  message: string;
  location?: string;
  suggestion?: string;
}

export interface ImprovementSuggestion {
  type: SuggestionType;
  originalText: string;
  suggestedText: string;
  reason: string;
  priority: 'low' | 'medium' | 'high';
  autoApplicable: boolean;
}

export interface EmailTemplate {
  id: string;
  name: string;
  purpose: EmailPurpose;
  language: Language;
  subjectTemplate: string;
  bodyTemplate: string;
  tone: EmailTone;
  placeholders: string[];
  isDefault: boolean;
  isActive: boolean;
  usageCount: number;
  successRate: number;
}

export interface DraftHistoryEntry {
  draftId: string;
  action: 'generated' | 'edited' | 'regenerated' | 'approved' | 'sent' | 'discarded';
  actorId?: string;
  timestamp: Date;
  details?: string;
  beforeText?: string;
  afterText?: string;
}

export interface RecentRecipient {
  recipient: Recipient;
  lastUsed: Date;
  usageCount: number;
}

// ============================================================================
// Store State & Actions
// ============================================================================

interface EmailDraftingState {
  // Drafts
  drafts: Map<string, GeneratedDraft>;
  activeDraftId: string | null;
  isGenerating: boolean;
  generationError: string | null;

  // Recipients
  recentRecipients: RecentRecipient[];

  // Templates
  templates: Map<string, EmailTemplate>;

  // History
  history: DraftHistoryEntry[];

  // UI State
  showComposeModal: boolean;
  showTemplateSelector: boolean;
  selectedPurpose: EmailPurpose | null;
  selectedTone: EmailTone;
  selectedLanguage: Language;

  // Editor state
  isEditing: boolean;
  editField: 'subject' | 'body' | 'salutation' | 'closing' | null;

  // Actions
  generateDraft: (request: GenerationRequest) => Promise<GeneratedDraft>;
  getDraft: (id: string) => GeneratedDraft | undefined;
  updateDraft: (id: string, updates: Partial<GeneratedDraft>) => void;
  approveDraft: (id: string, reviewerId: string) => void;
  markSent: (id: string) => void;
  discardDraft: (id: string, reason?: string) => void;
  regenerateDraft: (id: string, feedback?: string) => Promise<GeneratedDraft>;
  setActiveDraft: (id: string | null) => void;

  // Recipient management
  addRecentRecipient: (recipient: Recipient) => void;
  removeRecentRecipient: (email: string) => void;
  clearRecentRecipients: () => void;

  // Template management
  addTemplate: (template: EmailTemplate) => void;
  updateTemplate: (id: string, updates: Partial<EmailTemplate>) => void;
  deleteTemplate: (id: string) => void;
  getTemplatesByPurpose: (purpose: EmailPurpose) => EmailTemplate[];

  // History
  getHistoryForDraft: (draftId: string) => DraftHistoryEntry[];
  clearHistory: () => void;

  // UI Actions
  setShowComposeModal: (show: boolean) => void;
  setShowTemplateSelector: (show: boolean) => void;
  setSelectedPurpose: (purpose: EmailPurpose | null) => void;
  setSelectedTone: (tone: EmailTone) => void;
  setSelectedLanguage: (language: Language) => void;
  setIsEditing: (editing: boolean) => void;
  setEditField: (field: 'subject' | 'body' | 'salutation' | 'closing' | null) => void;

  // Reset
  reset: () => void;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState = {
  drafts: new Map<string, GeneratedDraft>(),
  activeDraftId: null,
  isGenerating: false,
  generationError: null,
  recentRecipients: [] as RecentRecipient[],
  templates: new Map<string, EmailTemplate>(),
  history: [] as DraftHistoryEntry[],
  showComposeModal: false,
  showTemplateSelector: false,
  selectedPurpose: null as EmailPurpose | null,
  selectedTone: 'professional' as EmailTone,
  selectedLanguage: 'en' as Language,
  isEditing: false,
  editField: null as 'subject' | 'body' | 'salutation' | 'closing' | null,
};

// ============================================================================
// Helper Functions
// ============================================================================

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function getPurposeLabel(purpose: EmailPurpose): string {
  const labels: Record<EmailPurpose, string> = {
    missing_info_request: 'Missing Information Request',
    quote_followup: 'Quote Follow-up',
    quote_submission: 'Quote Submission',
    supplier_inquiry: 'Supplier Inquiry',
    meeting_request: 'Meeting Request',
    meeting_confirmation: 'Meeting Confirmation',
    meeting_reschedule: 'Meeting Reschedule',
    issue_notification: 'Issue Notification',
    status_update: 'Status Update',
    thank_you: 'Thank You',
    introduction: 'Introduction',
    escalation: 'Escalation',
    apology: 'Apology',
    custom: 'Custom Email',
  };
  return labels[purpose] || purpose;
}

export function getPurposeLabelKey(purpose: EmailPurpose): string {
  const keys: Record<EmailPurpose, string> = {
    missing_info_request: 'emailDrafting.purpose.missingInfoRequest',
    quote_followup: 'emailDrafting.purpose.quoteFollowup',
    quote_submission: 'emailDrafting.purpose.quoteSubmission',
    supplier_inquiry: 'emailDrafting.purpose.supplierInquiry',
    meeting_request: 'emailDrafting.purpose.meetingRequest',
    meeting_confirmation: 'emailDrafting.purpose.meetingConfirmation',
    meeting_reschedule: 'emailDrafting.purpose.meetingReschedule',
    issue_notification: 'emailDrafting.purpose.issueNotification',
    status_update: 'emailDrafting.purpose.statusUpdate',
    thank_you: 'emailDrafting.purpose.thankYou',
    introduction: 'emailDrafting.purpose.introduction',
    escalation: 'emailDrafting.purpose.escalation',
    apology: 'emailDrafting.purpose.apology',
    custom: 'emailDrafting.purpose.custom',
  };
  return keys[purpose] || 'emailDrafting.purpose.custom';
}

export function getToneLabel(tone: EmailTone): string {
  const labels: Record<EmailTone, string> = {
    formal: 'Formal',
    professional: 'Professional',
    friendly: 'Friendly',
    urgent: 'Urgent',
    apologetic: 'Apologetic',
    appreciative: 'Appreciative',
    concise: 'Concise',
  };
  return labels[tone] || tone;
}

export function getToneLabelKey(tone: EmailTone): string {
  const keys: Record<EmailTone, string> = {
    formal: 'emailDrafting.tone.formal',
    professional: 'emailDrafting.tone.professional',
    friendly: 'emailDrafting.tone.friendly',
    urgent: 'emailDrafting.tone.urgent',
    apologetic: 'emailDrafting.tone.apologetic',
    appreciative: 'emailDrafting.tone.appreciative',
    concise: 'emailDrafting.tone.concise',
  };
  return keys[tone] || 'emailDrafting.tone.professional';
}

export function getLanguageLabel(language: Language): string {
  const labels: Record<Language, string> = {
    en: 'English',
    fr: 'French',
    de: 'German',
    es: 'Spanish',
    it: 'Italian',
    pt: 'Portuguese',
    ja: 'Japanese',
    zh: 'Chinese',
    ko: 'Korean',
    ar: 'Arabic',
  };
  return labels[language] || language;
}

export function getLanguageLabelKey(language: Language): string {
  const keys: Record<Language, string> = {
    en: 'emailDrafting.language.english',
    fr: 'emailDrafting.language.french',
    de: 'emailDrafting.language.german',
    es: 'emailDrafting.language.spanish',
    it: 'emailDrafting.language.italian',
    pt: 'emailDrafting.language.portuguese',
    ja: 'emailDrafting.language.japanese',
    zh: 'emailDrafting.language.chinese',
    ko: 'emailDrafting.language.korean',
    ar: 'emailDrafting.language.arabic',
  };
  return keys[language] || 'emailDrafting.language.english';
}

export function getStatusLabel(status: DraftStatus): string {
  const labels: Record<DraftStatus, string> = {
    generating: 'Generating...',
    ready: 'Ready for Review',
    reviewed: 'Reviewed',
    approved: 'Approved',
    sent: 'Sent',
    discarded: 'Discarded',
    failed: 'Failed',
  };
  return labels[status] || status;
}

export function getStatusLabelKey(status: DraftStatus): string {
  const keys: Record<DraftStatus, string> = {
    generating: 'emailDrafting.status.generating',
    ready: 'emailDrafting.status.ready',
    reviewed: 'emailDrafting.status.reviewed',
    approved: 'emailDrafting.status.approved',
    sent: 'emailDrafting.status.sent',
    discarded: 'emailDrafting.status.discarded',
    failed: 'emailDrafting.status.failed',
  };
  return keys[status] || 'emailDrafting.status.ready';
}

export function getStatusColor(status: DraftStatus): string {
  const colors: Record<DraftStatus, string> = {
    generating: '#f59e0b', // amber
    ready: '#3b82f6', // blue
    reviewed: '#8b5cf6', // purple
    approved: '#22c55e', // green
    sent: '#10b981', // emerald
    discarded: '#6b7280', // gray
    failed: '#ef4444', // red
  };
  return colors[status] || '#6b7280';
}

export function getStatusColorClass(status: DraftStatus): string {
  const classes: Record<DraftStatus, string> = {
    generating: 'text-rams-orange',
    ready: 'text-rams-steel',
    reviewed: 'text-rams-steel',
    approved: 'text-rams-green',
    sent: 'text-rams-green',
    discarded: 'text-rams-muted',
    failed: 'text-rams-red',
  };
  return classes[status] || 'text-rams-muted';
}

export function getComplianceSeverityColor(severity: 'info' | 'warning' | 'error'): string {
  const colors: Record<string, string> = {
    info: '#3b82f6',
    warning: '#f59e0b',
    error: '#ef4444',
  };
  return colors[severity] || '#6b7280';
}

export function getSuggestionPriorityColor(priority: 'low' | 'medium' | 'high'): string {
  const colors: Record<string, string> = {
    low: '#6b7280',
    medium: '#f59e0b',
    high: '#ef4444',
  };
  return colors[priority] || '#6b7280';
}

export function formatConfidenceScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

export function getConfidenceColor(score: number): string {
  if (score >= 0.8) return '#22c55e'; // green
  if (score >= 0.6) return '#f59e0b'; // amber
  return '#ef4444'; // red
}

export function getConfidenceColorClass(score: number): string {
  if (score >= 0.8) return 'text-rams-green';
  if (score >= 0.6) return 'text-rams-orange';
  return 'text-rams-red';
}

export function formatGenerationTime(
  ms: number,
  units?: { milliseconds: string; seconds: string }
): string {
  const unitMs = units?.milliseconds ?? 'ms';
  const unitS = units?.seconds ?? 's';
  if (ms < 1000) return `${ms}${unitMs}`;
  return `${(ms / 1000).toFixed(1)}${unitS}`;
}

export function createDefaultContext(recipient: Recipient): EmailContext {
  return {
    purpose: 'custom',
    recipient,
    keyPoints: [],
    attachments: [],
    tone: 'professional',
    language: recipient.languagePreference || 'en',
    includeSignature: true,
    maxParagraphs: 4,
  };
}

export function validateRecipient(recipient: Partial<Recipient>): string[] {
  const errors: string[] = [];
  if (!recipient.email) {
    errors.push('emailDrafting.validation.emailRequired');
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipient.email)) {
    errors.push('emailDrafting.validation.emailInvalid');
  }
  return errors;
}

export function createRecipient(email: string, name?: string): Recipient {
  return {
    id: generateId(),
    email,
    name,
    languagePreference: 'en',
    previousInteractions: 0,
  };
}

// ============================================================================
// Store Implementation
// ============================================================================

export const useEmailDraftingStore = create<EmailDraftingState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Draft generation - calls backend AI service
      generateDraft: async (request: GenerationRequest): Promise<GeneratedDraft> => {
        set({ isGenerating: true, generationError: null });

        try {
          // Call backend AI email drafting service
          const apiDraft = await apiClient.post<any>('/ai/email/generate', {
            recipient: {
              email: request.context.recipient.email,
              name: request.context.recipient.name,
              title: request.context.recipient.title,
              company: request.context.recipient.company,
            },
            purpose: request.context.purpose,
            tone: request.context.tone,
            key_points: request.context.keyPoints,
            reference_number: request.context.referenceNumber,
            deadline: request.context.deadline?.toISOString(),
            attachments: request.context.attachments,
            sender_name: request.senderName,
            sender_title: request.senderTitle,
            sender_email: request.senderEmail,
            company_name: request.companyName,
            language: request.language,
            thread_entity_type: request.threadContext?.entityType,
            thread_entity_id: request.threadContext?.entityId,
            thread_reasoning_id: request.threadContext?.reasoningId,
          });
          
          // Map API response to frontend draft format
          const draft: GeneratedDraft = {
            id: apiDraft.id || generateId(),
            requestId: request.id,
            status: 'ready',
            context: request.context,
            subject: apiDraft.subject,
            salutation: apiDraft.salutation,
            body: apiDraft.body,
            bodyPlain: apiDraft.body || '',
            bodyHtml: `<p>${apiDraft.salutation}</p><p>${apiDraft.body}</p><p>${apiDraft.closing}</p>`,
            opening: apiDraft.opening || '',
            mainContent: apiDraft.main_content || [],
            closing: apiDraft.closing,
            signature: apiDraft.signature || `${request.senderName}\n${request.senderTitle}\n${request.companyName}`,
            fullText: `${apiDraft.salutation}\n\n${apiDraft.body}\n\n${apiDraft.closing}\n\n${apiDraft.signature || ''}`,
            tone: request.context.tone,
            language: request.language,
            generatedAt: new Date(),
            modelVersion: apiDraft.model_version || 'v1.0',
            reasoningId: apiDraft.reasoning_id || request.threadContext?.reasoningId,
            confidenceScore: apiDraft.confidence_score || 0.85,
            alternatives: apiDraft.alternatives || [],
            complianceIssues: apiDraft.compliance_issues || [],
            suggestions: apiDraft.suggestions || [],
            tokensUsed: apiDraft.tokens_used || 0,
            generationTimeMs: apiDraft.generation_time_ms || 0,
            createdAt: new Date(),
            editsMade: [],
          };

          const drafts = new Map(get().drafts);
          drafts.set(draft.id, draft);

          // Evict oldest drafts when exceeding limit (#68)
          const MAX_DRAFTS = 50;
          if (drafts.size > MAX_DRAFTS) {
            const keys = Array.from(drafts.keys());
            for (let i = 0; i < keys.length - MAX_DRAFTS; i++) {
              drafts.delete(keys[i]);
            }
          }

          // Record history
          const history = [...get().history];
          history.push({
            draftId: draft.id,
            action: 'generated',
            actorId: request.requestedBy,
            timestamp: new Date(),
          });

          // Evict oldest history entries when exceeding limit (#68)
          const MAX_HISTORY = 200;
          const trimmedHistory = history.length > MAX_HISTORY
            ? history.slice(history.length - MAX_HISTORY)
            : history;

          // Add recipient to recents
          const recentRecipients = [...get().recentRecipients];
          const existingIdx = recentRecipients.findIndex(
            (r) => r.recipient.email === request.context.recipient.email
          );
          if (existingIdx >= 0) {
            recentRecipients[existingIdx] = {
              recipient: request.context.recipient,
              lastUsed: new Date(),
              usageCount: recentRecipients[existingIdx].usageCount + 1,
            };
          } else {
            recentRecipients.unshift({
              recipient: request.context.recipient,
              lastUsed: new Date(),
              usageCount: 1,
            });
          }

          set({
            drafts,
            history: trimmedHistory,
            recentRecipients: recentRecipients.slice(0, 20),
            activeDraftId: draft.id,
            isGenerating: false,
          });

          return draft;
        } catch (error) {
          set({
            isGenerating: false,
            generationError: error instanceof Error ? error.message : 'Generation failed',
          });
          throw error;
        }
      },

      getDraft: (id: string) => get().drafts.get(id),

      updateDraft: (id: string, updates: Partial<GeneratedDraft>) => {
        const drafts = new Map(get().drafts);
        const draft = drafts.get(id);
        if (!draft) return;

        const updatedDraft = { ...draft, ...updates };

        // Regenerate body if content changed
        if (updates.opening || updates.mainContent || updates.closing) {
          const bodyParts = [
            updatedDraft.salutation,
            '',
            updatedDraft.opening,
            '',
            ...updatedDraft.mainContent,
            '',
            updatedDraft.closing,
            '',
            updatedDraft.signature,
          ];
          updatedDraft.bodyPlain = bodyParts.join('\n');
        }

        updatedDraft.editsMade = [...(draft.editsMade || []), JSON.stringify(updates)];
        drafts.set(id, updatedDraft);

        // Record history
        const history = [...get().history];
        history.push({
          draftId: id,
          action: 'edited',
          timestamp: new Date(),
          details: Object.keys(updates).join(', '),
        });

        set({ drafts, history });
      },

      approveDraft: (id: string, reviewerId: string) => {
        const drafts = new Map(get().drafts);
        const draft = drafts.get(id);
        if (!draft) return;

        drafts.set(id, {
          ...draft,
          status: 'approved',
          reviewedAt: new Date(),
          reviewedBy: reviewerId,
        });

        const history = [...get().history];
        history.push({
          draftId: id,
          action: 'approved',
          actorId: reviewerId,
          timestamp: new Date(),
        });

        set({ drafts, history });
      },

      markSent: (id: string) => {
        const drafts = new Map(get().drafts);
        const draft = drafts.get(id);
        if (!draft) return;

        drafts.set(id, { ...draft, status: 'sent' });

        const history = [...get().history];
        history.push({
          draftId: id,
          action: 'sent',
          timestamp: new Date(),
        });

        set({ drafts, history });
      },

      discardDraft: (id: string, reason?: string) => {
        const drafts = new Map(get().drafts);
        const draft = drafts.get(id);
        if (!draft) return;

        drafts.set(id, { ...draft, status: 'discarded' });

        const history = [...get().history];
        history.push({
          draftId: id,
          action: 'discarded',
          timestamp: new Date(),
          details: reason,
        });

        set({
          drafts,
          history,
          activeDraftId: get().activeDraftId === id ? null : get().activeDraftId,
        });
      },

      regenerateDraft: async (id: string, feedback?: string): Promise<GeneratedDraft> => {
        const original = get().drafts.get(id);
        if (!original) throw new Error('Draft not found');

        // Mark original as discarded
        get().discardDraft(id, `Regenerated${feedback ? `: ${feedback}` : ''}`);

        // Create new request based on original
        // In real implementation, we'd store the original request
        const newRequest: GenerationRequest = {
          id: generateId(),
          context: createDefaultContext(createRecipient('recipient@example.com')),
          senderName: '',
          senderEmail: '',
          companyName: '',
          requestedAt: new Date(),
        };

        return get().generateDraft(newRequest);
      },

      setActiveDraft: (id: string | null) => set({ activeDraftId: id }),

      // Recipient management
      addRecentRecipient: (recipient: Recipient) => {
        const recentRecipients = [...get().recentRecipients];
        const existingIdx = recentRecipients.findIndex(
          (r) => r.recipient.email === recipient.email
        );
        if (existingIdx >= 0) {
          recentRecipients[existingIdx] = {
            ...recentRecipients[existingIdx],
            lastUsed: new Date(),
            usageCount: recentRecipients[existingIdx].usageCount + 1,
          };
        } else {
          recentRecipients.unshift({
            recipient,
            lastUsed: new Date(),
            usageCount: 1,
          });
        }
        set({ recentRecipients: recentRecipients.slice(0, 20) });
      },

      removeRecentRecipient: (email: string) => {
        set({
          recentRecipients: get().recentRecipients.filter((r) => r.recipient.email !== email),
        });
      },

      clearRecentRecipients: () => set({ recentRecipients: [] }),

      // Template management
      addTemplate: (template: EmailTemplate) => {
        const templates = new Map(get().templates);
        templates.set(template.id, template);
        set({ templates });
      },

      updateTemplate: (id: string, updates: Partial<EmailTemplate>) => {
        const templates = new Map(get().templates);
        const template = templates.get(id);
        if (!template) return;
        templates.set(id, { ...template, ...updates });
        set({ templates });
      },

      deleteTemplate: (id: string) => {
        const templates = new Map(get().templates);
        templates.delete(id);
        set({ templates });
      },

      getTemplatesByPurpose: (purpose: EmailPurpose) =>
        Array.from(get().templates.values()).filter(
          (t) => t.purpose === purpose && t.isActive
        ),

      // History
      getHistoryForDraft: (draftId: string) =>
        get().history.filter((h) => h.draftId === draftId),

      clearHistory: () => set({ history: [] }),

      // UI Actions
      setShowComposeModal: (show: boolean) => set({ showComposeModal: show }),
      setShowTemplateSelector: (show: boolean) => set({ showTemplateSelector: show }),
      setSelectedPurpose: (purpose: EmailPurpose | null) => set({ selectedPurpose: purpose }),
      setSelectedTone: (tone: EmailTone) => set({ selectedTone: tone }),
      setSelectedLanguage: (language: Language) => set({ selectedLanguage: language }),
      setIsEditing: (editing: boolean) => set({ isEditing: editing }),
      setEditField: (field: 'subject' | 'body' | 'salutation' | 'closing' | null) =>
        set({ editField: field }),

      // Reset
      reset: () => set({ ...initialState }),
    }),
    {
      name: 'email-drafting-storage',
      partialize: (state) => ({
        recentRecipients: state.recentRecipients,
        selectedTone: state.selectedTone,
        selectedLanguage: state.selectedLanguage,
      }),
    }
  )
);

export default useEmailDraftingStore;
