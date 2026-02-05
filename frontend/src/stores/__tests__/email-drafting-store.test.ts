/**
 * Tests for Email Drafting Store
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useEmailDraftingStore,
  generateId,
  getPurposeLabel,
  getToneLabel,
  getLanguageLabel,
  getStatusLabel,
  getStatusColor,
  getConfidenceColor,
  formatConfidenceScore,
  formatGenerationTime,
  getComplianceSeverityColor,
  getSuggestionPriorityColor,
  createDefaultContext,
  validateRecipient,
  createRecipient,
  EmailTone,
  EmailPurpose,
  DraftStatus,
  Language,
  Recipient,
  GenerationRequest,
} from '../email-drafting-store';

jest.mock('axios', () => {
  const isAxiosError = (error: any) => Boolean(error?.isAxiosError);

  const post = jest.fn().mockImplementation((_url: string, payload: any) => {
    const ref = payload?.reference_number;
    const name = payload?.recipient?.name || 'there';
    const keyPoints = payload?.key_points || [];
    return Promise.resolve({
      data: {
        id: 'draft-1',
        subject: ref ? `Update on ${ref}` : 'Subject',
        salutation: `Hello ${name}`,
        body: keyPoints.length ? keyPoints.join(' ') : 'Body content',
        opening: 'Opening',
        main_content: keyPoints.length ? keyPoints : ['Point 1'],
        closing: 'Regards',
        signature: 'Signature',
        alternatives: [],
        compliance_issues: [],
        suggestions: [],
        tokens_used: 0,
        generation_time_ms: 1,
        model_version: 'v1.0',
        confidence_score: 0.9,
      },
    });
  });

  const create = jest.fn(() => {
    const instance: any = jest.fn().mockResolvedValue({ data: {} });
    instance.interceptors = {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    };
    instance.post = post;
    instance.get = jest.fn().mockResolvedValue({ data: {} });
    instance.put = jest.fn().mockResolvedValue({ data: {} });
    instance.delete = jest.fn().mockResolvedValue({ data: {} });
    return instance;
  });

  return {
    __esModule: true,
    default: {
      create,
      post,
      isCancel: jest.fn(() => false),
      isAxiosError,
    },
    isAxiosError,
  };
});

// Reset store before each test
beforeEach(() => {
  const { result } = renderHook(() => useEmailDraftingStore());
  act(() => {
    result.current.reset();
  });
});

describe('Email Drafting Store', () => {
  // ============================================================================
  // Helper Functions Tests
  // ============================================================================

  describe('generateId', () => {
    it('should generate unique IDs', () => {
      const id1 = generateId();
      const id2 = generateId();
      expect(id1).not.toBe(id2);
    });

    it('should generate non-empty strings', () => {
      const id = generateId();
      expect(id.length).toBeGreaterThan(0);
    });
  });

  describe('getPurposeLabel', () => {
    it('should return label for missing_info_request', () => {
      expect(getPurposeLabel('missing_info_request')).toBe('Missing Information Request');
    });

    it('should return label for quote_followup', () => {
      expect(getPurposeLabel('quote_followup')).toBe('Quote Follow-up');
    });

    it('should return label for quote_submission', () => {
      expect(getPurposeLabel('quote_submission')).toBe('Quote Submission');
    });

    it('should return label for meeting_request', () => {
      expect(getPurposeLabel('meeting_request')).toBe('Meeting Request');
    });

    it('should return label for issue_notification', () => {
      expect(getPurposeLabel('issue_notification')).toBe('Issue Notification');
    });

    it('should return label for status_update', () => {
      expect(getPurposeLabel('status_update')).toBe('Status Update');
    });

    it('should return label for custom', () => {
      expect(getPurposeLabel('custom')).toBe('Custom Email');
    });

    it('should return label for all purposes', () => {
      const purposes: EmailPurpose[] = [
        'missing_info_request',
        'quote_followup',
        'quote_submission',
        'supplier_inquiry',
        'meeting_request',
        'meeting_confirmation',
        'meeting_reschedule',
        'issue_notification',
        'status_update',
        'thank_you',
        'introduction',
        'escalation',
        'apology',
        'custom',
      ];
      purposes.forEach((purpose) => {
        expect(getPurposeLabel(purpose)).toBeTruthy();
      });
    });
  });

  describe('getToneLabel', () => {
    it('should return label for formal', () => {
      expect(getToneLabel('formal')).toBe('Formal');
    });

    it('should return label for professional', () => {
      expect(getToneLabel('professional')).toBe('Professional');
    });

    it('should return label for friendly', () => {
      expect(getToneLabel('friendly')).toBe('Friendly');
    });

    it('should return label for urgent', () => {
      expect(getToneLabel('urgent')).toBe('Urgent');
    });

    it('should return label for all tones', () => {
      const tones: EmailTone[] = [
        'formal',
        'professional',
        'friendly',
        'urgent',
        'apologetic',
        'appreciative',
        'concise',
      ];
      tones.forEach((tone) => {
        expect(getToneLabel(tone)).toBeTruthy();
      });
    });
  });

  describe('getLanguageLabel', () => {
    it('should return English for en', () => {
      expect(getLanguageLabel('en')).toBe('English');
    });

    it('should return French for fr', () => {
      expect(getLanguageLabel('fr')).toBe('French');
    });

    it('should return German for de', () => {
      expect(getLanguageLabel('de')).toBe('German');
    });

    it('should return Spanish for es', () => {
      expect(getLanguageLabel('es')).toBe('Spanish');
    });

    it('should return label for all languages', () => {
      const languages: Language[] = ['en', 'fr', 'de', 'es', 'it', 'pt', 'ja', 'zh', 'ko', 'ar'];
      languages.forEach((lang) => {
        expect(getLanguageLabel(lang)).toBeTruthy();
      });
    });
  });

  describe('getStatusLabel', () => {
    it('should return Generating... for generating', () => {
      expect(getStatusLabel('generating')).toBe('Generating...');
    });

    it('should return Ready for Review for ready', () => {
      expect(getStatusLabel('ready')).toBe('Ready for Review');
    });

    it('should return Approved for approved', () => {
      expect(getStatusLabel('approved')).toBe('Approved');
    });

    it('should return Sent for sent', () => {
      expect(getStatusLabel('sent')).toBe('Sent');
    });

    it('should return label for all statuses', () => {
      const statuses: DraftStatus[] = [
        'generating',
        'ready',
        'reviewed',
        'approved',
        'sent',
        'discarded',
        'failed',
      ];
      statuses.forEach((status) => {
        expect(getStatusLabel(status)).toBeTruthy();
      });
    });
  });

  describe('getStatusColor', () => {
    it('should return amber for generating', () => {
      expect(getStatusColor('generating')).toBe('#f59e0b');
    });

    it('should return blue for ready', () => {
      expect(getStatusColor('ready')).toBe('#3b82f6');
    });

    it('should return green for approved', () => {
      expect(getStatusColor('approved')).toBe('#22c55e');
    });

    it('should return red for failed', () => {
      expect(getStatusColor('failed')).toBe('#ef4444');
    });

    it('should return colors for all statuses', () => {
      const statuses: DraftStatus[] = [
        'generating',
        'ready',
        'reviewed',
        'approved',
        'sent',
        'discarded',
        'failed',
      ];
      statuses.forEach((status) => {
        expect(getStatusColor(status)).toMatch(/^#[0-9a-f]{6}$/i);
      });
    });
  });

  describe('getConfidenceColor', () => {
    it('should return green for high confidence', () => {
      expect(getConfidenceColor(0.9)).toBe('#22c55e');
      expect(getConfidenceColor(0.8)).toBe('#22c55e');
    });

    it('should return amber for medium confidence', () => {
      expect(getConfidenceColor(0.7)).toBe('#f59e0b');
      expect(getConfidenceColor(0.6)).toBe('#f59e0b');
    });

    it('should return red for low confidence', () => {
      expect(getConfidenceColor(0.5)).toBe('#ef4444');
      expect(getConfidenceColor(0.3)).toBe('#ef4444');
    });
  });

  describe('formatConfidenceScore', () => {
    it('should format as percentage', () => {
      expect(formatConfidenceScore(0.85)).toBe('85%');
      expect(formatConfidenceScore(0.9)).toBe('90%');
      expect(formatConfidenceScore(1)).toBe('100%');
      expect(formatConfidenceScore(0)).toBe('0%');
    });

    it('should round to nearest integer', () => {
      expect(formatConfidenceScore(0.856)).toBe('86%');
      expect(formatConfidenceScore(0.854)).toBe('85%');
    });
  });

  describe('formatGenerationTime', () => {
    it('should format milliseconds', () => {
      expect(formatGenerationTime(500)).toBe('500ms');
      expect(formatGenerationTime(999)).toBe('999ms');
    });

    it('should format seconds', () => {
      expect(formatGenerationTime(1000)).toBe('1.0s');
      expect(formatGenerationTime(1500)).toBe('1.5s');
      expect(formatGenerationTime(2345)).toBe('2.3s');
    });
  });

  describe('getComplianceSeverityColor', () => {
    it('should return blue for info', () => {
      expect(getComplianceSeverityColor('info')).toBe('#3b82f6');
    });

    it('should return amber for warning', () => {
      expect(getComplianceSeverityColor('warning')).toBe('#f59e0b');
    });

    it('should return red for error', () => {
      expect(getComplianceSeverityColor('error')).toBe('#ef4444');
    });
  });

  describe('getSuggestionPriorityColor', () => {
    it('should return gray for low', () => {
      expect(getSuggestionPriorityColor('low')).toBe('#6b7280');
    });

    it('should return amber for medium', () => {
      expect(getSuggestionPriorityColor('medium')).toBe('#f59e0b');
    });

    it('should return red for high', () => {
      expect(getSuggestionPriorityColor('high')).toBe('#ef4444');
    });
  });

  describe('validateRecipient', () => {
    it('should return error for missing email', () => {
      const errors = validateRecipient({});
      expect(errors).toContain('emailDrafting.validation.emailRequired');
    });

    it('should return error for empty email', () => {
      const errors = validateRecipient({ email: '' });
      expect(errors).toContain('emailDrafting.validation.emailRequired');
    });

    it('should return error for invalid email format', () => {
      const errors = validateRecipient({ email: 'notanemail' });
      expect(errors).toContain('emailDrafting.validation.emailInvalid');
    });

    it('should return empty array for valid email', () => {
      const errors = validateRecipient({ email: 'test@example.com' });
      expect(errors).toHaveLength(0);
    });

    it('should validate complex email addresses', () => {
      expect(validateRecipient({ email: 'user.name@domain.co.uk' })).toHaveLength(0);
      expect(validateRecipient({ email: 'user+tag@example.com' })).toHaveLength(0);
    });
  });

  describe('createRecipient', () => {
    it('should create recipient with email only', () => {
      const recipient = createRecipient('test@example.com');
      expect(recipient.email).toBe('test@example.com');
      expect(recipient.name).toBeUndefined();
      expect(recipient.languagePreference).toBe('en');
      expect(recipient.previousInteractions).toBe(0);
    });

    it('should create recipient with name', () => {
      const recipient = createRecipient('test@example.com', 'John Doe');
      expect(recipient.email).toBe('test@example.com');
      expect(recipient.name).toBe('John Doe');
    });

    it('should generate unique IDs', () => {
      const r1 = createRecipient('test1@example.com');
      const r2 = createRecipient('test2@example.com');
      expect(r1.id).not.toBe(r2.id);
    });
  });

  describe('createDefaultContext', () => {
    it('should create context with recipient', () => {
      const recipient = createRecipient('test@example.com', 'John');
      const context = createDefaultContext(recipient);
      expect(context.recipient).toBe(recipient);
      expect(context.purpose).toBe('custom');
      expect(context.tone).toBe('professional');
    });

    it('should use recipient language preference', () => {
      const recipient = createRecipient('test@example.com');
      recipient.languagePreference = 'fr';
      const context = createDefaultContext(recipient);
      expect(context.language).toBe('fr');
    });

    it('should set default values', () => {
      const recipient = createRecipient('test@example.com');
      const context = createDefaultContext(recipient);
      expect(context.keyPoints).toEqual([]);
      expect(context.attachments).toEqual([]);
      expect(context.includeSignature).toBe(true);
      expect(context.maxParagraphs).toBe(4);
    });
  });

  // ============================================================================
  // Store State Tests
  // ============================================================================

  describe('Initial State', () => {
    it('should have empty drafts', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.drafts.size).toBe(0);
    });

    it('should have no active draft', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.activeDraftId).toBeNull();
    });

    it('should not be generating', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.isGenerating).toBe(false);
    });

    it('should have no generation error', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.generationError).toBeNull();
    });

    it('should have empty recent recipients', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.recentRecipients).toHaveLength(0);
    });

    it('should have default tone as professional', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.selectedTone).toBe('professional');
    });

    it('should have default language as en', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      expect(result.current.selectedLanguage).toBe('en');
    });
  });

  // ============================================================================
  // Draft Generation Tests
  // ============================================================================

  describe('Draft Generation', () => {
    const createTestRequest = (): GenerationRequest => ({
      id: generateId(),
      context: {
        purpose: 'quote_followup',
        recipient: createRecipient('john@example.com', 'John Doe'),
        keyPoints: ['First point', 'Second point'],
        attachments: [],
        referenceNumber: 'Q-123',
        tone: 'professional',
        language: 'en',
        includeSignature: true,
        maxParagraphs: 4,
      },
      senderName: 'Jane Smith',
      senderTitle: 'Sales Manager',
      senderEmail: 'jane@company.com',
      companyName: 'Acme Corp',
      requestedAt: new Date(),
    });

    it('should generate a draft', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft).toBeDefined();
      expect(draft!.id).toBeTruthy();
      expect(draft!.status).toBe('ready');
    });

    it('should store generated draft', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      await act(async () => {
        await result.current.generateDraft(request);
      });

      expect(result.current.drafts.size).toBe(1);
    });

    it('should set active draft after generation', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(result.current.activeDraftId).toBe(draft!.id);
    });

    it('should generate draft with subject', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft!.subject).toContain('Q-123');
    });

    it('should generate draft with salutation', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft!.salutation).toContain('John');
    });

    it('should generate draft with body', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft!.bodyPlain.length).toBeGreaterThan(0);
      expect(draft!.bodyHtml.length).toBeGreaterThan(0);
    });

    it('should include key points in body', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft!.bodyPlain).toContain('First point');
      expect(draft!.bodyPlain).toContain('Second point');
    });

    it('should add recipient to recent recipients', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      await act(async () => {
        await result.current.generateDraft(request);
      });

      expect(result.current.recentRecipients.length).toBe(1);
      expect(result.current.recentRecipients[0].recipient.email).toBe('john@example.com');
    });

    it('should record generation in history', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      const history = result.current.getHistoryForDraft(draft!.id);
      expect(history.length).toBe(1);
      expect(history[0].action).toBe('generated');
    });

    it('should generate with confidence score', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft!.confidenceScore).toBeGreaterThan(0);
      expect(draft!.confidenceScore).toBeLessThanOrEqual(1);
    });

    it('should track generation time', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request = createTestRequest();

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      expect(draft!.generationTimeMs).toBeGreaterThanOrEqual(0);
    });
  });

  // ============================================================================
  // Draft Management Tests
  // ============================================================================

  describe('Draft Management', () => {
    const setupDraft = async () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const request: GenerationRequest = {
        id: generateId(),
        context: {
          purpose: 'quote_followup',
          recipient: createRecipient('john@example.com', 'John'),
          keyPoints: [],
          attachments: [],
          tone: 'professional',
          language: 'en',
          includeSignature: true,
          maxParagraphs: 4,
        },
        senderName: 'Jane',
        senderEmail: 'jane@co.com',
        companyName: 'Co',
        requestedAt: new Date(),
      };

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      return { result, draft: draft! };
    };

    it('should get draft by ID', async () => {
      const { result, draft } = await setupDraft();
      expect(result.current.getDraft(draft.id)).toBeDefined();
      expect(result.current.getDraft(draft.id)?.id).toBe(draft.id);
    });

    it('should return undefined for unknown draft ID', async () => {
      const { result } = await setupDraft();
      expect(result.current.getDraft('unknown-id')).toBeUndefined();
    });

    it('should update draft subject', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.updateDraft(draft.id, { subject: 'New Subject' });
      });

      expect(result.current.getDraft(draft.id)?.subject).toBe('New Subject');
    });

    it('should update draft body content', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.updateDraft(draft.id, { opening: 'New opening paragraph.' });
      });

      const updated = result.current.getDraft(draft.id);
      expect(updated?.opening).toBe('New opening paragraph.');
      expect(updated?.bodyPlain).toContain('New opening paragraph.');
    });

    it('should track edits made', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.updateDraft(draft.id, { subject: 'Updated' });
      });

      const updated = result.current.getDraft(draft.id);
      expect(updated?.editsMade.length).toBe(1);
    });

    it('should record edit in history', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.updateDraft(draft.id, { subject: 'Changed' });
      });

      const history = result.current.getHistoryForDraft(draft.id);
      const editEntry = history.find((h) => h.action === 'edited');
      expect(editEntry).toBeDefined();
    });

    it('should approve draft', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.approveDraft(draft.id, 'reviewer-123');
      });

      const approved = result.current.getDraft(draft.id);
      expect(approved?.status).toBe('approved');
      expect(approved?.reviewedBy).toBe('reviewer-123');
      expect(approved?.reviewedAt).toBeDefined();
    });

    it('should record approval in history', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.approveDraft(draft.id, 'reviewer-123');
      });

      const history = result.current.getHistoryForDraft(draft.id);
      const approvalEntry = history.find((h) => h.action === 'approved');
      expect(approvalEntry).toBeDefined();
      expect(approvalEntry?.actorId).toBe('reviewer-123');
    });

    it('should mark draft as sent', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.markSent(draft.id);
      });

      expect(result.current.getDraft(draft.id)?.status).toBe('sent');
    });

    it('should record sent in history', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.markSent(draft.id);
      });

      const history = result.current.getHistoryForDraft(draft.id);
      expect(history.some((h) => h.action === 'sent')).toBe(true);
    });

    it('should discard draft', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.discardDraft(draft.id, 'Not needed');
      });

      expect(result.current.getDraft(draft.id)?.status).toBe('discarded');
    });

    it('should clear active draft when discarding active', async () => {
      const { result, draft } = await setupDraft();

      expect(result.current.activeDraftId).toBe(draft.id);

      act(() => {
        result.current.discardDraft(draft.id);
      });

      expect(result.current.activeDraftId).toBeNull();
    });

    it('should record discard reason in history', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.discardDraft(draft.id, 'Changed approach');
      });

      const history = result.current.getHistoryForDraft(draft.id);
      const discardEntry = history.find((h) => h.action === 'discarded');
      expect(discardEntry?.details).toBe('Changed approach');
    });

    it('should set active draft', async () => {
      const { result, draft } = await setupDraft();

      act(() => {
        result.current.setActiveDraft(null);
      });
      expect(result.current.activeDraftId).toBeNull();

      act(() => {
        result.current.setActiveDraft(draft.id);
      });
      expect(result.current.activeDraftId).toBe(draft.id);
    });
  });

  // ============================================================================
  // Recipient Management Tests
  // ============================================================================

  describe('Recipient Management', () => {
    it('should add recent recipient', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const recipient = createRecipient('test@example.com', 'Test User');

      act(() => {
        result.current.addRecentRecipient(recipient);
      });

      expect(result.current.recentRecipients.length).toBe(1);
      expect(result.current.recentRecipients[0].recipient.email).toBe('test@example.com');
    });

    it('should increment usage count for existing recipient', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const recipient = createRecipient('test@example.com', 'Test');

      act(() => {
        result.current.addRecentRecipient(recipient);
        result.current.addRecentRecipient(recipient);
      });

      expect(result.current.recentRecipients.length).toBe(1);
      expect(result.current.recentRecipients[0].usageCount).toBe(2);
    });

    it('should limit recent recipients to 20', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        for (let i = 0; i < 25; i++) {
          result.current.addRecentRecipient(createRecipient(`test${i}@example.com`));
        }
      });

      expect(result.current.recentRecipients.length).toBe(20);
    });

    it('should remove recent recipient', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const recipient = createRecipient('test@example.com');

      act(() => {
        result.current.addRecentRecipient(recipient);
      });
      expect(result.current.recentRecipients.length).toBe(1);

      act(() => {
        result.current.removeRecentRecipient('test@example.com');
      });
      expect(result.current.recentRecipients.length).toBe(0);
    });

    it('should clear all recent recipients', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.addRecentRecipient(createRecipient('test1@example.com'));
        result.current.addRecentRecipient(createRecipient('test2@example.com'));
      });
      expect(result.current.recentRecipients.length).toBe(2);

      act(() => {
        result.current.clearRecentRecipients();
      });
      expect(result.current.recentRecipients.length).toBe(0);
    });
  });

  // ============================================================================
  // Template Management Tests
  // ============================================================================

  describe('Template Management', () => {
    const createTestTemplate = () => ({
      id: generateId(),
      name: 'Test Template',
      purpose: 'quote_followup' as EmailPurpose,
      language: 'en' as Language,
      subjectTemplate: 'Follow-up: {reference}',
      bodyTemplate: 'Dear {name}, ...',
      tone: 'professional' as EmailTone,
      placeholders: ['reference', 'name'],
      isDefault: false,
      isActive: true,
      usageCount: 0,
      successRate: 0,
    });

    it('should add template', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const template = createTestTemplate();

      act(() => {
        result.current.addTemplate(template);
      });

      expect(result.current.templates.size).toBe(1);
    });

    it('should update template', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const template = createTestTemplate();

      act(() => {
        result.current.addTemplate(template);
        result.current.updateTemplate(template.id, { name: 'Updated Name' });
      });

      expect(result.current.templates.get(template.id)?.name).toBe('Updated Name');
    });

    it('should delete template', () => {
      const { result } = renderHook(() => useEmailDraftingStore());
      const template = createTestTemplate();

      act(() => {
        result.current.addTemplate(template);
      });
      expect(result.current.templates.size).toBe(1);

      act(() => {
        result.current.deleteTemplate(template.id);
      });
      expect(result.current.templates.size).toBe(0);
    });

    it('should get templates by purpose', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.addTemplate({
          ...createTestTemplate(),
          id: '1',
          purpose: 'quote_followup',
        });
        result.current.addTemplate({
          ...createTestTemplate(),
          id: '2',
          purpose: 'thank_you',
        });
        result.current.addTemplate({
          ...createTestTemplate(),
          id: '3',
          purpose: 'quote_followup',
        });
      });

      const followupTemplates = result.current.getTemplatesByPurpose('quote_followup');
      expect(followupTemplates.length).toBe(2);
    });

    it('should only return active templates', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.addTemplate({
          ...createTestTemplate(),
          id: '1',
          isActive: true,
        });
        result.current.addTemplate({
          ...createTestTemplate(),
          id: '2',
          isActive: false,
        });
      });

      const templates = result.current.getTemplatesByPurpose('quote_followup');
      expect(templates.length).toBe(1);
    });
  });

  // ============================================================================
  // History Tests
  // ============================================================================

  describe('History', () => {
    it('should get history for specific draft', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      const request: GenerationRequest = {
        id: generateId(),
        context: {
          purpose: 'custom',
          recipient: createRecipient('test@example.com'),
          keyPoints: [],
          attachments: [],
          tone: 'professional',
          language: 'en',
          includeSignature: true,
          maxParagraphs: 4,
        },
        senderName: 'Test',
        senderEmail: 'test@co.com',
        companyName: 'Co',
        requestedAt: new Date(),
      };

      let draft;
      await act(async () => {
        draft = await result.current.generateDraft(request);
      });

      const history = result.current.getHistoryForDraft(draft!.id);
      expect(history.length).toBe(1);
    });

    it('should clear history', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      const request: GenerationRequest = {
        id: generateId(),
        context: {
          purpose: 'custom',
          recipient: createRecipient('test@example.com'),
          keyPoints: [],
          attachments: [],
          tone: 'professional',
          language: 'en',
          includeSignature: true,
          maxParagraphs: 4,
        },
        senderName: 'Test',
        senderEmail: 'test@co.com',
        companyName: 'Co',
        requestedAt: new Date(),
      };

      await act(async () => {
        await result.current.generateDraft(request);
      });

      act(() => {
        result.current.clearHistory();
      });

      expect(result.current.history.length).toBe(0);
    });
  });

  // ============================================================================
  // UI State Tests
  // ============================================================================

  describe('UI State', () => {
    it('should toggle compose modal', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      expect(result.current.showComposeModal).toBe(false);

      act(() => {
        result.current.setShowComposeModal(true);
      });
      expect(result.current.showComposeModal).toBe(true);

      act(() => {
        result.current.setShowComposeModal(false);
      });
      expect(result.current.showComposeModal).toBe(false);
    });

    it('should toggle template selector', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      expect(result.current.showTemplateSelector).toBe(false);

      act(() => {
        result.current.setShowTemplateSelector(true);
      });
      expect(result.current.showTemplateSelector).toBe(true);
    });

    it('should set selected purpose', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.setSelectedPurpose('quote_followup');
      });
      expect(result.current.selectedPurpose).toBe('quote_followup');

      act(() => {
        result.current.setSelectedPurpose(null);
      });
      expect(result.current.selectedPurpose).toBeNull();
    });

    it('should set selected tone', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.setSelectedTone('formal');
      });
      expect(result.current.selectedTone).toBe('formal');
    });

    it('should set selected language', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.setSelectedLanguage('fr');
      });
      expect(result.current.selectedLanguage).toBe('fr');
    });

    it('should set editing state', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      expect(result.current.isEditing).toBe(false);

      act(() => {
        result.current.setIsEditing(true);
      });
      expect(result.current.isEditing).toBe(true);
    });

    it('should set edit field', () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      act(() => {
        result.current.setEditField('subject');
      });
      expect(result.current.editField).toBe('subject');

      act(() => {
        result.current.setEditField(null);
      });
      expect(result.current.editField).toBeNull();
    });
  });

  // ============================================================================
  // Reset Tests
  // ============================================================================

  describe('Reset', () => {
    it('should reset all state to initial values', async () => {
      const { result } = renderHook(() => useEmailDraftingStore());

      // Modify state
      const request: GenerationRequest = {
        id: generateId(),
        context: {
          purpose: 'custom',
          recipient: createRecipient('test@example.com'),
          keyPoints: [],
          attachments: [],
          tone: 'professional',
          language: 'en',
          includeSignature: true,
          maxParagraphs: 4,
        },
        senderName: 'Test',
        senderEmail: 'test@co.com',
        companyName: 'Co',
        requestedAt: new Date(),
      };

      await act(async () => {
        await result.current.generateDraft(request);
        result.current.setShowComposeModal(true);
        result.current.setSelectedTone('formal');
      });

      expect(result.current.drafts.size).toBe(1);
      expect(result.current.showComposeModal).toBe(true);

      // Reset
      act(() => {
        result.current.reset();
      });

      expect(result.current.drafts.size).toBe(0);
      expect(result.current.activeDraftId).toBeNull();
      expect(result.current.showComposeModal).toBe(false);
      expect(result.current.selectedTone).toBe('professional');
    });
  });
});
